Source: docs/strategy_migration.md#quick-summary--migration-checklist
Source: docs/strategy_migration.md#extensive-explanation
Source: docs/strategy-customization.md (INTERFACE_VERSION paragraph)

# V2 to V3 rename table

Labels: `docs` = from the Freqtrade docs 2026.10 (strategy_migration.md); `observed` = seen in this repo's runs on the 2026.10 image (tests/test_migration_fixtures.sh, tests/out/migration/); `tested` = code byte-identical to tests/strategies/MigratedV3.py, which passes backtesting, `lookahead-analysis` and `recursive-analysis`. MigratedV3 is the hand migration of tests/fixtures/strategies/LegacyV2.py. Both are teaching examples, not profitable strategies.

Interface version: docs say `INTERFACE_VERSION` should be 3 and that 3 is also the default when it is not set. Set it explicitly to 3 after migrating. A strategy that still says 2 "will need to be updated to v3 terminology as future versions will require this to be set" (docs, strategy-customization.md).

## Strategy methods and callbacks (docs)

| Old | New | Notes |
|-----|-----|-------|
| `populate_buy_trend()` | `populate_entry_trend()` | same signature |
| `populate_sell_trend()` | `populate_exit_trend()` | same signature |
| `custom_sell()` | `custom_exit()` | now called every iteration, independent of current profit and `exit_profit_only` |
| `check_buy_timeout()` | `check_entry_timeout()` | `order` argument is an `Order` object (old docs signature typed it `dict`) |
| `check_sell_timeout()` | `check_exit_timeout()` | same |
| `custom_stake_amount(..., entry_tag, **kwargs)` | add `side: str` after `entry_tag` | `"long"` or `"short"` |
| `confirm_trade_entry(..., entry_tag, **kwargs)` | add `side: str` after `entry_tag` | |
| `custom_entry_price(pair, current_time, proposed_rate, entry_tag, **kwargs)` | `custom_entry_price(pair, trade, current_time, proposed_rate, entry_tag, side, **kwargs)` | new `trade: Trade \| None` argument and `side` |
| `confirm_trade_exit(..., sell_reason, ...)` | `exit_reason` | docs: `sell_reason` is still provided "for a limited time" |
| `stoploss_from_open(...)`, `stoploss_from_absolute(...)` | pass `is_short=trade.is_short` | `stoploss_from_absolute` also takes `leverage=trade.leverage` in the docs example |
| `custom_stoploss` | gains `after_fill: bool` in the docs "After" example | optional; docs show it, the migration list does not require it |
| `trade.nr_of_successful_buys` | `trade.nr_of_successful_entries` | mostly in `adjust_trade_position()`; includes short entries |
| `trade.sell_reason` | `trade.exit_reason` | |

New `Trade` properties (docs): `is_short`, `entry_side`, `exit_side`, `trade_direction`. New `leverage` callback. Informative pairs can pass a third tuple element (candle type); `@informative` takes an optional `candle_type`.

## Dataframe columns (docs)

| Old | New |
|-----|-----|
| `buy` | `enter_long` |
| `sell` | `exit_long` |
| `buy_tag` | `enter_tag` (used for long and short) |
| new | `enter_short`, `exit_short` (only with `can_short = True`) |

Entry columns, tested (MigratedV3.py lines 59-60; the old form was `["buy", "buy_tag"]` ... `(1, "rsi_bb_low")`):

<!-- tested: tests/strategies/MigratedV3.py lines 59-60 -->
```python
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_bb_low")
```

Exit columns, tested (the old form was `["sell", "exit_tag"]`; the docs example itself already uses `exit_tag`):

<!-- tested: tests/strategies/MigratedV3.py lines 72-80 -->
```python
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] > 70)
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "rsi_high")
        return dataframe
```

Observed (2026.10 image, spot, `buy_tag` NOT used): a strategy with `populate_buy_trend` / `populate_sell_trend` and `buy` / `sell` columns still loads and backtests; Freqtrade renames `buy` to `enter_long` and `sell` to `exit_long` after the call. Observed crash: if the old `populate_buy_trend` writes a `buy_tag` column, the backtest dies with `ValueError: cannot reindex on an axis with duplicate labels`, because Freqtrade pre-creates `enter_tag` and then renames `buy_tag` to a second `enter_tag`. Rename `buy_tag` to `enter_tag` in the strategy yourself.

## Strategy-level settings (docs)

| Old | New |
|-----|-----|
| `use_sell_signal` | `use_exit_signal` |
| `sell_profit_only` | `exit_profit_only` |
| `sell_profit_offset` | `exit_profit_offset` |
| `ignore_roi_if_buy_signal` | `ignore_roi_if_entry_signal` |
| `forcebuy_enable` | `force_entry_enable` |

These can also be set in the config. Tested (MigratedV3.py lines 23-27):

<!-- tested: tests/strategies/MigratedV3.py lines 23-27 -->
```python
    # Renamed strategy settings (use_sell_signal, sell_profit_only, sell_profit_offset, ignore_roi_if_buy_signal).
    use_exit_signal = True
    exit_profit_only = False
    exit_profit_offset = 0.0
    ignore_roi_if_entry_signal = False
```

Docs inconsistency: the docs "Strategy level settings" example writes `sell_profit_offset: 0.01` and `exit_profit_offset: 0.01` with a colon (a type annotation without a value), not `=`. As written in a class body that defines no value. Use `=`.

## order_types, order_time_in_force, unfilledtimeout (docs)

| Old key | New key |
|---------|---------|
| `buy` | `entry` |
| `sell` | `exit` |
| `emergencysell` | `emergency_exit` |
| `forcesell` | `force_exit` |
| `forcebuy` | `force_entry` |

