---
name: freqtrade-migration
description: Use when you need to update an old Freqtrade strategy or config (interface v2 or earlier) to the current interface version 3, fix DEPRECATED warnings, rename buy/sell to entry/exit, or run freqtrade strategy-updater. Covers populate_buy_trend to populate_entry_trend, populate_sell_trend to populate_exit_trend, buy/sell/buy_tag columns to enter_long/exit_long/enter_tag, custom_sell, check_buy_timeout, sell_reason, use_sell_signal, order_types, unfilledtimeout, bid_strategy, INTERFACE_VERSION, removed features (populate_any_indicators, edge, hdf5, ticker_interval), and checking that a migration kept the same trades.
license: GPL-3.0
---

# Freqtrade strategy migration (v2 to v3)

Updates old strategies and configs to the Freqtrade 2026.10 interface (strategy interface version 3). Users trade real money: a wrong rename can silently change trading behavior, so migrate in small steps and prove the result with a before and after backtest. The example pair (tests/fixtures/strategies/LegacyV2.py old, tests/strategies/MigratedV3.py migrated) was run on the repo's test data (BTC/USDT and ETH/USDT, 5m, 2026-08-01 to 2026-10-01). Both are teaching examples, not profitable strategies; never present their numbers as a result.

Rules:
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives. That is the only blanket exception: pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives; explain each, never silently ignore. A pass does not prove the strategy is clean (see freqtrade-validation).
- Keep `dry_run: true`. Never set `dry_run: false` unless the user explicitly asks.
- Migration is renaming plus new arguments, not a redesign. Do not change signal logic, ROI, stoploss or parameters while migrating; propose those separately.
- Keep a copy of the original strategy and its backtest result before changing anything.
- Read the whole old strategy and config first. Look names up in the references; do not invent renames. Label what you could not verify.
- If the user wants shorts or futures, the migration is required: with a non-spot `trading_mode` the 2026.10 loader rejects old setting names (observed). Futures and shorting also need `trading_mode`, `margin_mode` and `can_short = True`; leverage can liquidate the position, warn the user.

## What 2026.10 does with an old strategy (observed)

On the 2026.10 image, in spot mode, the legacy fixture (`populate_buy_trend`, `populate_sell_trend`, `buy`/`sell` columns, `custom_sell`, `check_buy_timeout`, `sell_reason`, `use_sell_signal` and the other old settings, old `order_types` keys) still loads and backtests, with `DEPRECATED` warnings for the old settings and keys. The migrated version gave identical trades (200 trades, same pairs, dates, rates, profits, exit reasons). Exceptions found:

- A legacy `buy_tag` column crashes the backtest: `ValueError: cannot reindex on an axis with duplicate labels`. Rename it to `enter_tag`.
- In non-spot trading modes the old setting names are errors, and per the shipped resolver source the old method names (`populate_buy_trend` without `populate_entry_trend`, `custom_sell`, `check_buy_timeout`, `check_sell_timeout`) raise `OperationalException`.

"Still runs" is not "migrated": the docs say the compatibility layer may be dropped later and that old `order_types` keys "will be removed in the next versions". Details: references/deprecated.md.

## Workflow

