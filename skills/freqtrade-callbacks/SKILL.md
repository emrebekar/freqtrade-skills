---
name: freqtrade-callbacks
description: Use when you need to add Freqtrade strategy callbacks that react to trade state - custom_stoploss (trailing, stoploss_from_open, stoploss_from_absolute), custom_exit, custom_roi, custom_stake_amount, adjust_trade_position (DCA, partial exit), confirm_trade_entry, confirm_trade_exit, custom_entry_price, custom_exit_price, check_entry_timeout, adjust_order_price, order_filled, leverage, bot_start, bot_loop_start. Covers exact signatures, return values, backtest versus live behavior and a decision table.
license: GPL-3.0
---

# Freqtrade strategy callbacks

Callbacks are strategy methods the bot calls "whenever needed" (during a trade, or when entering or exiting), unlike `populate_*` which are vectorized. Pinned Freqtrade release: 2026.10. The example classes `CallbacksExample` and `PositionAdjustExample` ([tests/strategies/](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/)) were run through backtesting, `lookahead-analysis` and `recursive-analysis` on test data, and the backtest exports were inspected to confirm each callback fired (see "What the tests showed"). They are teaching examples, not profitable strategies; never present them as such.

Rules:
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives. A pass does not prove the strategy is clean; it only checks signals that fired in the tested timerange.
- Keep `dry_run: true`. Never set `dry_run: false` unless the user explicitly asks.
- Copy signatures from the references exactly, including type hints and `**kwargs`. Do not invent parameters. Leave `**kwargs` in every callback so future parameters do not break the strategy.
- Keep callbacks fast. Do not call the network or do heavy computation in them. Use `current_time`, never `datetime.now()`, or backtesting breaks.
- Read the user's existing strategy first; add only the callback that was asked for.
- A callback can hide losses: `confirm_trade_exit` can block stoploss exits, `adjust_trade_position` spends more money. Warn the user when you add either.

## Decision table: I want X, use Y

| I want to... | Callback | Enable with | Reference |
|--------------|----------|-------------|-----------|
| run something once at start / once per loop | `bot_start()` / `bot_loop_start()` | nothing | references/bot-loop.md |
| trail or tighten the stop based on trade state | `custom_stoploss()` | `use_custom_stoploss = True` | references/stoploss.md |
| stop relative to open price or an absolute price | `stoploss_from_open()` / `stoploss_from_absolute()` in `custom_stoploss()` | `use_custom_stoploss = True` | references/stoploss.md |
| exit a trade using trade data (age, profit, tags) | `custom_exit()` | `use_exit_signal` must not be False | references/exit-roi.md |
| a dynamic ROI threshold | `custom_roi()` | `use_custom_roi = True` | references/exit-roi.md |
| size each new trade | `custom_stake_amount()` | nothing | references/stake-position.md |
| add to (DCA) or partially close an open trade | `adjust_trade_position()` | `position_adjustment_enable = True` | references/stake-position.md |
| choose leverage per trade (futures) | `leverage()` | futures config | references/stake-position.md |
| veto an entry or exit at the last moment | `confirm_trade_entry()` / `confirm_trade_exit()` | nothing | references/confirm.md |
| set my own limit price for entries/exits | `custom_entry_price()` / `custom_exit_price()` | limit orders | references/orders.md |
| cancel unfilled orders by my own rule | `check_entry_timeout()` / `check_exit_timeout()` | nothing | references/orders.md |
| re-price an open unfilled limit order | `adjust_order_price()` or `adjust_entry_price()` / `adjust_exit_price()` | implement only one family | references/orders.md |
| react after any order fills (store data) | `order_filled()` | nothing | references/orders.md |

If a plain signal, `minimal_roi` or `stoploss` does the job, use those: they are simpler and behave the same in backtesting and live. The docs say `custom_exit()` is an inferior replacement for stoploss; use `custom_stoploss()` for stops.

## Workflow

1. Pick the callback from the table. Open its reference and copy the signature.
2. Add the enabling attribute if one is listed (`use_custom_stoploss`, `use_custom_roi`, `position_adjustment_enable`).
3. Write the logic with `current_time`, `trade` and `self.dp.get_analyzed_dataframe(pair, self.timeframe)` for indicator values (`dataframe.iloc[-1]` is allowed in callbacks, not in `populate_*`).
4. Backtest and make the callback visible: look at exit reasons, order tags, `trade.stake_amount`, or log a line. Do not assume it fired. See freqtrade-backtesting.
5. Remember that backtesting calls each callback at most once per candle (once per detail candle with `--timeframe-detail`), while live calls most of them about every 5 seconds. Strict conditions avoid repeated live actions.
6. Run the validation gate below.

## Tested example: all callbacks together

