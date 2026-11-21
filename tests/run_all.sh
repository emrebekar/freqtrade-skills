#!/usr/bin/env bash
# Run run_checks.sh for every entry in tests/strategies.json. Exit 1 if any fail.
# Needs a JSON reader: uses the pinned freqtrade image's python (scripts/dpy.sh).
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
while IFS=$'\t' read -r strategy config image freqai; do
  args=("$strategy" --config "$config" --image "$image")
  [ "$freqai" = "True" ] && args+=(--freqai)
  echo "== $strategy"
  bash tests/run_checks.sh "${args[@]}" || fail=1
done < <(scripts/dpy.sh -c '
import json
for e in json.load(open("tests/strategies.json")):
    print("\t".join([e["strategy"], e["config"], e["image"], str(bool(e.get("freqai")))]))
' | tr -d '\r')
exit $fail