1. Inventory. Read the strategy and config. List old names with a search, for example `grep -nE "populate_buy_trend|populate_sell_trend|custom_sell|check_(buy|sell)_timeout|sell_reason|\bbuy\b|\bsell\b|buy_tag|use_sell_signal|sell_profit|ignore_roi_if_buy_signal|nr_of_successful_buys|bid_strategy|ask_strategy|ticker_interval|populate_any_indicators" <file>`. Check the config for the keys in references/v2-to-v3.md (pricing, webhook, Telegram, `unfilledtimeout`, `order_types`).
2. Baseline. Backtest the ORIGINAL on a fixed `--timerange` with `--export trades`; save the trade list and summary. If it does not load, record the error; the baseline is then "does not run" and you cannot claim equivalence. See freqtrade-backtesting.
3. Optional first pass with `freqtrade strategy-updater` on a COPY. It converts most names but misses things and can break code (see "strategy-updater" below). Diff the result; never trust it as the migration.
4. Migrate by hand, table in references/v2-to-v3.md, in this order: class and `INTERFACE_VERSION = 3`; method names; dataframe columns (`buy` to `enter_long`, `sell` to `exit_long`, `buy_tag` to `enter_tag`); strategy settings; `order_types` / `order_time_in_force` / `unfilledtimeout` keys; callback signatures (new `side`, `exit_reason`, `Order` type); helper calls (`is_short`); trade attributes; exit-reason string comparisons; config keys.
5. Check what the tool cannot see: variable names `buy`/`sell`, tag strings that equal an old name, `sell_reason` attribute reads, `order_types` keys `forcesell`/`forcebuy`/`emergencysell`.
6. Backtest the MIGRATED strategy on the same `--timerange` with the same config and `--export trades`. Compare trade count, then pairs, open/close dates, rates, profit and exit reasons. Pure renaming should give identical trades. If they differ, find the cause before going on; the usual ones are a changed string compared in logic, a renamed variable that shadowed something, or a `custom_exit`/`custom_sell` behavior difference (docs: `custom_exit` is now called every iteration, independent of current profit and `exit_profit_only`).
7. Clear the warnings: run the backtest again and confirm no `DEPRECATED` lines remain in the log. freqtrade can exit 0 on errors, so require a `BACKTESTING REPORT` table and no `ERROR`, `CRITICAL` or `Traceback` lines.
8. Validation gate (below). Migration projects often carry old look-ahead habits (`shift(-1)`, whole-column statistics, `iloc` in `populate_*`); a clean backtest does not rule them out.
9. Report: what was renamed, what was left alone, trade comparison result, validation results, anything unverified.

## Quick rename reference (docs)

| Old | New |
|-----|-----|
| `populate_buy_trend` / `populate_sell_trend` | `populate_entry_trend` / `populate_exit_trend` |
| columns `buy`, `sell`, `buy_tag` | `enter_long`, `exit_long`, `enter_tag` (+ `enter_short`, `exit_short`) |
| `custom_sell` | `custom_exit` |
| `check_buy_timeout` / `check_sell_timeout` | `check_entry_timeout` / `check_exit_timeout` |
| `confirm_trade_exit(..., sell_reason, ...)` | `exit_reason` |
| `custom_stake_amount`, `confirm_trade_entry`, `custom_entry_price` | new `side` argument (`custom_entry_price` also `trade`) |
| `stoploss_from_open`, `stoploss_from_absolute` | pass `is_short=trade.is_short` |
| `trade.nr_of_successful_buys`, `trade.sell_reason` | `trade.nr_of_successful_entries`, `trade.exit_reason` |
| `use_sell_signal`, `sell_profit_only`, `sell_profit_offset`, `ignore_roi_if_buy_signal`, `forcebuy_enable` | `use_exit_signal`, `exit_profit_only`, `exit_profit_offset`, `ignore_roi_if_entry_signal`, `force_entry_enable` |
| `order_types` / `order_time_in_force` / `unfilledtimeout` keys `buy`, `sell` | `entry`, `exit` |
| `order_types` keys `emergencysell`, `forcesell`, `forcebuy` | `emergency_exit`, `force_exit`, `force_entry` |
| exit reasons `sell_signal`, `custom_sell`, `force_sell`, `emergency_sell` | `exit_signal`, `custom_exit`, `force_exit`, `emergency_exit` |
| config `bid_strategy`, `ask_strategy`, `ask_last_balance`, `bid_last_balance` | `entry_pricing`, `exit_pricing`, `price_last_balance` |
| `ignore_buying_expired_candle_after` | root level of the config |
| webhook `webhookbuy` ... `webhooksellcancel`; Telegram `buy`, `sell` ... | `entry`, `entry_fill`, `entry_cancel`, `exit`, `exit_fill`, `exit_cancel` |
| `ticker_interval` | `timeframe` |
| `populate_any_indicators` | `feature_engineering_*()` and `set_freqai_targets()` (freqtrade-freqai) |

