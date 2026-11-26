#!/usr/bin/env bash
# Self-test for scripts/bump_version.py on a copy of tests/fixtures/bump (no network: --docs-commit or a bad --repo-url).
set -uo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-scripts/dpy.sh}"
F=tests/fixtures/bump; T=tests/out/bump
fail=0
bad() { echo "FAIL: $1"; fail=1; }
fresh() { rm -rf "$T" "$T.orig"; mkdir -p tests/out; cp -r "$F" "$T"; sed -i 's/$/\r/' "$T/skills/x/references/r.md"; cp -r "$T" "$T.orig"; }
bump() { $PY scripts/bump_version.py "$@" --root "$T" 2>&1; }

fresh
out=$(bump 2026.11 --docs-commit abc123); rc=$?
[ $rc -eq 0 ] || bad "bump exit $rc: $out"
grep -rq --exclude=test_bump_version.sh '2026\.10' "$T" && bad "old tag left: $(grep -rn '2026\.10' "$T")"
grep -q 'Pinned Freqtrade release: 2026.11\.' "$T/skills/x/SKILL.md" || bad "pinned line not bumped"
grep -q 'docs 2026.11 (abc123)\. Source: https://github.com/freqtrade/freqtrade/tree/2026.11/docs' "$T/skills/x/SKILL.md" || bad "footer not bumped"
grep -q 'removed in 2019.9; timerange 20261001-20261101' "$T/skills/x/SKILL.md" || bad "historical version or timerange changed"
grep -q 'freqtrade 2026.11`' "$T/skills/x/SKILL.md" || bad "version output not bumped"
[ "$(grep -c $'\r' "$T/skills/x/references/r.md")" -gt 0 ] || bad "CRLF lost"
grep -q '"tag": "2026.11"' "$T/freqtrade-version.json" && grep -q '"image": "freqtradeorg/freqtrade:2026.11"' "$T/freqtrade-version.json" && grep -q '"docs_commit": "abc123"' "$T/freqtrade-version.json" || bad "json not bumped"
grep -q "fixture tag: 2026.10" "$T/tests/test_bump_version.sh" || bad "bump self-test was rewritten"
grep -q '2026.11_freqai' "$T/tests/strategies.json" && grep -q 'freqtrade:2026.11}' "$T/scripts/dpy.sh" || bad "pin files not bumped"

cp -r "$T" "$T.once"
out=$(bump 2026.11 --docs-commit abc123); rc=$?
[ $rc -eq 0 ] || bad "same-tag bump exit $rc: $out"
diff -r "$T.once" "$T" >/dev/null || bad "same-tag bump changed files"
rm -rf "$T.once"

out=$(bump 2026.x --docs-commit abc123); rc=$?
[ $rc -eq 1 ] || bad "bad tag exit $rc"

fresh
sed -i 's/^# X$/# X\n\nReal output on 2026.10 here./' "$T/skills/x/SKILL.md"; rm -rf "$T.orig"; cp -r "$T" "$T.orig"
out=$(bump 2026.11 --docs-commit abc123); rc=$?
[ $rc -eq 1 ] || bad "leftover exit $rc"
grep -q 'SKILL.md:9' <<<"$out" || bad "leftover not reported: $out"
diff -r "$T.orig" "$T" >/dev/null || bad "leftover run wrote files"

fresh
out=$(bump 2026.11 --repo-url tests/out/not-a-repo); rc=$?
[ $rc -eq 1 ] || bad "unresolvable docs commit exit $rc: $out"
diff -r "$T.orig" "$T" >/dev/null || bad "unresolvable run wrote files"

rm -rf "$T" "$T.orig"
[ $fail -eq 0 ] && echo "OK: bump_version self-test passed"
exit $fail
