Source: docs/includes/pairlists.md#pairlists-and-pairlist-handlers
Source: docs/includes/pairlists.md#available-pairlist-handlers
Source: docs/includes/pairlists.md#full-example-of-pairlist-handlers
Source: docs/commands/test-pairlist.md

# Pairlists

Configured in `pairlists`, a list of handler dicts run in order. The first must be a generator (`StaticPairList`, `VolumePairList`, `ProducerPairList`, `RemotePairList`, `MarketCapPairList`, `PercentChangePairList` or `CrossMarketPairList`); the rest are filters. Inactive markets and `exchange.pair_blacklist` entries are always removed. The blacklist supports regex (`BNB/.*`, `.*DOWN/BTC`, `.*UP/BTC`).

Test any pairlist before use:

```bash
freqtrade test-pairlist --config user_data/config.json
freqtrade test-pairlist --config user_data/config.json --quote USDT --print-json
freqtrade test-pairlist --config user_data/config.json -1
```

Options: `-c/--config`, `--quote Q [Q ...]`, `-1/--one-column`, `--print-json`, `--exchange EXCHANGE` (only without a config), `--userdir`, `-v`.

## Backtesting support

`VolumePairList`, `PercentChangePairList`, `DelistFilter`, `FullTradesFilter` and `PerformanceFilter` do not support backtesting (`PrecisionFilter` not with multiple strategies). For backtests use a `StaticPairList` with a fixed whitelist, ideally exported from a dry-run/live pairlist.

## StaticPairList (default)

Uses `exchange.pair_whitelist` minus `exchange.pair_blacklist`; both accept regex (`.*/USDT`).

```json
"exchange": {
    "name": "binance",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "pair_blacklist": ["BNB/USDT"]
},
"pairlists": [
    {"method": "StaticPairList"}
]
```

`"allow_inactive": true` skips the active-market check (backtesting expired pairs). In a follow-up position, all whitelist pairs are appended to the end of the list.

## VolumePairList

Top `number_assets` pairs by `quoteVolume` (the only `sort_key`). In first position it ignores `pair_whitelist` and takes all markets with the stake currency; later in the chain it sorts what earlier handlers returned.

```json
"pairlists": [
    {
        "method": "VolumePairList",
        "number_assets": 20,
        "sort_key": "quoteVolume",
        "min_value": 0,
        "max_value": 8000000,
        "refresh_period": 1800
    }
]
```

`min_value`/`max_value` bound the volume. `refresh_period` is seconds (default 1800). Advanced mode builds volume from candles: `lookback_days` (implies 1d candles) or `lookback_timeframe` + `lookback_period`; then `refresh_period` must not be smaller than the candle size. In first position with a lookback this downloads candles for all pairs and is slow; narrow the list first. On exchanges without 24h volume (e.g. Gemini) use `"refresh_period": 86400, "lookback_days": 1`.

## Other generators

- `PercentChangePairList`: `number_assets`, `min_value`, `max_value`, `sort_direction` (`asc`/`desc`), `refresh_period` (1800), `lookback_days` / `lookback_timeframe` / `lookback_period`. Ticker based by default; candle based with lookback settings.
- `MarketCapPairList`: `number_assets`, `max_rank`, `refresh_period` (86400), `mode` (`whitelist`/`blacklist`), `categories` (CoinGecko category ids such as `layer-1`). Uses CoinGecko; duplicate symbols on CoinGecko can pick the wrong coin; each category costs an API call; `max_rank` above 250 risks rate limits.
- `RemotePairList`: `pairlist_url` (URL or `file:///path`), `mode`, `processing_mode` (`filter`/`append`), `number_assets`, `refresh_period`, `keep_pairlist_on_failure` (true), `read_timeout` (60), `bearer_token`, `save_to_file`. The source returns `{"pairs": [...], "refresh_period": 1800}`.
- `ProducerPairList`: `number_assets`, `producer_name`; needs consumer mode.
- `CrossMarketPairList`: `pairs_exist_on` is `both_markets` (default) or `current_market_only`.

## Filters

| Filter | Settings (defaults) | Effect |
|--------|---------------------|--------|
| `AgeFilter` | `min_days_listed` (10), `max_days_listed` (none) | Removes pairs listed too recently or too long ago. |
| `DelistFilter` | `max_days_from_now` (0 = any future delisting) | Removes pairs about to be delisted. Bybit Futures, Bitget Futures, Binance (Binance spot live only). |
| `FullTradesFilter` | - | When slots are full, shrinks the whitelist to in-trade pairs. Put it second in the chain. |
| `OffsetFilter` | `offset`, `number_assets` | Skips the first `offset` pairs, then takes `number_assets`. |
| `PairInformationFilter` | `selection_mode` (`whitelist`/`blacklist`), `info_key` (dot notation, e.g. `info.contractType`), `info_compare_value` | Filters by ccxt market info fields. |
| `PerformanceFilter` | `minutes` (0 = all time), `min_profit` | Sorts by past trade performance; needs a few hundred trades. Do not use `min_profit` without `minutes`. |
| `PrecisionFilter` | - | Drops coins whose stoploss price would be distorted by precision rounding (>= 1%). Pointless for futures. |
| `PriceFilter` | `min_price`, `max_price`, `max_value`, `low_price_ratio` | At least one of `min_price`, `max_price`, `low_price_ratio` must be set. |
| `ShuffleFilter` | `shuffle_frequency` (`candle` default, or `iteration`), `seed` | Randomizes order; `seed` applies only in backtesting modes. |
| `SpreadFilter` | `max_spread_ratio` (0.005) | Drops pairs whose ask/bid spread is above the ratio. |
| `RangeStabilityFilter` | `lookback_days` or (`lookback_timeframe` default `1d` + `lookback_period`), `min_rate_of_change`, `max_rate_of_change`, `refresh_period`, `sort_direction` | Drops pairs with too small or too large range (removes stablecoins). Setting `lookback_days` and `lookback_period` together is an error. |
| `VolatilityFilter` | same lookback settings, `min_volatility`, `max_volatility`, `refresh_period`, `sort_direction` | Drops pairs outside the volatility band (std dev of log returns). |

## Full example

```json
"exchange": {
    "pair_whitelist": [],
    "pair_blacklist": ["BNB/BTC"]
},
"pairlists": [
    {
        "method": "VolumePairList",
        "number_assets": 20,
        "sort_key": "quoteVolume"
    },
    {
        "method": "DelistFilter",
        "max_days_from_now": 0
    },
    {"method": "AgeFilter", "min_days_listed": 10},
    {"method": "PrecisionFilter"},
    {"method": "PriceFilter", "low_price_ratio": 0.01},
    {"method": "SpreadFilter", "max_spread_ratio": 0.005},
    {
        "method": "RangeStabilityFilter",
        "lookback_days": 10,
        "min_rate_of_change": 0.01,
        "refresh_period": 86400
    },
    {
        "method": "VolatilityFilter",
        "lookback_days": 10,
        "min_volatility": 0.05,
        "max_volatility": 0.50,
        "refresh_period": 86400
    },
    {"method": "ShuffleFilter", "seed": 42}
]
```
