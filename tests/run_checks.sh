#!/usr/bin/env bash
# usage: tests/run_checks.sh <Strategy> [--config FILE] [--strategy-path DIR] [--image IMG] [--freqai]
# Runs backtesting, lookahead-analysis and recursive-analysis in the freqtrade image.
# All outputs go to tests/out/<Strategy>/ (gitignored). Exit 1 if any check fails.
set -uo pipefail
cd "$(dirname "$0")/.."

[ $# -ge 1 ] || { echo "usage: $0 <Strategy> [--config FILE] [--strategy-path DIR] [--image IMG] [--freqai] [--freqaimodel NAME]" >&2; exit 2; }
STRATEGY="$1"; shift
MODEL=""; CONFIG="tests/config.test.json"; SPATH="tests/strategies"; IMAGE="freqtradeorg/freqtrade:2026.10"; FREQAI=""
# freqtrade ignores the config's "datadir" key, so pass it on the CLI.
DATADIR="tests/data/binance"; TIMERANGE="20260801-20261001"
while [ $# -gt 0 ]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --strategy-path) SPATH="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    --freqai) FREQAI="--freqai"; shift ;;
    --freqaimodel) MODEL="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) HOST="$(pwd -W)"; export MSYS_NO_PATHCONV=1 ;;
  *) HOST="$(pwd)" ;;
esac
OUT="tests/out/$STRATEGY"; USERDIR="$OUT/user_data"
rm -rf "$OUT" || { echo "setup: FAIL (cannot clean $OUT; root-owned from an earlier Linux run?)"; exit 1; }
mkdir -p "$OUT"
# Linux CI: root in the container (image user ftuser cannot write a runner-owned tests/out; an arbitrary --user cannot read ftuser's site-packages).
UIDARGS=(); [ "$(uname -s)" = Linux ] && UIDARGS=(--user 0:0)
run() { docker run --rm "${UIDARGS[@]}" -e COLUMNS=250 -e PYTHONUSERBASE=/home/ftuser/.local -v "$HOST:/repo" -w /repo "$@"; }
ft() { run "$IMAGE" "$@"; }
COMMON=(-c "$CONFIG" --userdir "$USERDIR" -d "$DATADIR" --timerange "$TIMERANGE" --strategy-path "$SPATH" -s "$STRATEGY" --no-color)
[ -n "$MODEL" ] && COMMON+=(--freqaimodel "$MODEL")
fail=0

ft create-userdir --userdir "$USERDIR" >"$OUT/create-userdir.log" 2>&1 || { echo "setup: FAIL (create-userdir; see $OUT/create-userdir.log)"; exit 1; }

# freqtrade exits 0 on some errors (bad --timerange, unrecognized args), so also require error-free output and a results table.
if ft backtesting "${COMMON[@]}" --export none >"$OUT/backtest.log" 2>&1 \
   && ! grep -Eq '(^|[ ])(ERROR|CRITICAL)[ ]|: error: |Traceback \(most recent call last\)' "$OUT/backtest.log" \
   && grep -q "BACKTESTING REPORT" "$OUT/backtest.log"; then
  echo "backtest: OK"
else
  echo "backtest: FAIL (see $OUT/backtest.log)"; fail=1
fi

if ft lookahead-analysis "${COMMON[@]}" --lookahead-analysis-exportfilename "$OUT/lookahead.csv" >"$OUT/lookahead.log" 2>&1 \
   && [ -f "$OUT/lookahead.csv" ]; then
  run --entrypoint python "$IMAGE" -I tests/check_results.py lookahead "$OUT/lookahead.csv" $FREQAI || fail=1
else
  echo "lookahead: FAIL (command failed or no result; see $OUT/lookahead.log)"; fail=1
fi

if ft recursive-analysis "${COMMON[@]}" >"$OUT/recursive.log" 2>&1; then
  run --entrypoint python "$IMAGE" -I tests/check_results.py recursive "$OUT/recursive.log" $FREQAI || fail=1
else
  echo "recursive: FAIL (command failed; see $OUT/recursive.log)"; fail=1
fi

exit $fail
