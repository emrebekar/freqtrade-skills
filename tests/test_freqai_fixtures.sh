#!/usr/bin/env bash
# Exercises run_checks' --freqai lookahead rule (tests/check_results.py) two ways:
# 1. synthetic CSV rows (fast): &-target plus FreqAI output columns pass, FreqAI outputs without any & column fail; any other flagged column or biased signal fails.
# 2. real lookahead-analysis on FreqAI fixtures (slow, ~90 s each): flagged = must fail, missed = known false negative, must pass.
set -uo pipefail
cd "$(dirname "$0")/.."
IMAGE="freqtradeorg/freqtrade:2026.10_freqai"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) HOST="$(pwd -W)"; export MSYS_NO_PATHCONV=1 ;; *) HOST="$(pwd)" ;; esac
UIDARGS=(); [ "$(uname -s)" = Linux ] && UIDARGS=(--user 0:0)
run() { docker run --rm "${UIDARGS[@]}" -e COLUMNS=250 -e PYTHONUSERBASE=/home/ftuser/.local -v "$HOST:/repo" -w /repo "$@"; }
OUT=tests/out/freqai-fixtures; USERDIR="$OUT/user_data"; rm -rf "$OUT"; mkdir -p "$OUT"
fail=0
HDR="filename,strategy,has_bias,total_signals,biased_entry_signals,biased_exit_signals,biased_indicators"
BASE='&-s_close,&-s_close_mean,&-s_close_std,do_predict,exit_tag,exit_long,enter_tag,enter_long'
# name:entry:exit:extra-indicator:expect(pass|fail)
for spec in "targets_only:0:0::pass" "leaky_returned_feature:0:0:%%-leak:fail" "other_column:0:0:rsi:fail" "biased_signal:2:0::fail"; do
  IFS=: read -r name e x extra want <<< "$spec"
  inds="$BASE"; [ -n "$extra" ] && inds="$extra,$BASE"
  printf '%s\nS.py,S,True,20,%s,%s,"%s"\n' "$HDR" "$e" "$x" "$inds" > "$OUT/$name.csv"
  msg=$(run --entrypoint python "$IMAGE" -I tests/check_results.py lookahead "$OUT/$name.csv" --freqai); rc=$?
  if { [ "$want" = pass ] && [ $rc -eq 0 ]; } || { [ "$want" = fail ] && [ $rc -ne 0 ]; }; then echo "synthetic $name: OK as expected ($want) - $msg"
  else echo "synthetic $name: FAIL (expected $want) - $msg"; fail=1; fi
done

table() { printf "┃ Indicators ┃ 40 (from strategy) ┃ 199 ┃
"; for r in "$@"; do printf "│ %s │ %s │ %s │
" $r; done; }
rt() { # name expect(pass|fail) flag rows...
  n="$1"; want="$2"; fl="$3"; shift 3; table "$@" > "$OUT/rec-$n.log"
  msg=$(run --entrypoint python "$IMAGE" -I tests/check_results.py recursive "$OUT/rec-$n.log" $fl); rc=$?
  if { [ "$want" = pass ] && [ $rc -eq 0 ]; } || { [ "$want" = fail ] && [ $rc -ne 0 ]; }; then echo "synthetic recursive $n: OK as expected ($want) - $msg"
  else echo "synthetic recursive $n: FAIL (expected $want) - $msg"; fail=1; fi
}
rt only_targets pass --freqai "&-s_close -111.5% -59.6%"
rt target_and_bad_feature fail --freqai "&-s_close -111.5% -59.6%" "%%-rsi 2.000% 0.000%"
rt target_and_good_feature pass --freqai "&-s_close -111.5% -59.6%" "%%-rsi 0.100% 0.000%"
printf '%s
S.py,S,True,20,0,0,"do_predict,enter_long,exit_long"
' "$HDR" > "$OUT/derived_only.csv"
msg=$(run --entrypoint python "$IMAGE" -I tests/check_results.py lookahead "$OUT/derived_only.csv" --freqai); rc=$?
if [ $rc -ne 0 ]; then echo "synthetic derived_only: OK as expected (fail) - $msg"; else echo "synthetic derived_only: FAIL (expected fail) - $msg"; fail=1; fi
rt targets_without_flag fail "" "&-s_close -111.5% -59.6%"

[ "${SKIP_RUNS:-0}" = 1 ] && exit $fail
run "$IMAGE" create-userdir --userdir "$USERDIR" >"$OUT/create-userdir.log" 2>&1 || { echo "setup: FAIL"; exit 1; }
# dir:name:expected. missed = known false negative (leaky %- feature is dropped before the strategy sees it).
for spec in tests/strategies:FreqaiExample:pass tests/fixtures/strategies:FreqaiLookaheadBadReturned:fail tests/fixtures/strategies:FreqaiLookaheadBad:pass; do
  IFS=: read -r dir s want <<< "$spec"; csv="$OUT/$s.csv"
  run "$IMAGE" lookahead-analysis -c tests/config.freqai.json --userdir "$USERDIR" -d tests/data/okx \
    --timerange 20260801-20261001 --strategy-path "$dir" -s "$s" --freqaimodel LightGBMRegressor --no-color \
    --lookahead-analysis-exportfilename "$csv" >"$OUT/$s.log" 2>&1
  if [ ! -f "$csv" ]; then echo "$s: FAIL (no result; see $OUT/$s.log)"; fail=1; continue; fi
  msg=$(run --entrypoint python "$IMAGE" -I tests/check_results.py lookahead "$csv" --freqai); rc=$?
  if { [ "$want" = pass ] && [ $rc -eq 0 ]; } || { [ "$want" = fail ] && [ $rc -ne 0 ]; }; then echo "$s: OK as expected ($want) - $msg"
  else echo "$s: FAIL (expected $want) - $msg"; fail=1; fi
done
exit $fail
