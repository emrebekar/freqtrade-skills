# Single-source Pinned Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `freqtrade-version.json` becomes the only hand-set version; skill prose drops its version, the remaining mentions are rewritten by one script, and the validator rejects stray ones.

**Architecture:** Validator learns the "allowed forms" of the pinned literal and a per-SKILL.md pinned line. A one-time prose edit makes `skills/` pass. A stdlib bump script rewrites allowed forms plus the non-skill pin files and fails on leftovers.

**Tech Stack:** Python 3 stdlib, bash self-tests (repo pattern: `tests/test_*.sh`, `PY=scripts/dpy.sh`), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-26-version-single-source-design.md`

## Global Constraints

- Branch `fix/pin-docker-image` (PR #2). Stdlib only. Scripts must run under `scripts/dpy.sh` (image has no git; repo mounted at `/repo`, so temp files go under `tests/out/`).
- Pinned line text, exactly: `Pinned Freqtrade release: <tag>.` — one per SKILL.md (all 9 skills, including freqtrade-migration).
- Footer form unchanged: `Built from Freqtrade docs <tag> (<docs_commit>). Source: https://github.com/freqtrade/freqtrade/tree/<tag>/docs`.
- Historical versions (any version other than the pinned one) are never rewritten or flagged.
- `docs/superpowers/` is never touched by the bump script.
- Docs commit for a tag = `git ls-remote https://github.com/freqtrade/freqtrade refs/tags/<tag>` (verified: 2026.10 -> `4cf0351e08d26e96a6429ef48103b726bb230cf8`, matches `freqtrade-version.json`).
- Provenance wording: "on the pinned release", "from the pinned release's help", "in the pinned image".

## Review Focus

- Pinned literal inside a longer number (`2026.100`, `12026.10`) must not count as a mention: match with `(?<![\d.])P(?!\d)`. Test in Task 1.
- `2026.10` inside the footer URL `tree/2026.10/docs` is an allowed form. Test in Task 1 (good fixture footer passes).
- Bump to the current tag must be a no-op that exits 0, not a "leftover" failure. Test in Task 3.
- Bump whose docs commit cannot be resolved must exit 1 and change no file. Test in Task 3.
- CRLF files on Windows checkouts keep their line endings after a bump (read/write with `newline=""`). Test in Task 3.

---

### Task 1: Validator rules for the pinned line and stray versions

**Files:**
- Modify: `scripts/validate_skills.py` (`check_skill`, module constants)
- Modify: `tests/fixtures/skills_good/good-skill/SKILL.md`, `tests/fixtures/skills_goodcli/real-cli/SKILL.md` (add pinned line so they stay valid)
- Create: `tests/fixtures/skills_bad/stray-version/SKILL.md`
- Test: `tests/test_validate_skills.sh`

**Interfaces:**
- Consumes: `pinned` (str) already passed into `check_skill(d, agents_text, pinned=None)`.
- Produces: `PIN_LINE_FMT = "Pinned Freqtrade release: {}."` and `allowed_spans(text: str, pinned: str) -> list[tuple[int, int]]` in `scripts/validate_skills.py`; Task 3 imports both (insert `scripts/` into `sys.path`).

Allowed forms (regexes built with `P = re.escape(pinned)`): `freqtradeorg/freqtrade:P(_[a-z]+)?`, `` `P_[a-z]+` ``, the pinned line, the footer line, `git checkout P`, `freqtrade:P#` (compose sed). `allowed_spans` returns the character spans of all their matches.

- [ ] **Step 1: Add the failing cases.** `stray-version/SKILL.md`: valid frontmatter, pinned line, footer, prose `Real output on 2026.10 here.` and historical `removed in 2019.9`. In `tests/test_validate_skills.sh` append `"stray-version/SKILL.md:[0-9]*: hand-written version"` to the bad-root pattern list, and assert the bad-root output does not contain `2019.9`. Add `Pinned Freqtrade release: 2026.10.` before the footer in the two good fixtures.
- [ ] **Step 2: Run** `PY=scripts/dpy.sh bash tests/test_validate_skills.sh` — expect `FAIL bad root: no 'stray-version/SKILL.md:[0-9]*: hand-written version' error`.
- [ ] **Step 3: Implement.** When `pinned` is set: SKILL.md contains `PIN_LINE_FMT.format(pinned)` exactly once, else `"{p}: pinned line 'Pinned Freqtrade release: {pinned}.' missing or repeated"`; footer tag equals `pinned`, else `"{p}: footer tag != {pinned}"`; for SKILL.md and each reference, each match of `(?<![\d.])P(?!\d)` outside `allowed_spans` yields `"{file}:{line}: hand-written version '{pinned}', write 'the pinned release'"`.
- [ ] **Step 4: Run** the self-test — expect `OK: validator self-test passed`. `scripts/dpy.sh scripts/validate_skills.py` now fails on `skills/` (hand-written mentions, 9 missing pinned lines); expected until Task 2.
- [ ] **Step 5: Commit** `feat: validator rejects hand-written pinned version in skills` (do not push yet: `skills/` fails until Task 2).

### Task 2: One-time prose rewrite in skills

**Files:**
- Modify: every file the validator lists after Task 1 (about 34 under `skills/`); `tests/check_results.py` comment "Observed on 2026.10" -> "Observed on the pinned release".

**Interfaces:**
- Consumes: validator output from Task 1 as the work list.
- Produces: `skills/` passing the validator.

