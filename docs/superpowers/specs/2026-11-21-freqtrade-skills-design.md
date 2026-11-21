# Freqtrade Skills — Design

Date: 2026-11-21
Status: approved 2026-11-21

## Intent

A public GitHub repo of agent skills that make any AI coding assistant good at
**developing Freqtrade strategies**: from an empty folder to a strategy that is
written, backtested, optimized, and validated free of lookahead bias.
Audience: anyone writing Freqtrade strategies, using whatever agent harness they
prefer.

## Goals

- Cover the full strategy-development loop, including FreqAI.
- Work in every harness that supports the open Agent Skills format
  (`SKILL.md` + frontmatter): Claude Code, Codex, Cursor, Gemini CLI, GitHub
  Copilot, and others.
- Accurate to the official Freqtrade docs; every skill states the docs version
  it was built from.
- Push users toward safe practice: no strategy is "done" until it passes
  `lookahead-analysis` and `recursive-analysis`.

## Non-goals

- Running a bot in production: Telegram, REST API, webhooks, FreqUI,
  producer/consumer, Docker ops beyond quickstart.
- Contributing to Freqtrade itself (`developer.md`).
- Trading advice, "profitable strategy" claims, or ready-to-run money-making
  strategies.

## Anti-goals (failure even if it works)

- Skills that encourage going live on unvalidated backtests.
- Skills that hallucinate config keys, callback signatures, or CLI flags not in
  the docs.
- Harness lock-in: anything that only works in Claude Code.
- Bloat: dumping raw docs so the agent drowns in context.

## Constraints

- Source: `freqtrade/freqtrade` docs. Freqtrade is GPL-3.0; skills reuse code
  examples from the docs, so this repo is **GPL-3.0** with attribution.
- Agent Skills spec: frontmatter only `name` + `description` (plus optional
  standard fields like `license`); no harness-specific fields in `SKILL.md`.
  `name` is lowercase-hyphenated and matches the folder.
- `gh` CLI is not installed on the build machine; publishing needs `gh` or a
  manually created remote + `git push`.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **A (picked)** | ~9 focused skills, each a lean `SKILL.md` + `references/` distilled from docs; Agent Skills standard first, Claude plugin manifest as an extra layer | More files to maintain; best triggering and least context |
| B | One umbrella `freqtrade` skill routing to ~15 reference files | Simplest; triggers on everything, heavy root file |
| C | Raw docs copied into skills | Easy refresh; ~15k lines of noise, poor agent performance |

Picked A because the user wants it usable in every harness and by every
strategy developer; focused skills trigger precisely and keep context small.

## Design

### Repo layout

```
freqtrade-skills/
├── README.md                  # what, install per harness, docs version, disclaimer
├── LICENSE                    # GPL-3.0
├── AGENTS.md                  # fallback for harnesses without skill support: index of skills
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json       # Claude Code: /plugin marketplace add <owner>/freqtrade-skills
├── skills/
│   ├── freqtrade-setup/
│   ├── freqtrade-strategy/
│   ├── freqtrade-callbacks/
│   ├── freqtrade-config/
│   ├── freqtrade-backtesting/
│   ├── freqtrade-hyperopt/
│   ├── freqtrade-validation/
│   ├── freqtrade-freqai/
│   └── freqtrade-migration/
├── freqtrade-version.json     # pinned stable tag + docs commit
├── scripts/
│   ├── validate_skills.py     # frontmatter + links
│   └── docs_diff.py           # doc changes between tags, mapped to skills
├── tests/
│   ├── strategies/            # example strategies from the skills
│   ├── data/                  # small committed OHLCV sample
│   └── config.test.json
└── .github/workflows/
    ├── test.yml               # validate + run strategies on pinned Freqtrade
    └── release-watch.yml      # weekly: new release → test + diff → issue
```

### Skills and their sources

