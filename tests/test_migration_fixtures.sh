#!/usr/bin/env bash
# Checks the freqtrade-migration claims on 2026.10 (manual suite, not in run_all.sh):
#  1. LegacyV2 (old names) still loads and backtests; MigratedV3 gives identical trades.
#  2. A legacy `buy_tag` column breaks the backtest (observed crash).
#  3. strategy-updater converts LegacyV2 to a strategy that backtests identically, and
#     leaves the documented gaps (forcesell/forcebuy/emergencysell keys, missing `side`).
set -uo pipefail
cd "$(dirname "$0")/.."
IMAGE="freqtradeorg/freqtrade:2026.10"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) HOST="$(pwd -W)"; export MSYS_NO_PATHCONV=1 ;; *) HOST="$(pwd)" ;; esac
UIDARGS=(); [ "$(uname -s)" = Linux ] && UIDARGS=(--user 0:0)
run() { docker run --rm "${UIDARGS[@]}" -e COLUMNS=250 -e PYTHONUSERBASE=/home/ftuser/.local -v "$HOST:/repo" -w /repo "$@"; }
OUT=tests/out/migration; USERDIR="$OUT/user_data"
rm -rf "$OUT" && mkdir -p "$OUT/legacy" "$OUT/migrated" "$OUT/updated" "$OUT/updated_res" "$OUT/buytag" "$OUT/buytag_res"
run "$IMAGE" create-userdir --userdir "$USERDIR" >"$OUT/create-userdir.log" 2>&1 || { echo "setup: FAIL"; exit 1; }
fail=0
bt() { # <strategy> <strategy-path> <resultdir> <log>
  run "$IMAGE" backtesting -c tests/config.test.json --userdir "$USERDIR" -d tests/data/okx \
    --timerange 20260801-20261001 --strategy-path "$2" -s "$1" --no-color \
    --export trades --backtest-directory "$3" >"$4" 2>&1
}
ok_log() { ! grep -Eq '(^|[ ])(ERROR|CRITICAL)[ ]|Traceback \(most recent call last\)' "$1" && grep -q "BACKTESTING REPORT" "$1"; }

# 1. legacy vs migrated
bt LegacyV2 tests/fixtures/strategies "$OUT/legacy" "$OUT/legacy.log"; ok_log "$OUT/legacy.log" || { echo "legacy backtest: FAIL"; fail=1; }
bt MigratedV3 tests/strategies "$OUT/migrated" "$OUT/migrated.log"; ok_log "$OUT/migrated.log" || { echo "migrated backtest: FAIL"; fail=1; }

# 3. updater on a copy
cp tests/fixtures/strategies/LegacyV2.py "$OUT/updated/LegacyV2.py"
run "$IMAGE" strategy-updater --userdir "$USERDIR" --strategy-path "$OUT/updated" --strategy-list LegacyV2 --no-color >"$OUT/updater.log" 2>&1
bt LegacyV2 "$OUT/updated" "$OUT/updated_res" "$OUT/updated.log"; ok_log "$OUT/updated.log" || { echo "updated backtest: FAIL"; fail=1; }
for needle in "'forcesell'" "'forcebuy'" "'emergencysell'"; do
  grep -q "$needle" "$OUT/updated/LegacyV2.py" && echo "updater gap confirmed: $needle left unchanged" || { echo "updater gap: FAIL ($needle was converted; update the skill)"; fail=1; }
done
grep -q "side: str" "$OUT/updated/LegacyV2.py" && { echo "updater gap: FAIL (side added; update the skill)"; fail=1; } || echo "updater gap confirmed: no side argument added"
for needle in "trade.sell_reason is not None" "def custom_entry_price(self, pair: str, current_time" "return stoploss_from_open(0.07, current_profit)$" "return stoploss_from_absolute(current_rate \* 0.95, current_rate)$"; do
  grep -q -- "$needle" "$OUT/updated/LegacyV2.py" && echo "updater gap confirmed: $needle left unchanged" || { echo "updater gap: FAIL ($needle changed; update the skill)"; fail=1; }
done
grep -q "trade.nr_of_successful_entries" "$OUT/updated/LegacyV2.py" && echo "updater converted: nr_of_successful_buys" || { echo "updater: FAIL (nr_of_successful_buys not converted)"; fail=1; }
grep -q "is_short" "$OUT/updated/LegacyV2.py" && { echo "updater gap: FAIL (is_short added; update the skill)"; fail=1; } || echo "updater gap confirmed: no is_short added"

# 2. buy_tag crash
sed 's/"buy",$/["buy", "buy_tag"],/; s/\] = 1$/] = (1, "t")/' tests/fixtures/strategies/LegacyV2.py > "$OUT/buytag/LegacyV2.py"
bt LegacyV2 "$OUT/buytag" "$OUT/buytag_res" "$OUT/buytag.log"
grep -q "cannot reindex on an axis with duplicate labels" "$OUT/buytag.log" && echo "buy_tag crash confirmed" || { echo "buy_tag crash: FAIL (not reproduced; update the skill)"; fail=1; }

# compare trades
run -i --entrypoint python "$IMAGE" -I - "$OUT" <<'PY' || fail=1
import glob, json, sys, zipfile
out = sys.argv[1]
def trades(d, strat):
    z = sorted(glob.glob(f"{out}/{d}/*.zip"))[-1]
    with zipfile.ZipFile(z) as f:
        name = next(n for n in f.namelist() if n.endswith(".json") and "_config" not in n and "_meta" not in n and "market_change" not in n)
        data = json.load(f.open(name))["strategy"][strat]["trades"]
    return [(t["pair"], t["open_date"], t["close_date"], t["open_rate"], t["close_rate"], t["profit_abs"], t["exit_reason"]) for t in data]
a, b, c = trades("legacy", "LegacyV2"), trades("migrated", "MigratedV3"), trades("updated_res", "LegacyV2")
print(f"trades: legacy={len(a)} migrated={len(b)} updater={len(c)}")
bad = False
for label, x in (("migrated", b), ("updater", c)):
    same = a == x
    print(f"legacy == {label}: {same}")
    bad |= not same
sys.exit(1 if bad or not a else 0)
PY
exit $fail
