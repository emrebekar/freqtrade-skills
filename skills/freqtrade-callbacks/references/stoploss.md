Source: docs/strategy-callbacks.md#custom-stoploss
Source: docs/strategy-callbacks.md#adjust-stoploss-after-position-adjustments
Source: docs/strategy-callbacks.md#custom-stoploss-examples
Source: docs/strategy-callbacks.md#common-helpers-for-stoploss-calculations
Source: docs/stoploss.md#stoploss-and-leverage

# custom_stoploss

Enable with `use_custom_stoploss = True`. The normal `stoploss` stays mandatory: it is the initial stoploss (before the callback is first called for a trade) and an absolute lower level.

Signature (docs):

```python
def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, after_fill: bool,
                    **kwargs) -> float | None:
```

## Return value (docs)

- A float: stoploss as a distance from `current_rate`, as a ratio. At `current_rate` 200, `0.02` puts the stop at 196. The sign is ignored: `0.05` and `-0.05` are the same.
- `None`: no change. The docs call it "the only safe way" to leave the stoploss alone. `NaN` and `inf` are invalid and ignored like `None`.
- The stoploss price can only move up. A value that would produce a lower stop price than the current one is ignored.
- Exits caused by it have exit reason `trailing_stop_loss` (docs; confirmed in the test backtest, 8 exits).
- In backtesting `current_rate` and `current_profit` use the candle high (low for shorts); the stop is evaluated against the candle low (high for shorts).
- Futures: the returned value is the risk for the trade, not the price move. Multiply by `trade.leverage` (see stoploss and leverage below).
- Use `current_time`, not `datetime.now()`.
- Docs tip: disable `trailing_stop` when using custom stoploss; both can work together but may conflict.

## Tested example

A 4% trail with a lock above the open price once 1% in profit:

<!-- tested: tests/strategies/CallbacksExample.py lines 98-105 -->
```python
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float | None:
        # Once 1% in profit, lock the stop at 0.5% above the open price (never moves down).
        if current_profit > 0.01:
            return stoploss_from_open(0.005, current_profit, is_short=trade.is_short, leverage=trade.leverage)
        # Otherwise trail 4% behind the current price.
        return -0.04 * trade.leverage
```

The class sets `use_custom_stoploss = True` and keeps the static `stoploss = -0.10`:

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

## after_fill

Docs: if the signature contains `after_fill`, freqtrade makes an extra call with `after_fill=True` after an order fills (for example after a position adjustment). In that call the stoploss may move in either direction, including widening. If your function lacks the `after_fill` parameter this call is not made (backwards compatibility).

Doc example (not run by the repo tests):

```python
if after_fill:
    # After an additional order, start with a stoploss of 10% below the new open rate
    return stoploss_from_open(0.10, current_profit, is_short=trade.is_short, leverage=trade.leverage)
```

Docs conflict: the position-adjust warning in strategy-callbacks.md says "Stoploss is still calculated from the initial opening price, not averaged price", while the after-fill example sets the stop relative to the new averaged open rate. If it matters, log `trade.open_rate` and the exit price in a backtest of your own strategy instead of relying on either statement.

## Helpers

Import them from `freqtrade.strategy`. The docs show usage only; the signatures below were read with `inspect.signature` in the 2026.10 image.

`stoploss_from_open(open_relative_stop, current_profit, is_short=False, leverage=1.0)`: converts "X profit above the open price" into the current-price-relative value the callback must return. Docs example: open 100, price 121 (`current_profit` 0.21): `stoploss_from_open(0.07, 0.21, False)` returns 0.1157024793; 11.57% below 121 is 107, 7% above 100. Leverage is considered.

Checked in the 2026.10 image: `stoploss_from_open(0.07, 0.21, False)` returned `0.11570247933884292`, and `stoploss_from_open(0.07, 0.05, False)` returned `0.0` (profit below the wanted stop). The docs warn that invalid input (profit below the requested level, for example when `confirm_trade_exit()` blocked a close) can produce "CustomStoploss function did not return valid stoploss" warnings, and suggest the `stoploss_from_open(...) or 1` idiom. Docs contradiction: the callback section says `None` is the only safe way to leave the stoploss unchanged, yet the idiom and one docs example return `1`. The tested example avoids both by gating on `current_profit > 0.01`, above the 0.005 target, and otherwise returning the trail. Prefer `None` for "no change".

`stoploss_from_absolute(stop_rate, current_rate, is_short=False, leverage=1.0)`: converts an absolute stop price to the relative value. Checked in the image: `stoploss_from_absolute(196, 200, is_short=False)` returned `0.02` (about; `0.020000000000000018`).

Doc example, 2xATR stop (not run by the repo tests; the docs example computes `trade_date` but never uses it):

```python
dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
candle = dataframe.iloc[-1].squeeze()
side = 1 if trade.is_short else -1
return stoploss_from_absolute(current_rate + (side * candle["atr"] * 2),
                              current_rate=current_rate,
                              is_short=trade.is_short,
                              leverage=trade.leverage)
```

## Other doc examples (not run by the repo tests)

- Time based: first 60 minutes initial stoploss (return `None`), then `-0.10 * trade.leverage`, after 120 minutes `-0.05 * trade.leverage`. Check the longest interval first, since conditions are evaluated top to bottom.
- Per pair: return `-0.10 * trade.leverage` for some pairs, another value for others.
- Positive offset: `None` until `current_profit` reaches 0.04, then `max(min(current_profit / 2, 0.05), 0.025) * trade.leverage`.
- Stepped: evaluate highest profit first, `stoploss_from_open(0.25, ...)` above 0.40 profit, 0.15 above 0.25, 0.07 above 0.20, else `None`.
- Docs example indicator stop (parabolic SAR) returns `stoploss_from_absolute(...)` only when the SAR price is below `current_rate`.

## Stoploss and leverage (docs)

Stoploss is the risk on the trade: -10% at 10x leverage triggers on a 1% price move. Do not set a too-tight stoploss at high leverage.

Stoploss on exchange follows custom stoploss changes as configured by `stoploss_on_exchange_interval`; see freqtrade-strategy references/stoploss.md and the docs page stoploss.md.
