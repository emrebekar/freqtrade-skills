Source: docs/stoploss.md#stop-loss-on-exchangefreqtrade
Source: docs/stoploss.md#stop-loss-types
Source: docs/stoploss.md#stoploss-and-leverage
Source: docs/stoploss.md#changing-stoploss-on-open-trades

# Stoploss

`stoploss` is a negative ratio of the open price: `-0.10` exits when the trade is 10% down. Fees are included, so the stop sits exactly 10% below entry. All stoploss properties can be set in the strategy or the config; config values override the strategy. Always set a stoploss.

```python
stoploss = -0.10
```

## Stoploss types

1. Static: `stoploss = -0.10`.
2. Trailing: `trailing_stop = True` moves the stop up with the highest observed price, staying 10% below it.
3. Trailing with a different positive distance: `trailing_stop_positive = 0.02` (2%) once in profit; `trailing_stop_positive_offset` is the profit at which this applies (set it higher than `trailing_stop_positive` to lock in profit at the first step).
4. Trailing only after an offset: `trailing_only_offset_is_reached = True` keeps the static `stoploss` until the offset is reached.
5. Custom stoploss callback: see freqtrade-callbacks.

```python
stoploss = -0.10
trailing_stop = True
trailing_stop_positive = 0.02
trailing_stop_positive_offset = 0.03
trailing_only_offset_is_reached = True
```

Keep `trailing_stop_positive_offset` lower than the minimal ROI, otherwise ROI sells first. The two snippets above are from the docs; they are not run by the repo tests (the tested strategies use a static `stoploss = -0.10`).

## Stoploss on exchange

`order_types` in the strategy or config controls whether the stop is a real order on the exchange (survives a bot outage and network delays) or checked by freqtrade:

```python
order_types = {
    "entry": "limit",
    "exit": "limit",
    "emergency_exit": "market",
    "stoploss": "market",
    "stoploss_on_exchange": True,
    "stoploss_on_exchange_interval": 60,
    "stoploss_on_exchange_limit_ratio": 0.99
}
```

- Only some exchanges support it, and not all support both stop-limit and stop-market. If the exchange supports both, the `stoploss` order type decides which is used. If only one is available you must configure accordingly or the bot fails to start.
- Prefer stop-market: a stop-limit may not fill in a crash and the loss can exceed "stoploss + limit ratio".
- Do not set a very tight stop (missed fills) or a very wide one such as `-1` (the exchange may reject it; the bot then falls back to the `emergency_exit` order type).
- `stoploss_on_exchange_limit_ratio` (limit order price relative to the stop price) is only used for stop-limit. Example: stop at 95, ratio 0.99 gives limit 94.05.
- `stoploss_on_exchange_interval` (seconds, default 60) is how often the bot updates/re-places the stop order.
- `stoploss_price_type` (`last`, `mark`, `index`) only applies to futures and is validated at startup.
- If the stop order is cancelled manually on the exchange, the bot creates a new one.

## Stoploss and leverage

Stoploss is the risk on the trade measured on your own capital. A 10% stoploss at 10x leverage triggers on a 1% price move; at 2x it triggers on a 5% move. With leverage, check that the stoploss is reachable before liquidation: with leverage 2 a stoploss of -0.5 would be liquidated first. See leverage-shorting.md.

## Changing the stoploss of open trades

Edit the value in the config or strategy and reload the config (`/reload_config`) or restart the bot. The new value is applied to open trades. It cannot be changed when `trailing_stop` is on and the stop has already moved.
