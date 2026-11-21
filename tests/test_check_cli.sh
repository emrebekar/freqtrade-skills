#!/usr/bin/env bash
# Self-test for check_cli.py. CI: PY=python bash tests/test_check_cli.sh
set -u
cd "$(dirname "$0")/.."
PY="${PY:-scripts/dpy.sh}"
C="scripts/check_cli.py"
fail=0

out=$($PY $C --root tests/fixtures/skills_badcli 2>&1); rc=$?
[ "$rc" -eq 1 ] || { echo "FAIL bad fixture: exit $rc, want 1"; fail=1; }
echo "$out" | grep -q "fake-cli/SKILL.md:4: --fake-flag not in freqtrade backtesting" || { echo "FAIL bad fixture: no --fake-flag error"; fail=1; }
echo "$out" | grep -q "unknown subcommand not-a-command" || { echo "FAIL bad fixture: no unknown subcommand error"; fail=1; }

out=$($PY $C --root tests/fixtures/skills_goodcli 2>&1); rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL good fixture: exit $rc"; echo "$out"; fail=1; }

out=$($PY $C --root tests/fixtures/skills_emptycli 2>&1); rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL empty root: exit $rc"; echo "$out"; fail=1; }

out=$($PY $C --root tests/fixtures/does_not_exist 2>&1); rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL missing root: exit $rc"; echo "$out"; fail=1; }

[ "$fail" -eq 0 ] && echo "OK: check_cli self-test passed"
exit $fail
