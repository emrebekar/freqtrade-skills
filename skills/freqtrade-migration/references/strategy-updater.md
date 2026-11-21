Source: docs/commands/strategy-updater.md
Source: docs/strategy_migration.md

# strategy-updater

`freqtrade strategy-updater` rewrites strategy files to the v3 interface automatically. The docs page is only the `--help` output; the behavior below is `observed` on the 2026.10 image ([tests/test_migration_fixtures.sh](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/test_migration_fixtures.sh) and the scratch runs under tests/out/updater*, plus reading the shipped `freqtrade/strategy/strategyupdater.py`). Treat the updater as a first pass to diff and fix by hand, never as the migration.

## Usage

```bash
freqtrade strategy-updater --strategy-list MyStrategy --strategy-path user_data/strategies
freqtrade strategy-updater --strategy-list MyStrategy OtherStrategy --recursive-strategy-search
```

Options (from `--help`): `--strategy-list STRATEGY [STRATEGY ...]` (strategies to convert), `--strategy-path PATH` (additional lookup path), `--recursive-strategy-search`, plus the common `-c`, `-d`, `--userdir`, `-v`, `--no-color`, `--logfile`.

Observed behavior:

- It edits the source file in place. Before that it copies the original to `<userdir>/strategies_orig_updater/<file>` (observed: the file name is the same, with no date, so a second run overwrites the backup with the already converted file). Run it on a copy, or commit first, and `diff` the result.
- It prints `Conversion of <file> started.` and `... took 0.1 seconds.` and exits without validating the result. Always load and backtest afterwards.
- It does not need data or a trading config; `--userdir` must point at an existing user directory (`freqtrade create-userdir --userdir DIR`).

## What it converts (observed)

Run on [tests/fixtures/strategies/LegacyV2.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/fixtures/strategies/LegacyV2.py) (the test script uses a copy under tests/out/migration/updated/). `trade.nr_of_successful_buys` to `trade.nr_of_successful_entries` is asserted by the script too.

- Adds `INTERFACE_VERSION = 3` as the first class member (or sets an existing value to 3). Only for classes whose base is literally `IStrategy`.
- Method names: `populate_buy_trend`, `populate_sell_trend`, `custom_sell`, `check_buy_timeout`, `check_sell_timeout`.
- Dataframe columns `buy`, `sell`, `buy_tag`, as names or string subscripts/lists (`["buy", "buy_tag"]` becomes `['enter_long', 'enter_tag']`).
- Settings: `use_sell_signal`, `sell_profit_only`, `sell_profit_offset`, `ignore_roi_if_buy_signal`, `forcebuy_enable`, `ticker_interval` (to `timeframe`).
- The keys `buy` / `sell` in `order_types`, `order_time_in_force`, `unfilledtimeout` become `entry` / `exit`.
- The argument name `sell_reason` to `exit_reason` (as in `confirm_trade_exit`).
- `trade.nr_of_successful_buys` to `trade.nr_of_successful_entries`.
- `space="buy"` / `space="sell"` in hyperopt parameters are intentionally left alone (the updater skips `space=` keywords).
- A `numpy` `NaN` / `NAN` to `nan` replacement (NumPy 2).

The converted LegacyV2 backtested with identical trades to the original and to the hand-migrated [tests/strategies/MigratedV3.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/MigratedV3.py) (200 trades each, same pairs, dates, rates, profits and exit reasons).

## What it does NOT convert (observed)

Items 1 to 4 are reproducible from the repo: the fixture [tests/fixtures/strategies/LegacyV2.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/fixtures/strategies/LegacyV2.py) contains each pattern and [`tests/test_migration_fixtures.sh`](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/test_migration_fixtures.sh) asserts the gap on the converted copy. Items 5 and 6 come from reading the updater source, not from a run. Also grep yourself for exit reason strings such as `sell_signal`, `custom_sell`, `force_sell`, `emergency_sell` in comparisons.

1. `order_types` keys `emergencysell`, `forcesell`, `forcebuy` stay unchanged (`emergency_exit`, `force_exit`, `force_entry` are the new names). Freqtrade still logs a `DEPRECATED` warning for them.
2. No `side` argument is added to `custom_stake_amount`, `confirm_trade_entry` or `custom_entry_price`, and `custom_entry_price` does not get the `trade` argument. Old signatures keep working only because of `**kwargs`; futures and shorts need `side`.
3. `stoploss_from_open` / `stoploss_from_absolute` get no `is_short` (or `leverage`) argument.
4. `trade.sell_reason` is not renamed to `trade.exit_reason` (an attribute access; the argument name `sell_reason` is renamed, the attribute is not).
5. Config files: it edits strategy `.py` files only. `bid_strategy`, `ask_strategy`, webhook and Telegram keys in the JSON config are untouched (see v2-to-v3.md).
6. No `can_short`, `enter_short` or `exit_short` are added. FreqAI `populate_any_indicators` is not converted (not tested here; the updater source has no rule for it).

## What it breaks or changes silently (observed hazards)

Scratch-only, not reproducible from the repo (run on a throwaway strategy, tests/out/updater2/, not committed; these patterns break a running strategy so they are not in the fixtures; re-run them yourself before relying on the exact output):

- A local variable named `sell` or `buy` is renamed where it is assigned (`sell = ...` became `exit_long = ...`) but not where it is used inside a subscript (`dataframe.loc[sell, ...]` stayed `sell`). Result: `NameError` at run time. Grep for any variable or function argument named `buy`, `sell`, `buy_tag`.
- Every string constant equal to `buy` or `sell` is rewritten to `entry` / `exit`, and every string equal to a mapped name is rewritten too. Observed: the tag in `(1, "buy")` became `'entry'`. A tag, exit reason or dict key named `buy` / `sell` changes value silently, which can change logic that compares tags.
- The file is regenerated from the syntax tree: quotes become single, blank lines and wrapped lines are collapsed, `-0.10` becomes `-0.1`, long conditions are joined onto one line, and the file loses its final newline. Comments were kept in the runs here, but expect a noisy diff. Behavior stayed the same on the fixture.

## Recommended use

1. Copy the strategy; run the updater on the copy.
2. `diff` old against new; fix every item in "does NOT convert" and "hazards" by hand, using v2-to-v3.md.
3. Backtest old and new on the same timerange and compare trades (workflow in SKILL.md).
4. Run the validation gate (lookahead and recursive analysis) before any dry run.