Hyperopt `space="buy"` and `space="sell"` are unchanged (the updater leaves them alone; see freqtrade-hyperopt). The full table with before/after code and docs inconsistencies: references/v2-to-v3.md.

The core of the migration, tested (tests/strategies/MigratedV3.py; the old form wrote `["buy", "buy_tag"]` and `["sell", "exit_tag"]` inside `populate_buy_trend` / `populate_sell_trend`):

<!-- tested: tests/strategies/MigratedV3.py lines 59-60 -->
```python
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_bb_low")
```

<!-- tested: tests/strategies/MigratedV3.py lines 82-86 -->
```python
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        if current_profit > 0.015:
            return "profit_1_5pct"
        return None
```

## strategy-updater

```bash
freqtrade strategy-updater --strategy-list MyStrategy --strategy-path user_data/strategies
```

It rewrites the file in place (the original goes to `<userdir>/strategies_orig_updater/`, overwritten on a second run). Observed on 2026.10: it renames the methods, columns, settings and the `buy`/`sell` keys of `order_types`, `order_time_in_force`, `unfilledtimeout`, sets `INTERFACE_VERSION = 3`, and the converted fixture traded identically. It does NOT rename the `emergencysell`/`forcesell`/`forcebuy` keys, does NOT add `side` or `is_short` arguments, does NOT rename `trade.sell_reason`, and does not touch the config. It can break code: a local variable `sell` is renamed at assignment but not inside a subscript (NameError), and a string such as the tag `"buy"` silently becomes `"entry"`. It also reformats the whole file. Details and evidence: references/strategy-updater.md.

## Validation gate

Before reporting the migrated strategy as done:

1. The strategy loads (`freqtrade list-strategies`), backtests without errors and with trades, and the migrated trades match the baseline (or every difference is explained and approved by the user).
2. `lookahead-analysis` reports no bias (`has_bias` False, no biased entry/exit signals or indicators). Fix entries before exits. The only blanket exception is FreqAI `set_freqai_targets()` columns. Pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives; explain each to the user, never silently ignore.
3. `recursive-analysis` shows near-zero variance (the project checks use at most 0.5% at the declared `startup_candle_count`); otherwise raise `startup_candle_count`, not the tolerance.
4. No `DEPRECATED` lines remain in the backtest log.
5. Only after 1 to 4, suggest a dry run. Live trading is the user's separate, explicit decision.

```bash
freqtrade backtesting --strategy MyStrategy --timerange 20260801-20261001 --export trades
freqtrade lookahead-analysis --strategy MyStrategy --timerange 20260801-20261001
freqtrade recursive-analysis --strategy MyStrategy --timerange 20260801-20261001
```

Details of these commands: freqtrade-validation.

## Examples in this repo

| File | Shows |
|------|-------|
| tests/fixtures/strategies/LegacyV2.py | Old interface: v2 method names, columns and settings (still loads in spot) |
| tests/strategies/MigratedV3.py | The same strategy migrated by hand (passes backtesting, lookahead and recursive checks) |
| tests/test_migration_fixtures.sh | Manual suite: legacy vs migrated vs updater trade equality, updater gaps, `buy_tag` crash |

## References

- references/v2-to-v3.md - full rename table with before/after code, config keys, FreqAI split, docs inconsistencies
- references/deprecated.md - removed features and replacements (edge, hdf5, `ticker_interval`, protections in config, funding-rate timeframe), what still works in 2026.10
- references/strategy-updater.md - usage, what it converts, what it misses, hazards

## Related skills

freqtrade-strategy (current interface, signals, callbacks overview), freqtrade-callbacks (new callback signatures), freqtrade-config (config keys, pricing), freqtrade-backtesting (run and compare backtests), freqtrade-validation (lookahead and recursive gate), freqtrade-freqai (feature engineering split), freqtrade-hyperopt (parameter spaces).

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
