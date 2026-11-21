Source: docs/strategy-callbacks.md#bot-order-confirmation
Source: docs/strategy-callbacks.md#trade-entry-buy-order-confirmation
Source: docs/strategy-callbacks.md#trade-exit-sell-order-confirmation

# confirm_trade_entry and confirm_trade_exit

These are the last methods called before an order is placed. Return `True` to place the order, `False` to abort. When not implemented they always confirm. Keep them fast: no heavy computation or network requests.

## confirm_trade_entry

<!-- tested: tests/strategies/CallbacksExample.py lines 83-90 -->
```python
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        # Refuse entries during the first hour (UTC) of the day. Arbitrary rule, for demonstration.
        if current_time.hour == 0:
            logger.info("CALLBACK confirm_trade_entry rejected %s at %s", pair, current_time)
            return False
        return True
```

The rule in the example (no entries in the first UTC hour) is arbitrary, for demonstration. Docs parameters: `order_type` (usually limit or market), `amount` in base currency, `rate` (limit price, or current rate for market orders), `time_in_force` (default GTC), `entry_tag`, `side` (`"long"` or `"short"`).

Test result: in the 2026-08-01 to 2026-10-01 backtest it returned `False` 27 times (log lines from the callback). The backtest summary row "Rejected Entry signals" showed 0 at the same time, so that row does not count confirm rejections; count them with a log line or a counter.

## confirm_trade_exit

Called right before a regular exit order. It may be called several times in one iteration for the same trade if different exit reasons apply, in this order: `exit_signal` / `custom_exit`, `stop_loss`, `roi`, `trailing_stop_loss`.

Signature (docs; not run by the repo tests):

```python
def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                       rate: float, time_in_force: str, exit_reason: str,
                       current_time: datetime, **kwargs) -> bool:
```

`exit_reason` can be any of `"roi"`, `"stop_loss"`, `"stoploss_on_exchange"`, `"trailing_stop_loss"`, `"exit_signal"`, `"force_exit"`, `"emergency_exit"` (docs list). Docs example rejects a `force_exit` with negative profit via `trade.calc_profit_ratio(rate) < 0`; the docs say it is only a sample.

Warnings (docs):

- `confirm_trade_exit()` can block stoploss exits, which ignores your stoploss and can cause significant losses. Never block `stop_loss` / `stoploss_on_exchange` / `trailing_stop_loss` reasons unless the user explicitly asks.
- It is not called for liquidations (forced by the exchange).
- If it blocks a close while `custom_stoploss()` uses `stoploss_from_open()`, you may see "CustomStoploss function did not return valid stoploss" warnings (see references/stoploss.md).

Not documented: what `exit_reason` contains for a tagged `custom_exit()` string. Log it before relying on it.