`CallbacksExample` ([tests/strategies/CallbacksExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/CallbacksExample.py)) implements `bot_start`, `bot_loop_start`, `custom_stake_amount`, `confirm_trade_entry`, `custom_exit` and `custom_stoploss`. Class attributes:

<!-- tested: tests/strategies/CallbacksExample.py lines 15-26 -->
```python
class CallbacksExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10
    use_custom_stoploss = True

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200
```

A trailing custom stoploss that uses the open-price helper, and a custom exit with a tag:

<!-- tested: tests/strategies/CallbacksExample.py lines 92-105 -->
```python
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        # Close any trade at a loss that has been open for 2 hours or more.
        if current_profit < 0.0 and (current_time - trade.open_date_utc) >= timedelta(hours=2):
            return "unclog"

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float | None:
        # Once 1% in profit, lock the stop at 0.5% above the open price (never moves down).
        if current_profit > 0.01:
            return stoploss_from_open(0.005, current_profit, is_short=trade.is_short, leverage=trade.leverage)
        # Otherwise trail 4% behind the current price.
        return -0.04 * trade.leverage
```

`PositionAdjustExample` ([tests/strategies/PositionAdjustExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/PositionAdjustExample.py)) enables position adjustment, allows one extra entry, and implements one DCA add plus one partial exit:

<!-- tested: tests/strategies/PositionAdjustExample.py lines 21-26 -->
```python
    position_adjustment_enable = True
    # One extra entry per trade, on top of the first entry order.
    max_entry_position_adjustment = 1

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200
```

Its callback is in references/stake-position.md.

## Lifecycle in one glance

Live or dry-run, each loop (every `internals.process_throttle_secs`, about 5 s): `bot_loop_start()`, populate_* per pair, `order_filled()` and timeout/price-adjust callbacks for open orders, exits (`custom_exit()`, `custom_stoploss()`, `custom_exit_price()`, `confirm_trade_exit()`), `adjust_trade_position()`, then entries (`custom_entry_price()`, `leverage()`, `custom_stake_amount()`, `confirm_trade_entry()`). `bot_start()` runs once at start. Backtesting runs a subset per candle. Full order for both modes: references/bot-loop.md.

## What the tests showed

Backtest of 2026-08-01 to 2026-10-01, BTC/USDT and ETH/USDT, 5m, from the exported trades and the log:

- `custom_exit`: 340 of 457 trades exited with reason `unclog` (the tag the callback returned).
- `custom_stoploss`: 8 trades exited with reason `trailing_stop_loss`, as the docs say custom stoploss exits are reported.
- `custom_stake_amount`: trades tagged `ema_cross` had stake about 50 USDT, `rsi_bb_low` about 100 USDT (config stake 100).
- `confirm_trade_entry`: returned False 27 times (logged); the backtest summary line "Rejected Entry signals" still showed 0, so do not count confirm rejections from that line.
- `bot_start` and `bot_loop_start` logged. `adjust_trade_position`: 24 of 95 trades had two entry orders (tag `dca_1`) and 20 had a partial exit (tag `half_profit`).

## Validation gate

Before reporting the strategy as done:

1. The strategy loads (`freqtrade list-strategies`) and backtests without errors and with trades; the callback actually fired (see step 4 of the workflow).
2. `lookahead-analysis` reports no bias (`has_bias` No, no biased entry/exit signals or indicators). The only blanket exception is FreqAI `set_freqai_targets()` columns. Pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives; explain each to the user, never silently ignore.
3. `recursive-analysis` shows near-zero variance (the project checks use at most 0.5% at the declared `startup_candle_count`); otherwise raise `startup_candle_count`, not the tolerance.
4. Only after 1 to 3, suggest a dry run. Live trading is the user's separate, explicit decision.

Callbacks that read the dataframe (`self.dp.get_analyzed_dataframe`) are only as safe as the indicators in it. Details of these commands: freqtrade-validation.

## References

- references/bot-loop.md - `bot_start`, `bot_loop_start`, execution order live and in backtesting
- references/stoploss.md - `custom_stoploss`, `after_fill`, `stoploss_from_open`, `stoploss_from_absolute`, examples
- references/exit-roi.md - `custom_exit`, `custom_roi`
- references/stake-position.md - `custom_stake_amount`, `adjust_trade_position`, `leverage`
- references/confirm.md - `confirm_trade_entry`, `confirm_trade_exit`
- references/orders.md - custom prices, timeouts, `adjust_order_price`, `order_filled`

## Related skills

freqtrade-strategy (signals, ROI, static stoploss, Trade object), freqtrade-config (stake amount, order types, unfilledtimeout), freqtrade-backtesting (run backtests, read exit reasons), freqtrade-validation (lookahead, recursive, hyperopt gating).

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
