#!/usr/bin/env bash
# Run python inside the pinned freqtrade image (no host Python needed).
set -euo pipefail
IMAGE="${FT_IMAGE:-freqtradeorg/freqtrade:2026.10}"  # FT_IMAGE: test against another release
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) HOST="$(pwd -W)"; export MSYS_NO_PATHCONV=1 ;;
  *) HOST="$(pwd)" ;;
esac
exec docker run --rm -v "$HOST:/repo" -w /repo --entrypoint python "$IMAGE" "$@"
