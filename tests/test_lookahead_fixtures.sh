#!/usr/bin/env bash
# Runs lookahead-analysis on the known-bad fixtures and checks the documented outcome.
# Flagged fixtures must fail the lookahead check; the two "limitation" fixtures document
# false negatives and must pass it (if that changes, update skills/freqtrade-validation).
set -uo pipefail
cd "$(dirname "$0")/.."
IMAGE="freqtradeorg/freqtrade:2026.10"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) HOST="$(pwd -W)"; export MSYS_NO_PATHCONV=1 ;; *) HOST="$(pwd)" ;; esac
UIDARGS=(); [ "$(uname -s)" = Linux ] && UIDARGS=(--user 0:0)
run() { docker run --rm "${UIDARGS[@]}" -e COLUMNS=250 -e PYTHONUSERBASE=/home/ftuser/.local -v "$HOST:/repo" -w /repo "$@"; }
OUT=tests/out/fixtures; USERDIR="$OUT/user_data"; mkdir -p "$OUT"
run "$IMAGE" create-userdir --userdir "$USERDIR" >"$OUT/create-userdir.log" 2>&1 || { echo "setup: FAIL"; exit 1; }
fail=0
# name:expected (flagged = lookahead check fails, missed = known false negative, check passes)
for spec in LookaheadBad:flagged LookaheadBadMean:flagged LookaheadBadZscore:flagged LookaheadBadIloc:flagged \
            LookaheadBadResample:flagged LookaheadBadMerge:missed LookaheadBadMacd1:missed; do
  s="${spec%%:*}"; want="${spec##*:}"; csv="$OUT/$s.csv"; rm -f "$csv"
  run "$IMAGE" lookahead-analysis -c tests/config.test.json --userdir "$USERDIR" -d tests/data/okx \
    --timerange 20260801-20261001 --strategy-path tests/fixtures/strategies -s "$s" --no-color \
    --lookahead-analysis-exportfilename "$csv" >"$OUT/$s.log" 2>&1
  if [ ! -f "$csv" ]; then echo "$s: FAIL (no result; see $OUT/$s.log)"; fail=1; continue; fi
  msg=$(run --entrypoint python "$IMAGE" -I tests/check_results.py lookahead "$csv"); rc=$?
  if { [ "$want" = flagged ] && [ $rc -ne 0 ]; } || { [ "$want" = missed ] && [ $rc -eq 0 ]; }; then
    echo "$s: OK as expected ($want) - $msg"
  else
    echo "$s: FAIL (expected $want) - $msg"; fail=1
  fi
done
exit $fail
