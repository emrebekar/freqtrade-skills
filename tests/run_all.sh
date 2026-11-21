#!/usr/bin/env bash
# Run run_checks.sh for every entry in tests/strategies.json. Exit 1 if any fail,
# or if the manifest cannot be read / is empty.
# Manifest fields: strategy, config, image, freqai (bool); optional strategy_path, freqaimodel.
# PY / MANIFEST env vars exist so the failure paths can be tested.
set -uo pipefail
cd "$(dirname "$0")/.."
MANIFEST="${MANIFEST:-tests/strategies.json}"
PY="${PY:-scripts/dpy.sh}"
# FT_TAG=<tag> retargets every manifest image (x:2026.10 and x:2026.10_freqai) to that release.
FT_TAG="${FT_TAG:-}"

rows="$("$PY" -c '
import json, sys
for e in json.load(open(sys.argv[1])):
    print("|".join([e["strategy"], e["config"], e["image"], str(bool(e.get("freqai"))),
                    e.get("strategy_path", "tests/strategies"), e.get("freqaimodel", "")]))
' "$MANIFEST" | tr -d '\r')" || { echo "run_all: FAIL (could not read manifest $MANIFEST)" >&2; exit 1; }
[ -n "$rows" ] || { echo "run_all: FAIL (manifest $MANIFEST has no entries)" >&2; exit 1; }

fail=0
while IFS='|' read -r strategy config image freqai spath model; do
  if [ -n "$FT_TAG" ]; then suffix=""; [[ "$image" == *_freqai ]] && suffix="_freqai"; image="${image%%:*}:${FT_TAG}${suffix}"; fi
  args=("$strategy" --config "$config" --image "$image" --strategy-path "$spath")
  [ "$freqai" = "True" ] && args+=(--freqai)
  [ -n "$model" ] && args+=(--freqaimodel "$model")
  echo "== $strategy"
  bash tests/run_checks.sh "${args[@]}" || fail=1
done <<< "$rows"
exit $fail