- [ ] **Step 1:** Replace each "Freqtrade version assumed: 2026.10" with `Pinned Freqtrade release: 2026.10.` (freqtrade-strategy: ", strategy interface version 3" becomes its own sentence). Add the pinned line to freqtrade-migration's SKILL.md intro.
- [ ] **Step 2:** Rewrite every hand-written mention with the Global Constraints wording, keeping meaning (e.g. "Real output on 2026.10 (IndicatorsExample…)" -> "Real output on the pinned release (IndicatorsExample…)"; install-native.md "use the 2026.10 release (`git checkout 2026.10`)" -> "use the pinned release (`git checkout 2026.10`)").
- [ ] **Step 3: Run** `scripts/dpy.sh scripts/validate_skills.py && PY=scripts/dpy.sh bash tests/test_validate_skills.sh` — expect exit 0 and `OK: validator self-test passed`. `git grep -c '2026\.10' skills` total about 46.
- [ ] **Step 4: Commit and push** `docs: state pinned release once per skill, drop hand-written versions`.

### Task 3: Bump script

**Files:**
- Create: `scripts/bump_version.py`, `tests/test_bump_version.sh`
- Create: `tests/fixtures/bump/` — `freqtrade-version.json`; `skills/x/SKILL.md` (image tag, pinned line, footer, `git checkout 2026.10`, historical `2019.9`); `skills/x/references/r.md` saved with CRLF; `scripts/dpy.sh` containing `freqtradeorg/freqtrade:2026.10`; `tests/strategies.json` with `2026.10` and `2026.10_freqai` images
- Modify: `.github/workflows/test.yml` validate job: add step `bump_version self-tests` running `bash tests/test_bump_version.sh`

**Interfaces:**
- Consumes: `PIN_LINE_FMT`, `allowed_spans` from Task 1.
- Produces: CLI `bump_version.py NEW_TAG [--docs-commit SHA] [--root DIR] [--repo-url URL]`. Exit 0 on success or same-tag no-op; exit 1 on bad tag (`^\d{4}\.\d{1,2}$`), unresolvable docs commit, or leftover old tag in skills (prints each `file:line`).

Targets relative to `--root` (default `.`): `freqtrade-version.json` (set `tag`, `image`, `docs_commit` via `json`); `skills/**/*.md` (rewrite only inside `allowed_spans`, footer gets the new docs commit); plain old-tag replace in `.github/workflows/*.yml`, `scripts/dpy.sh`, `tests/*.sh`, `tests/strategies.json`, `tests/check_results.py`, `tests/fixtures/**/SKILL.md`, `README.md`. Missing targets are skipped. Compute every new file content first, check skills for leftovers, then write; on any error write nothing.

- [ ] **Step 1: Write `tests/test_bump_version.sh`**, copying `tests/fixtures/bump` to a fresh `tests/out/bump` per case:
  - `2026.11 --docs-commit abc123`: exit 0; `grep -r 2026.10` finds nothing; `Pinned Freqtrade release: 2026.11.` present; footer has `docs 2026.11 (abc123)` and `tree/2026.11/docs`; `2019.9` unchanged; `r.md` still has CR bytes; JSON `tag` `2026.11`, `image` `freqtradeorg/freqtrade:2026.11`.
  - running the same command again: exit 0, `diff -r` against the first result is empty.
  - `2026.x`: exit 1.
  - prose `on 2026.10 here` added to SKILL.md: exit 1, output names `SKILL.md:`, tree unchanged (`diff -r` against fixture).
  - no `--docs-commit`, `--repo-url tests/out/not-a-repo`: exit 1, tree unchanged.
- [ ] **Step 2: Run** `PY=scripts/dpy.sh bash tests/test_bump_version.sh` — expect failure (script missing).
- [ ] **Step 3: Implement `scripts/bump_version.py`.** Docs commit via `subprocess.run(["git", "ls-remote", repo_url, f"refs/tags/{tag}"])`; empty output or missing git -> exit 1.
- [ ] **Step 4: Run** the self-test — expect `OK: bump_version self-test passed`. Real-repo check, then discard: `scripts/dpy.sh scripts/bump_version.py 2026.11 --docs-commit deadbeef && scripts/dpy.sh scripts/validate_skills.py; git checkout -- .` — expect both exit 0.
- [ ] **Step 5: Commit and push** `feat: add bump_version.py to rewrite the pinned release`.

### Task 4: Release flow and docs

**Files:**
- Modify: `.github/workflows/release-watch.yml:115` (issue text), `README.md:76`

- [ ] **Step 1:** Issue text: replace "run 'git grep -n 2026.10' and bump every hit (…)" with "run 'python3 scripts/bump_version.py <new tag>' (resolves the docs commit with git ls-remote), then re-observe outputs that changed".
- [ ] **Step 2:** README release section, one sentence: the version is set only in `freqtrade-version.json`; `scripts/bump_version.py NEW_TAG` rewrites image tags, pinned lines, footers and pin files; the validator rejects hand-written versions in skill prose.
- [ ] **Step 3: Run** `scripts/dpy.sh scripts/validate_skills.py && PY=scripts/dpy.sh bash tests/test_validate_skills.sh && PY=scripts/dpy.sh bash tests/test_bump_version.sh` — all exit 0. Push; `gh pr checks 2 --watch` — all pass.
- [ ] **Step 4: Commit and push** `docs: release flow uses bump_version.py`; update PR #2 description with the new sections.
