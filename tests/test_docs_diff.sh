#!/usr/bin/env bash
# Self-test for scripts/docs_diff.py using local fixture doc trees (no clone, no network).
set -uo pipefail
cd "$(dirname "$0")/.."
F=tests/fixtures/docs_diff
out="$(scripts/dpy.sh scripts/docs_diff.py --old-dir $F/old --new-dir $F/new --skills $F/skills | tr -d '\r')" || { echo "docs_diff: FAIL (script error)"; exit 1; }
fail=0
has() { grep -qF -- "$1" <<<"$out" || { echo "FAIL: missing: $1"; fail=1; }; }
hasnt() { ! grep -qF -- "$1" <<<"$out" || { echo "FAIL: unexpected: $1"; fail=1; }; }
has "2 changed, 1 added, 3 removed"
has '`docs/a.md#changing-one` (changed)'
has '- `docs/a.md#brand-new-thing-v2`'   # unmapped; slug drops punctuation
has '`docs/a.md#going-away` (removed)'
has '`docs/b.md#part` (changed)'                # mapped via file-level Source
has '**`tests/fixtures/docs_diff/skills/s1/references/r1.md`**'
has '**`tests/fixtures/docs_diff/skills/s1/references/r2.md`**'
hasnt '**`tests/fixtures/docs_diff/skills/s1/references/r3.md`**'  # cites only an unchanged section
has '`docs/a.md#going-away`'
has 'r1.md`: `docs/a.md#going-away`'           # dangling anchor
has 'r2.md`: `docs/gone.md`'                   # dangling file-level
hasnt 'not-a-heading'                          # fenced heading ignored
[ $fail -eq 0 ] && echo "docs_diff: OK" || { echo "$out"; exit 1; }