`stoploss`, `stoploss_on_exchange`, `stoploss_on_exchange_interval`, `exit_timeout_count` and `unit` keep their names. Docs: "two words are joined with `_`". Docs inconsistency: the "before" `order_time_in_force` uses lowercase `"gtc"`, the "After" uses `"GTC"`; the repo uses `"GTC"` (the migrated example passes with it). Tested (MigratedV3.py lines 29-40):

<!-- tested: tests/strategies/MigratedV3.py lines 29-40 -->
```python
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "force_exit": "market",
        "force_entry": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
        "stoploss_on_exchange_interval": 60,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}
    unfilledtimeout = {"entry": 10, "exit": 10, "unit": "minutes"}
```

Observed: with the old keys the 2026.10 spot backtest only logs `DEPRECATED` warnings for each key (`order_types.buy`, `.sell`, `.emergencysell`, `.forcesell`, `.forcebuy`, `order_time_in_force.buy/.sell`, `unfilledtimeout.buy/.sell`). The docs note the old keys "will be removed in the next versions", so migrate them.

## Callbacks, tested (MigratedV3.py lines 82-104)

<!-- tested: tests/strategies/MigratedV3.py lines 82-104 -->
```python
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        if current_profit > 0.015:
            return "profit_1_5pct"
        return None

    def check_entry_timeout(self, pair: str, trade: Trade, order: Order,
                            current_time: datetime, **kwargs) -> bool:
        return False

    def check_exit_timeout(self, pair: str, trade: Trade, order: Order,
                           current_time: datetime, **kwargs) -> bool:
        return False

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            entry_tag: str | None, side: str, **kwargs) -> float:
        return proposed_stake

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, exit_reason: str,
                           current_time: datetime, **kwargs) -> bool:
        return True
```

Entry callbacks, stoploss helpers and trade attributes, tested (MigratedV3.py lines 106-127; the old forms are in LegacyV2.py, the branches do not fire with this ROI, they test the syntax):

<!-- tested: tests/strategies/MigratedV3.py lines 106-127 -->
```python
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        return True

    def custom_entry_price(self, pair: str, trade: Trade | None, current_time: datetime,
                           proposed_rate: float, entry_tag: str | None, side: str,
                           **kwargs) -> float:
        return proposed_rate

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float | None:
        # Same branches as LegacyV2; they do not fire with this ROI, the point is the syntax.
        if trade.nr_of_successful_entries > 1 or trade.exit_reason is not None:
            return 1
        if current_profit > 0.10:
            return stoploss_from_open(0.07, current_profit, is_short=trade.is_short)
        if current_profit > 0.05:
            return stoploss_from_absolute(current_rate * 0.95, current_rate,
                                          is_short=trade.is_short, leverage=trade.leverage)
        return 1
```

Imports for these signatures (MigratedV3.py line 9): `from freqtrade.persistence import Order, Trade`.

## Terminology, pricing and notification settings (docs)

Exit reason strings changed. Update any `exit_reason` / `trade.exit_reason` comparison and any report filter that used the old strings: `sell_signal` to `exit_signal`, `custom_sell` to `custom_exit`, `force_sell` to `force_exit`, `emergency_sell` to `emergency_exit`. Source-read (2026.10 persistence migration code, not run here): old `custom_sell` rows in the database are rewritten to `custom_exit`.

Config (docs):

| Old | New |
|-----|-----|
| `bid_strategy` | `entry_pricing` |
| `ask_strategy` | `exit_pricing` |
| `ask_last_balance`, `bid_last_balance` | `price_last_balance` |
| `ignore_buying_expired_candle_after` (inside `ask_strategy` in the docs "before" example) | root level of the config |
| price side | can now be `ask`, `bid`, `same` or `other` (see freqtrade-config) |

Webhook config (docs): `webhookbuy` to `entry`, `webhookbuyfill` to `entry_fill`, `webhookbuycancel` to `entry_cancel`, `webhooksell` to `exit`, `webhooksellfill` to `exit_fill`, `webhooksellcancel` to `exit_cancel`. Telegram notification settings: `buy` to `entry`, `buy_fill` to `entry_fill`, `buy_cancel` to `entry_cancel`, `sell` to `exit`, `sell_fill` to `exit_fill`, `sell_cancel` to `exit_cancel`. Also: `forcesell`, `forcebuy`, `emergencysell` are now `force_exit`, `force_enter`, `emergency_exit`. Docs inconsistency: that top note says `force_enter`, while the same page's `order_types` table says `force_entry` and the setting is `force_entry_enable`. Use `force_entry` for `order_types` (tested above).

Docs inconsistency in the pricing example: the "before" JSON places `ask_last_balance` in `bid_strategy` and `bid_last_balance` in `ask_strategy`, and the snippet lacks a comma after `"bid_last_balance": 0.0`. Do not paste it as is.

## FreqAI strategies (docs, untested here)

`populate_any_indicators()` was removed in 2023.3 and split into `feature_engineering_expand_all()`, `feature_engineering_expand_basic()`, `feature_engineering_standard()` and `set_freqai_targets()`. Remove the expansion loops and the `{pair}` / `{timeframe}` parts of column names; targets (`&` prefix) move to `set_freqai_targets()`. Details and a tested FreqAI example: freqtrade-freqai. Custom `IFreqaiModel` classes that use `data_cleaning_train()` / `data_cleaning_predict()` must move to `define_data_pipeline()` / `define_label_pipeline()` (docs "FreqAI - New data Pipeline"; applies to custom models from before 2023.6).
