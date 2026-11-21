#!/usr/bin/env bash
# usage: tests/run_hyperopt.sh <Strategy> [--epochs N] [--spaces "buy sell"] [--loss NAME] [--loss-path DIR] [--timerange R]
#        [--config FILE] [--strategy-path DIR] [--image IMG]
# Copies the strategy to tests/out/hyperopt/strategies/ and runs hyperopt there (-j 1, fixed --random-state),
# then hyperopt-list and hyperopt-show on the result. The params JSON lands in the temp copy, never in the repo.
# Logs: tests/out/hyperopt/*.log. Exit 1 on any failure.
set -uo pipefail
cd "$(dirname "$0")/.."

[ $# -ge 1 ] || { echo "usage: $0 <Strategy> [--epochs N] [--spaces \"buy sell\"] [--loss NAME] [--timerange R]" >&2; exit 2; }
STRATEGY="$1"; shift
LOSSPATH=""; EPOCHS=5; SPACES="buy sell"; LOSS="SharpeHyperOptLossDaily"; CONFIG="tests/config.test.json"
SPATH="tests/strategies"; IMAGE="freqtradeorg/freqtrade:2026.10"
DATADIR="tests/data/binance"
TIMERANGE="20260801-20260915" # in-sample part only; 20260915-20261001 stays unseen for validation
while [ $# -gt 0 ]; do
  case "$1" in
    --epochs) EPOCHS="$2"; shift 2 ;;
    --spaces) SPACES="$2"; shift 2 ;;
    --loss) LOSS="$2"; shift 2 ;;
    --loss-path) LOSSPATH="$2"; shift 2 ;;
    --timerange) TIMERANGE="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --strategy-path) SPATH="$2"; shift 2 ;;
    --image) IMAGE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) HOST="$(pwd -W)"; export MSYS_NO_PATHCONV=1 ;;
  *) HOST="$(pwd)" ;;
esac
OUT="tests/out/hyperopt"; USERDIR="$OUT/user_data"; COPY="$OUT/strategies"
[ -f "$SPATH/$STRATEGY.py" ] || { echo "setup: FAIL ($SPATH/$STRATEGY.py not found)"; exit 1; }
rm -rf "$OUT" || { echo "setup: FAIL (cannot clean $OUT)"; exit 1; }
mkdir -p "$COPY" && cp "$SPATH/$STRATEGY.py" "$COPY/" || { echo "setup: FAIL (copy)"; exit 1; }
UIDARGS=(); [ "$(uname -s)" = Linux ] && UIDARGS=(--user 0:0)
ft() { docker run --rm "${UIDARGS[@]}" -e COLUMNS=250 -e PYTHONUSERBASE=/home/ftuser/.local -v "$HOST:/repo" -w /repo "$IMAGE" "$@"; }
BASE=(-c "$CONFIG" --userdir "$USERDIR" -d "$DATADIR" --no-color)

ft create-userdir --userdir "$USERDIR" >"$OUT/create-userdir.log" 2>&1 || { echo "setup: FAIL (see $OUT/create-userdir.log)"; exit 1; }

# shellcheck disable=SC2086 # SPACES is a deliberate space-separated list
if ft hyperopt "${BASE[@]}" --strategy-path "$COPY" -s "$STRATEGY" --timerange "$TIMERANGE" \
     ${LOSSPATH:+--hyperopt-path "$LOSSPATH"} --hyperopt-loss "$LOSS" --spaces $SPACES -e "$EPOCHS" -j 1 --random-state 42 >"$OUT/hyperopt.log" 2>&1; then
  echo "hyperopt: OK ($EPOCHS epochs, $SPACES, $LOSS, $TIMERANGE)"
else
  echo "hyperopt: FAIL (see $OUT/hyperopt.log)"; exit 1
fi

fail=0
# freqtrade returned exit 0 on an argparse error (observed with hyperopt-show -s), so also scan the logs
if grep -q "error: " "$OUT/hyperopt.log"; then echo "hyperopt: FAIL (argument error in log)"; exit 1; fi
if grep -q "No good result found" "$OUT/hyperopt.log"; then echo "hyperopt: FAIL (no result met the loss function / --min-trades; exit code was 0)"; exit 1; fi
ft hyperopt-list "${BASE[@]}" >"$OUT/hyperopt-list.log" 2>&1 && echo "hyperopt-list: OK" || { echo "hyperopt-list: FAIL (see $OUT/hyperopt-list.log)"; fail=1; }
ft hyperopt-show "${BASE[@]}" --best -n -1 >"$OUT/hyperopt-show.log" 2>&1 \
  && echo "hyperopt-show: OK" || { echo "hyperopt-show: FAIL (see $OUT/hyperopt-show.log)"; fail=1; }
grep -q "error: " "$OUT/hyperopt-list.log" "$OUT/hyperopt-show.log" && { echo "list/show: FAIL (argument error in log)"; fail=1; }
[ -f "$COPY/$STRATEGY.json" ] && echo "params file: $COPY/$STRATEGY.json (temp copy only)"
exit $fail
