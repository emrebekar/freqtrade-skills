Source: docs/strategy-customization.md#additional-data-dataprovider
Source: docs/strategy-customization.md#additional-data-wallets
Source: docs/strategy-customization.md#additional-data-trades
Source: docs/strategy-customization.md#prevent-trades-from-happening-for-a-specific-pair
Source: docs/strategy-advanced.md#dataframe-access
Source: docs/strategy-advanced.md#storing-information-persistent

# DataProvider, wallets and trades

`self.dp` is the DataProvider. All methods return `None` (or an empty frame) on failure instead of raising. Always check the run mode before using live-only methods. The snippets in this file are from the docs and are not run by the repo tests, except `current_whitelist()` and `get_pair_dataframe()` which are used in InformativeMergeExample.

## Methods

| Method | Returns | Notes |
|--------|---------|-------|
| `available_pairs` (property) | `(pair, timeframe)` tuples cached | |
| `current_whitelist()` | list of whitelisted pairs | Use for dynamic whitelists; not supported by `plot-dataframe` or webserver mode. |
| `get_pair_dataframe(pair, timeframe, candle_type=...)` | historic (backtest) or cached live data | In `populate_*` during backtesting it returns the full range: do not look into the future. In callbacks only up to the current simulated candle. |
| `get_analyzed_dataframe(pair, timeframe)` | `(dataframe, last_analyzed)` | Dataframe after `populate_*`; empty if the pair is not cached. For use in callbacks. |
| `historic_ohlcv(pair, timeframe)` | data on disk | |
| `ohlcv(pair, timeframe)` | cached candles or empty frame | |
| `market(pair)` | ccxt market data | fees, limits, precision |
| `orderbook(pair, maximum)` | `{"bids": [[price, amount], ...], "asks": [...]}` | Live only. |
| `ticker(pair)` | ccxt ticker | Live only; fields vary by exchange (`vwap`, `last` may be missing or `None`). |
| `check_delisting(pair)` | delisting datetime or `None` | Live only; exchange dependent. |
| `funding_rate(pair)` | current funding rate dict | Futures pairs `base/quote:settle`; live only. For backtesting use the historic `funding_rate` candle type. |
| `runmode` | run mode | Compare `self.dp.runmode.value` with `'live'`, `'dry_run'`. |
| `send_msg(text, always_send=False)` | | Notification in dry/live only; no-op in backtesting. Identical messages are sent once per candle unless `always_send=True` (avoid: spam). |

## Backtesting traps

`orderbook()`, `ticker()`, `check_delisting()` and `funding_rate()` always return the current real-time value. Without a run-mode guard, backtesting and hyperopt fill the whole dataframe with that one value. Guard them:

```python
if self.dp.runmode.value in ('live', 'dry_run'):
    ob = self.dp.orderbook(metadata['pair'], 1)
    dataframe['best_bid'] = ob['bids'][0][0]
    dataframe['best_ask'] = ob['asks'][0][0]
```

Even guarded, such values differ between backtest and dry-run, so signals built on them cannot be validated by backtesting. During hyperopt the DataProvider is only usable in `populate_indicators()` inside the strategy, not in the entry/exit methods.

## Latest candle in callbacks

`.iloc[-1]` is safe in callbacks because `get_analyzed_dataframe()` only returns candles the simulation may see. It is not safe in `populate_*`.

```python
dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
last_candle = dataframe.iloc[-1].squeeze()
```

Do not use `current_time` to look up the latest candle: it points to the incomplete candle. Round a trade's open date with `timeframe_to_prev_date(self.timeframe, trade.open_date_utc)` to find the trade candle (it may be missing right after entry).

## Wallets

`self.wallets` exposes `get_free(asset)`, `get_used(asset)`, `get_total(asset)`. Check `if self.wallets:` first. In `populate_*` during backtesting it returns the full configured wallet; in callbacks the simulated wallet.

## Trades from the database

`Trade.get_trades_proxy(pair=..., is_open=False, open_date=...)` returns trades. It is not supported in `populate_*` during backtesting or hyperopt (returns empty results). See trade-object.md. The docs example for summing profit contains a stray `]` in the call; do not copy it verbatim.

## Pair locks

`self.lock_pair(pair, until, reason)`, `self.unlock_pair(pair)`, `self.unlock_reason(reason)`, `self.is_pair_locked(pair)`. `until` must be a future datetime and is rounded up to the next candle. Manual locking does not work in backtesting (only Protections do). Freqtrade itself locks a pair until the end of the current candle after an exit.

## Persistent per-trade data

Inside callbacks that get a `trade`: `trade.set_custom_data(key="k", value=v)`, `trade.get_custom_data(key="k", default=0)`, `trade.get_custom_data_entry(key=...)`, `trade.delete_custom_data(key=...)`. Values must be JSON serializable; keep them small (`bool`, `int`, `float`, `str`). The older non-persistent `custom_*` dict on the strategy class is deprecated and lost on restart.
