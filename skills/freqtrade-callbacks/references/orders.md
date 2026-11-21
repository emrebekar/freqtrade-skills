Source: docs/strategy-callbacks.md#custom-order-price-rules
Source: docs/strategy-callbacks.md#custom-order-timeout-rules
Source: docs/strategy-callbacks.md#adjust-order-price
Source: docs/strategy-callbacks.md#order-filled-callback

# Order callbacks: prices, timeouts, re-pricing, fills

None of these are run by the repo tests (the test strategies use the default order pricing, and the test data has no order book). Everything below is from the docs; signatures are copied verbatim. Test them in your own backtest, and remember backtesting fills orders only if the price lies within the candle's low/high range.

## custom_entry_price and custom_exit_price

Called right before placing an order.

```python
def custom_entry_price(self, pair: str, trade: Trade | None, current_time: datetime, proposed_rate: float,
                       entry_tag: str | None, side: str, **kwargs) -> float:

def custom_exit_price(self, pair: str, trade: Trade,
                      current_time: datetime, proposed_rate: float,
                      current_profit: float, exit_tag: str | None, **kwargs) -> float:
```

- Returning `None` or an invalid value falls back to `proposed_rate` (regular pricing configuration).
- For the first entry `trade` is `None`; the Trade object exists once the first entry order is created.
- Only works for limit orders; can leave many orders unfilled. The default maximum distance from the proposed rate is 2%, configurable with `custom_price_max_distance_ratio` (docs: new entry price 97, proposed 100, 2% limit gives 98).
- Backtesting: supported; orders fill if the price is inside the candle's range; unfilled orders are subject to regular timeout handling once per (detail) candle. `custom_exit_price()` is only called for exit-signal exits, custom exits and partial exits; other exit types use regular backtesting prices.
- Docs example reads `dataframe["bollinger_10_lowerband"].iat[-1]` from `self.dp.get_analyzed_dataframe(...)`.

## check_entry_timeout and check_exit_timeout

Called for every open order until filled or cancelled; return `True` to cancel, `False` to keep. Backtesting: called once per (detail) candle for orders that do not fill immediately (custom pricing).

```python
def check_entry_timeout(self, pair: str, trade: Trade, order: Order,
                        current_time: datetime, **kwargs) -> bool:

def check_exit_timeout(self, pair: str, trade: Trade, order: Order,
                       current_time: datetime, **kwargs) -> bool:
```

Docs: set `unfilledtimeout` larger than your longest custom timeout (the example sets 25 hours for a 24 hour rule), otherwise the plain timeout applies first. Entry `unfilledtimeout` and these callbacks take precedence over `adjust_order_price()`. The docs example using `self.dp.orderbook(pair, 1)` reads live order book data; not available in backtests, see freqtrade-strategy references/dataprovider.md.

## adjust_order_price, adjust_entry_price, adjust_exit_price

Refresh or replace limit orders on new candles; called once per iteration unless the order was (re)placed in the current candle, so at most once per candle per order, and the first call is at the start of the next candle. `custom_entry_price()` / `custom_exit_price()` still set the initial price.

```python
def adjust_order_price(
    self,
    trade: Trade,
    order: Order | None,
    pair: str,
    current_time: datetime,
    proposed_rate: float,
    current_order_rate: float,
    entry_tag: str | None,
    side: str,
    is_entry: bool,
    **kwargs,
) -> float | None:
```

- Return `current_order_rate` to keep the order, another price to cancel and replace, `None` to cancel without replacing.
- If cancelling fails the order is not replaced. Partially filled orders are not replaced; use `adjust_trade_position()` to fix the size.
- `adjust_entry_price()` (entry orders only) and `adjust_exit_price()` (exit orders only) are the split versions with otherwise identical behavior. Implementing `adjust_order_price()` together with either split callback is not supported and raises an error at bot startup (docs); the docs say that if both exist only `adjust_order_price()` is used, which contradicts "raises an error", so implement only one family.
- `trade.open_date_utc` stays at the very first order's time; use the first filled order's date when needed.
- The docs do not show the split callbacks' signatures. Read with `inspect.signature` from the 2026.10 image, both are `(self, trade: Trade, order: Order | None, pair: str, current_time: datetime, proposed_rate: float, current_order_rate: float, entry_tag: str | None, side: str, **kwargs) -> float | None` (no `is_entry`). Re-check against your installed version.

## order_filled

Called right after an order fills, for all order types (entry, exit, stoploss, position adjustment).

```python
def order_filled(self, pair: str, trade: Trade, order: Order, current_time: datetime, **kwargs) -> None:
```

Docs example stores data when the first entry fills (`trade.nr_of_successful_entries == 1` and `order.ft_order_side == trade.entry_side`): `trade.set_custom_data(key="entry_candle_high", value=last_candle["high"])`. Storing custom trade data is advanced usage; see the docs section "Storing custom trade data" in strategy-advanced.md.
