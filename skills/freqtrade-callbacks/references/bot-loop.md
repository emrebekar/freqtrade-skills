Source: docs/strategy-callbacks.md#bot-start
Source: docs/strategy-callbacks.md#bot-loop-start
Source: docs/bot-basics.md#bot-execution-logic
Source: docs/bot-basics.md#backtesting-hyperopt-execution-logic

# Bot start, bot loop and callback order

## bot_start

Called once when the strategy is loaded, after dataprovider and wallet are set. During hyperopt it runs only once at startup.

<!-- tested: tests/strategies/CallbacksExample.py lines 65-66 -->
```python
    def bot_start(self, **kwargs) -> None:
        logger.info("CALLBACK bot_start")
```

Doc example (not run by the repo tests, needs network): guard remote calls with the run mode.

```python
def bot_start(self, **kwargs) -> None:
    if self.config["runmode"].value in ("live", "dry_run"):
        self.custom_remote_data = requests.get("https://some_remote_source.example.com")
```

## bot_loop_start

Called once at the start of each bot iteration in dry/live (about every 5 seconds unless configured differently) or once per candle in backtest/hyperopt. Use it for pair-independent work.

<!-- tested: tests/strategies/CallbacksExample.py lines 68-72 -->
```python
    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        # Fires once per candle in backtesting: log only the first one.
        if not getattr(self, "_loop_logged", False):
            self._loop_logged = True
            logger.info("CALLBACK bot_loop_start first call at %s", current_time)
```

The test logs only the first call; in backtesting it ran for the first candle after the startup candles (2026-08-01 00:05).

## Order of calls, dry/live (docs: bot-basics)

1. Fetch open trades, build pairlist, download OHLCV (once per candle).
2. `bot_loop_start()`
3. Per pair: `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()`
4. Open order state update: `order_filled()` for filled orders; timeouts via `check_entry_timeout()` / `check_exit_timeout()`; then `adjust_order_price()` (or `adjust_entry_price()` / `adjust_exit_price()` only when `adjust_order_price()` is not implemented)
5. Exits: considers stoploss, ROI, exit signal, `custom_exit()`, `custom_stoploss()`; exit price from `exit_pricing` or `custom_exit_price()`; `confirm_trade_exit()` right before the order
6. `adjust_trade_position()` for open trades when enabled
7. Trade-slot check (`max_open_trades`)
8. Entries: entry price from `entry_pricing` or `custom_entry_price()`; `leverage()` in margin/futures; `custom_stake_amount()`; `confirm_trade_entry()` right before the order

## Order of calls, backtesting/hyperopt (docs: bot-basics)

`bot_start()` once; `populate_*` once per pair. Then per candle: `bot_loop_start()`; order timeouts (`unfilledtimeout`, `check_entry_timeout()`, `check_exit_timeout()`); `adjust_order_price()` (or the entry/exit split); entry signals; `confirm_trade_entry()` / `confirm_trade_exit()`; `custom_entry_price()`; `leverage()`; `custom_stake_amount()`; `adjust_trade_position()`; `order_filled()` for filled entries; `custom_stoploss()` and `custom_exit()`; `custom_exit_price()` for exit-signal, custom-exit and partial exits; `order_filled()` for filled exits.

Docs warning: backtesting calls each callback at most once per candle (`--timeframe-detail` makes that once per detail candle). Most callbacks run about every 5 s live, which causes backtest/live mismatches.

## Docs inconsistencies and notes

- strategy-callbacks.md says "Called for open trade every throttling iteration (roughly every 5 seconds)" for `custom_exit`, `custom_stoploss` and `custom_roi`; that is live only. In backtesting the cadence is per candle (bot-basics warning above).
- Docs examples for `populate_indicators` in the custom stoploss (SAR) and custom ROI (ATR) sections do not `return dataframe`. Do not copy that; always return the dataframe.
- Whether `bot_loop_start()` / `bot_start()` run in each mode comes from bot-basics (listed above); not separately tested beyond the log lines in CallbacksExample.
