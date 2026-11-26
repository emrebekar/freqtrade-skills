# Freqtrade Skills

Agent Skills (the open `SKILL.md` format) that help an AI coding agent develop [Freqtrade](https://www.freqtrade.io) strategies: set up and configure a bot, write strategies and callbacks, backtest, tune with hyperopt, use FreqAI, migrate old strategies, and check for lookahead bias and recursive-indicator bugs before anything runs on a live account. The skills work in any harness that supports Agent Skills; for the rest, `AGENTS.md` indexes them.

## Skills

| Skill | Use it when you want to |
|-------|-------------------------|
| `freqtrade-setup` | install Freqtrade (Docker or native), create the user dir and config, generate a strategy, download and list data |
| `freqtrade-config` | edit `config.json`: keys, secrets, pairlists, protections, pricing, exchange notes |
| `freqtrade-strategy` | write an `IStrategy` class: indicators, signals, ROI/stoploss, informative pairs, shorting and leverage |
| `freqtrade-callbacks` | add callbacks: `custom_stoploss`, `custom_exit`, `adjust_trade_position`, order and entry/exit confirmation hooks |
| `freqtrade-backtesting` | run and read backtests, use `--timeframe-detail`, `--breakdown`, exports and plots |
| `freqtrade-validation` | run `lookahead-analysis` and `recursive-analysis`, interpret results, fix the common causes |
| `freqtrade-hyperopt` | tune parameters, pick spaces and loss functions, avoid overfitting |
| `freqtrade-freqai` | build FreqAI machine-learning strategies and avoid training leakage |
| `freqtrade-migration` | move old (interface v2) strategies and configs to v3 |

## Install

Every skill is a folder under `skills/`. Install the nine folders by one of the routes below.

**Claude Code** (plugin marketplace):

```text
/plugin marketplace add emrebekar/freqtrade-skills
/plugin install freqtrade-skills@freqtrade-skills
```

Or copy `skills/*` into `~/.claude/skills/` (all projects) or `.claude/skills/` (one repository).

**OpenAI Codex CLI:** copy `skills/*` into `~/.agents/skills/` (user) or `<repo>/.agents/skills/` (project).

**Cursor:** copy `skills/*` into `~/.cursor/skills/` or `~/.agents/skills/` (user), or `<repo>/.cursor/skills/` or `<repo>/.agents/skills/` (project).

**Gemini CLI:** copy `skills/*` into `~/.gemini/skills/` or `~/.agents/skills/` (user), or `<repo>/.gemini/skills/` or `<repo>/.agents/skills/` (workspace).

**GitHub Copilot** (CLI, cloud agent, VS Code agent mode and others, depending on version): copy `skills/*` into `~/.copilot/skills/` or `~/.agents/skills/` (personal), or `<repo>/.github/skills/`, `<repo>/.claude/skills/` or `<repo>/.agents/skills/` (project).

**Any other agent** (cross-agent installer, needs Node.js):

```text
npx skills add emrebekar/freqtrade-skills
```

Add `-g` for a global install and `-a <agent>` to pick the target agent.

**No native skill support:** point your agent at `AGENTS.md`.

## How the skills keep you safe

Every development skill carries a validation gate. An agent using these skills will not call a strategy finished, and will not suggest a dry-run or live run, until `freqtrade lookahead-analysis` and `freqtrade recursive-analysis` both pass. The one documented exception is FreqAI: `set_freqai_targets()` legitimately looks ahead and is reported as a false positive, so only the other columns count. `freqtrade-validation` explains each result and how to fix the usual causes (`shift(-1)`, whole-column statistics, `iloc`, resampling, merges, startup candles).

## Tested against

- Freqtrade `2026.10`
- Freqtrade docs commit `4cf0351e08d26e96a6429ef48103b726bb230cf8` (recorded in `freqtrade-version.json`)
- Docker images `freqtradeorg/freqtrade:2026.10` and `freqtradeorg/freqtrade:2026.10_freqai`

## Running the tests

Needs Docker only; no host Python. Scripts run inside the pinned image.

```bash
bash tests/run_all.sh                 # every strategy in tests/strategies.json: backtest + lookahead + recursive
bash tests/run_checks.sh SampleSmoke  # one strategy
bash tests/run_hyperopt.sh HyperoptExample
bash tests/test_validate_skills.sh && bash tests/test_check_cli.sh && bash tests/test_docs_diff.sh
scripts/dpy.sh scripts/validate_skills.py && scripts/dpy.sh scripts/check_cli.py
```

Slow manual suites (also available as the `slow` job via `workflow_dispatch` in CI): `tests/test_lookahead_fixtures.sh`, `tests/test_migration_fixtures.sh`, `tests/test_freqai_fixtures.sh`. CI is `.github/workflows/test.yml`.

## Refreshing for a new Freqtrade release

`.github/workflows/release-watch.yml` runs weekly (and on demand). When Freqtrade publishes a newer stable release than `freqtrade-version.json`, it tests the skills against the new image (`FT_IMAGE` for `scripts/dpy.sh`, `FT_TAG` for `tests/run_all.sh`), runs `scripts/docs_diff.py` and opens an issue titled `Freqtrade <tag> released: refresh skills`. The issue lists changed doc sections mapped to the reference files whose `Source:` lines cite them, plus dangling anchors. The rewrite itself is always a reviewed PR; nothing is committed automatically. Locally: `scripts/dpy.sh` cannot clone (the image has no git), so run `python3 scripts/docs_diff.py --old 2026.9 --new 2026.10` on a host with Python and git, or pass `--old-dir/--new-dir`. Self-test: `bash tests/test_docs_diff.sh`. `scripts/validate_skills.py` fails on any `freqtradeorg/freqtrade` image in a skill whose tag is not the `freqtrade-version.json` release (or a `_flavour` of it), so a missed bump, `latest`, `develop`, `stable` or an untagged image cannot merge.

## Contributing

Issues and pull requests are welcome. Keep `SKILL.md` frontmatter to `name`, `description` and `license`, no harness-specific syntax, and run the validation and test commands above before opening a PR.

## Disclaimer

Not financial advice. Always dry-run before live trading.

Example strategies are teaching examples and lose money on the test data.

## License and attribution

GPL-3.0, see `LICENSE`. The skills are derived from the [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) documentation (GPL-3.0); each skill ends with the docs version it was built from.

Design: [docs/superpowers/specs/2026-11-21-freqtrade-skills-design.md](docs/superpowers/specs/2026-11-21-freqtrade-skills-design.md)
