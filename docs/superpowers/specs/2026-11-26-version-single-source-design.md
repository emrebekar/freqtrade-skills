# Single source for the pinned Freqtrade version

## Intent
Stop hand-editing `2026.10` in 34 skill files every release. The pinned release lives in `freqtrade-version.json` only; every other mention is either derived by a script or replaced by wording that needs no version.

## Goals
- `freqtrade-version.json` is the one place a human sets the version.
- Shipped markdown keeps literal, copy-pasteable image tags (installed skills have no access to the JSON at read time).
- One command bumps every remaining mention; CI fails if a mention is stale or a new hand-written one appears.

## Non-goals / anti-goals
- No templates or generated skill tree (two copies of every file, sync checks).
- No runtime "latest release" lookup: it breaks the pinning from PR #2 and makes sample outputs lie.
- Historical versions ("removed in 2019.9", "deprecated in 2025.12" in freqtrade-migration, freqai models.md) are content, not the pin: never rewritten or flagged.
- A bump must not claim outputs were re-observed: the bump PR comes from release-watch after the skills were tested on the new image.

## Approaches
1. **Chosen: one source, bump script and validator enforcement.** Prose loses its version; remaining mentions are machine-bumped.
2. Build-time templates (`skills-src/` with `{{FT_TAG}}` rendered to `skills/`): zero hand-written versions, but two trees and edits to the wrong copy. Too heavy for one variable.
3. Agent finds the latest release at run time: no version in files, but reverses pinning and loses reproducibility.

## Design
**Allowed forms of the pinned version in `skills/`** (everything the bump script rewrites):
- image tags `freqtradeorg/freqtrade:<tag>[_flavour]` and bare flavour tags in backticks (`` `<tag>_freqai` ``);
- one line per SKILL.md replacing "Freqtrade version assumed: <tag>": `Pinned Freqtrade release: <tag>.`;
- the footer `Built from Freqtrade docs <tag> (<docs_commit>). Source: .../tree/<tag>/docs`;
- commands that must name it (`git checkout <tag>` in install-native.md, the compose `sed` line).

**Prose rewrite (one-time, by hand):** about 75 provenance mentions ("on 2026.10", "from the 2026.10 help", "in the 2026.10 image") become "on the pinned release", "from the pinned release's help", "in the pinned image". Same for the comment in `tests/check_results.py`.

**`scripts/bump_version.py NEW_TAG [--docs-commit SHA]`** (stdlib only):
- reads the old tag from `freqtrade-version.json`;
- resolves the docs commit with `git ls-remote https://github.com/freqtrade/freqtrade refs/tags/NEW_TAG` unless `--docs-commit` is given;
- rewrites the allowed forms in `skills/**/*.md` and the old tag in the non-skill pin files: `freqtrade-version.json`, `.github/workflows/*.yml`, `scripts/dpy.sh`, `tests/*.sh`, `tests/strategies.json`, `tests/check_results.py`, `tests/fixtures/**/SKILL.md`, `README.md`;
- then fails, listing `file:line`, if the old tag still appears anywhere in those files (catches a form the rewrite missed);
- never touches `docs/superpowers/` (historical plans and specs).

**Validator (`validate_skills.py`) additions:**
- each SKILL.md has exactly one `Pinned Freqtrade release: <pinned>.` line, and the footer tag equals the pinned one;
- the pinned literal appears in `skills/` only in the allowed forms; any other occurrence fails as "hand-written version, use 'the pinned release'". Historical versions are not the pinned literal, so they pass untouched.

**Release flow:** release-watch already tests the new image and opens an issue; the refresh PR runs `scripts/bump_version.py <tag>` and updates the issue's text ("run bump_version.py" replaces "git grep and bump every hit").

## Builder's calls
- Exact regex for "allowed forms" and the replacement wording per sentence.
- Self-test for the bump script: a temp copy of fixture files bumped from 2026.10 to 2026.11 with `--docs-commit`, asserting no `2026.10` remains and historical versions are unchanged.
- Delivery: same branch as PR #2 (`fix/pin-docker-image`), since it builds on the image-tag check there (my call).