| Skill | Job | Main docs |
|---|---|---|
| `freqtrade-setup` | install, userdir, new config/strategy, download data | installation, docker_quickstart, commands/create-userdir, new-config, new-strategy, data-download |
| `freqtrade-strategy` | write `IStrategy`: indicators, entry/exit, ROI, stoploss, informative pairs, DataProvider, shorting/leverage | strategy-101, strategy-customization, strategy-advanced, stoploss, leverage, trade-object, includes/strategy-imports |
| `freqtrade-callbacks` | custom_stoploss, custom_exit, custom_roi, stake, position adjust, order price/timeout, confirm callbacks | strategy-callbacks |
| `freqtrade-config` | config.json, pairlists, protections, pricing, exchange notes | configuration, includes/pairlists, includes/protections, includes/pricing, exchanges |
| `freqtrade-backtesting` | run + read backtests, analysis, plotting | backtesting, advanced-backtesting, commands/backtesting*, plotting, data-analysis |
| `freqtrade-hyperopt` | parameter spaces, loss functions, reading results, overfitting caution | hyperopt, advanced-hyperopt, commands/hyperopt* |
| `freqtrade-validation` | lookahead + recursive analysis, common mistakes checklist | lookahead-analysis, recursive-analysis, strategy-customization "common mistakes", faq |
| `freqtrade-freqai` | FreqAI config, feature engineering, models, running, RL | freqai, freqai-configuration, freqai-feature-engineering, freqai-running, freqai-reinforcement-learning, freqai-parameter-table |
| `freqtrade-migration` | update old strategies to current interface | strategy_migration, deprecated, commands/strategy-updater |

### Skill shape

- `SKILL.md` under ~300 lines: when to use, workflow steps, the CLI commands
  for the task, top pitfalls, pointers to reference files.
- `description` is written for triggering: names the tasks and Freqtrade terms
  a user would say.
- `references/*.md`: distilled facts, signatures, config keys, and verified
  code examples from the docs. Agent loads only when needed.
- Each `SKILL.md` ends with: `Built from Freqtrade docs <ref> (<date>). Source: <link>`.
- Cross-skill handoff in text ("after writing, use freqtrade-validation"),
  never harness-specific invocation syntax.

### Accuracy check (user decision: test the code)

- Every callback signature, config key, and CLI flag is checked against the
  docs (and `docs/commands/*` for CLI).
- Code is **executed** against a pinned Freqtrade stable install:
  - `tests/strategies/`: one minimal example strategy per relevant skill
    (strategy, callbacks, hyperopt, freqai, migration output), built from the
    skill's own examples.
  - Each runs through `backtesting`, `lookahead-analysis`,
    `recursive-analysis`; hyperopt runs a few epochs; FreqAI runs a short
    backtest with a light model.
  - Python snippets in `references/` are at least syntax/import-checked.
  - CLI commands shown in skills are checked with `--help` for flag existence.
- CI (`.github/workflows/test.yml`) runs all of this on push/PR.
- Builder's call: commit a small sample OHLCV dataset in `tests/data/`
  instead of downloading in CI (exchange APIs often geo-block CI runners).

### Validation gate (builder's call)

Hard rule in every development skill: never call a strategy finished, nor
suggest dry-run/live, until `lookahead-analysis` and `recursive-analysis` pass.
Skills route to `freqtrade-validation` at the end of their workflow.
Documented exception: FreqAI targets from `set_freqai_targets()` are falsely
flagged by lookahead-analysis (per docs).

### Refresh on new release (user decision)

- `freqtrade-version.json` pins the stable tag and docs commit the skills
  were built from.
- Each reference file lists its source doc sections (`Source: docs/x.md#y`).
- `scripts/docs_diff.py <old-tag> <new-tag>`: shows changed doc sections and
  which skills/reference files they map to.
- Scheduled workflow (`.github/workflows/release-watch.yml`, weekly): detects a
  new Freqtrade stable release, runs the test suite against it, and opens an
  issue with the test result + docs diff mapped to skills.
- Builder's call: the content rewrite itself stays a human/agent-reviewed PR,
  not auto-committed, so wrong trading info never ships unreviewed.

## Decided by the user

- Audience: everyone who develops Freqtrade strategies.
- Scope: strategy development lifecycle; FreqAI included.
- Must work on any harness the user prefers.
- Publish on GitHub.
- Code examples are tested on a real Freqtrade install.
- A new Freqtrade release triggers a skills refresh.

## Builder's calls (marked as proposals)

- Docs version: build from the latest **stable** release docs, not `develop`
  (`2026.11-dev` at `a025e7f`), since most users run stable. Check out the
  stable tag before distilling content.
- 9-skill split as in the table above.
- GPL-3.0 license.
- Install docs in README for: Claude Code (plugin marketplace + manual copy),
  Codex, Cursor, Gemini CLI, Copilot, and generic "copy `skills/<name>` into
  your agent's skills folder"; `npx skills add <owner>/freqtrade-skills` if the
  cross-agent installer supports it at build time (verify).
- README carries a "not financial advice; dry-run before live" disclaimer.

## Left to the builder

- Exact per-harness skill install paths (verify against each harness's current
  docs at build time).
- Reference file split inside each skill.
- Wording of descriptions and pitfalls.
- GitHub owner/repo name and publish mechanics (needs user's GitHub account).
