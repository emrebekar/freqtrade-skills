#!/usr/bin/env bash
# Self-test for validate_skills.py. CI: PY=python bash tests/test_validate_skills.sh
set -u
cd "$(dirname "$0")/.."
PY="${PY:-scripts/dpy.sh}"
V="scripts/validate_skills.py"
fail=0

out=$($PY $V --root tests/fixtures/skills_bad --agents tests/fixtures/skills_good/AGENTS.md 2>&1); rc=$?
[ "$rc" -eq 1 ] || { echo "FAIL bad root: exit $rc, want 1"; fail=1; }
for pat in "bad-name/SKILL.md: name .*invalid" "description missing" "references/missing.md" "AGENTS" "footer-not-last/SKILL.md: footer" "skills_bad/good: not listed" "freqtrade:latest. is not the pinned" "freqtrade:(no tag). is not the pinned" "freqtrade:2026.9. is not the pinned release tag (want 2026.10)"; do
  echo "$out" | grep -q "$pat" || { echo "FAIL bad root: no '$pat' error"; fail=1; }
done

mkdir -p tests/out && echo "{}" > tests/out/ver-bad.json
out=$($PY $V --root tests/fixtures/skills_good --agents tests/fixtures/skills_good/AGENTS.md --version-file tests/out/ver-bad.json 2>&1); rc=$?
[ "$rc" -eq 1 ] && echo "$out" | grep -q "no 'tag'" || { echo "FAIL bad version file: exit $rc, out: $out"; fail=1; }

out=$($PY $V --root tests/fixtures/skills_good --agents tests/fixtures/skills_good/AGENTS.md 2>&1); rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL good root: exit $rc"; echo "$out"; fail=1; }

[ "$fail" -eq 0 ] && echo "OK: validator self-test passed"
exit $fail
