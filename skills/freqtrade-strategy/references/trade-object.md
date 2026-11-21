Source: docs/trade-object.md#trade-available-attributes
Source: docs/trade-object.md#class-methods
Source: docs/trade-object.md#order-object

# Trade and Order objects

A `Trade` is a persisted position. It is passed to many callbacks (see freqtrade-callbacks) and cannot be modified directly; changes happen through callback return values. Import with `from freqtrade.persistence import Trade` (also exported from `freqtrade.strategy`).

## Common Trade attributes (use `trade.<name>`)

| Attribute | Type | Meaning |
|-----------|------|---------|
| `pair` | str | Pair of the trade |
| `is_open`, `is_short` | bool | Open/closed; short or long |
| `open_rate` | float | Entry rate (average if position was adjusted) |
| `open_date_utc`, `close_date_utc` | datetime | Use these, not `open_date`/`close_date` |
| `stake_amount`, `max_stake_amount` | float | Current stake; max stake used (sum of filled entries) |
| `amount` | float | Base currency owned; 0.0 until the first order fills |
| `leverage` | float | 1.0 on spot |
| `enter_tag`, `exit_reason` | str | From the `enter_tag` column; why the trade exited |
| `close_profit`, `close_profit_abs` | float | Relative / absolute profit at closure (`0.01` = 1%) |
| `realized_profit` | float | Absolute profit already realized while still open |
| `max_rate`, `min_rate` | float | Highest / lowest price during the trade (not 100% accurate) |
| `nr_of_successful_entries`, `nr_of_successful_exits` | int | Filled order counts |
| `has_open_position`, `has_open_orders` | bool | Position exists; open orders (excluding stoploss orders) |
| `orders`, `open_orders` | Order[] | All / open orders |
| `entry_side`, `exit_side`, `trade_direction` | str | `"buy"`/`"sell"`; `"long"`/`"short"` |
| `date_last_filled_utc`, `date_entry_fill_utc` | datetime | Last fill; first entry fill |

Stoploss related: `stop_loss`, `stop_loss_pct`, `initial_stop_loss`, `initial_stop_loss_pct`, `stoploss_last_update_utc`, `stoploss_or_liquidation` (the more restrictive of stoploss and liquidation price). Futures/margin: `liquidation_price`, `interest_rate`, `funding_fees`. The full attribute list is in the Freqtrade docs page trade-object.md.

## Class methods

Usable as `Trade.<method>`. In backtesting/hyperopt use them only in callbacks; in `populate_*` they give wrong results.

- `Trade.get_trades_proxy(pair=..., is_open=..., open_date=..., close_date=...)`: all arguments optional; returns a list of trades.
- `Trade.get_open_trade_count()`: number of open trades.
- `Trade.get_total_closed_profit()`: sum of `close_profit_abs` of closed trades.
- `Trade.total_open_trades_stakes()`: total stake in open trades.
- Not supported in backtesting/hyperopt: `Trade.get_overall_performance()` (guard with `self.config['runmode'].value in ('live', 'dry_run')`) and `Trade.get_trading_volume()`.

```python
from freqtrade.persistence import Trade
from datetime import timedelta

trade_hist = Trade.get_trades_proxy(pair='ETH/USDT', is_open=False, open_date=current_date - timedelta(days=2))
```

(`current_date` is a datetime you provide, for example the `current_time` argument of a callback. Docs example, not run by the repo tests.)

## Order object

`trade.orders` holds `Order` objects. Prefer the `safe_*` accessors because many raw fields can be `None`: `safe_filled`, `safe_amount`, `safe_price`, `safe_cost`, `safe_remaining`, `safe_fee_base`. Other fields: `ft_order_side` (`buy`, `sell`, `stoploss`), `ft_is_open`, `order_type`, `status` (ccxt: open, closed, expired, canceled, rejected), `side`, `price`, `average`, `stop_price`, `order_filled_utc`, `order_date_utc` (use the `_utc` variants).

## Persistent custom data

`trade.set_custom_data(key, value)`, `trade.get_custom_data(key, default=...)`, `trade.get_custom_data_entry(key)`, `trade.delete_custom_data(key)`; values must be JSON serializable and small. See dataprovider.md.
