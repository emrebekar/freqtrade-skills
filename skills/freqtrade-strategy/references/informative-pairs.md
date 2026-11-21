Source: docs/strategy-customization.md#informative-pairs
Source: docs/strategy-customization.md#informative-pairs-decorator-informative
Source: docs/strategy-customization.md#merge_informative_pair
Source: docs/strategy-customization.md#complete-dataprovider-sample

# Informative pairs and timeframes

Use a higher timeframe (or another pair) as extra context. Two supported ways, each tested on the repo test data (5m main timeframe, 1h informative):

1. `@informative("1h")` decorator: shortest, columns appear in the dataframe before `populate_indicators()` runs.
2. `DataProvider` + `merge_informative_pair()`: full control, needed when one informative pair must use data from another.

Do not mix both patterns for the same informative timeframe in one strategy: combining them is not documented and not tested here. The two example strategies each use one pattern and produce identical backtest results (120 trades on the test data).

## Rules

- The informative timeframe must be equal to or higher than the strategy timeframe. A smaller one is not recommended with these helpers.
- Never use a plain `.merge()` for this: candle `date` is the open time, so a 1h candle opened at 12:00 would be visible at 12:05 although it closes at 13:00. `merge_informative_pair()` and `@informative` shift the informative date by one informative candle to prevent this lookahead.
- Pairs listed in `informative_pairs()` are refreshed with the whitelist; keep the list short and prefer resampling to longer timeframes where possible. They are not traded unless also whitelisted.
- `startup_candle_count` does not necessarily change with informative timeframes; it is the maximum candles any timeframe needs for stable indicators. Check with `recursive-analysis`.

## Pattern 1: `@informative` decorator (tested)

Source file: InformativeExample.

<!-- tested: tests/strategies/InformativeExample.py lines 12-30 -->
```python
    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # RSI is recursive; 200 main candles cover the 1h RSI as well (recursive-analysis checked).
    startup_candle_count: int = 200

    # Available in populate_indicators and later as "rsi_1h".
    # Method names must be unique across all @informative methods.
    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe
```

The decorated method's columns get the suffix `_1h` in the main dataframe: `rsi` becomes `rsi_1h`. Use it in `populate_entry_trend` as `dataframe["rsi_1h"]`. The full file is [tests/strategies/InformativeExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/InformativeExample.py).

Decorator facts from the docs:
- Signature: `informative(timeframe, asset="", fmt=None, *, candle_type=None, ffill=True, cache=True)`.
- `asset` selects another pair, e.g. `@informative("1h", "BTC/{stake}")` gives `btc_usdt_rsi_1h` when the stake currency is USDT (use the `{stake}` placeholder instead of hard-coding it). Without `asset` the current pair is used and columns are `{column}_{timeframe}`.
- `fmt` customizes column names, e.g. `fmt="{base}_{column}_{timeframe}"`.
- Decorators can be stacked on one method (`@informative("30m")` and `@informative("1h")` give `rsi_30m`, `rsi_1h`).
- Method names must be unique. A repeated name silently overwrites the earlier method and its columns vanish without an error.
- Decorated methods run in isolation and cannot see other informative pairs. If one informative pair needs another, use pattern 2.
- `cache=True` (default) recomputes only when a new informative candle exists (dry/live). Use `cache=False` for methods with external state or side effects.
- The column name `date_merge` is reserved while informative decorators are merged.
- With hyperopt use the parameter's `.range` instead of `.value` inside informative methods.
- `candle_type` selects other candle types, e.g. `@informative("1h", candle_type="funding_rate")`.

## Pattern 2: DataProvider and `merge_informative_pair` (tested)

Source file: InformativeMergeExample.

<!-- tested: tests/strategies/InformativeMergeExample.py lines 21-35 -->
```python
    inf_tf = "1h"

    def informative_pairs(self):
        # Download and cache the informative timeframe for every whitelisted pair.
        return [(pair, self.inf_tf) for pair in self.dp.current_whitelist()]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.inf_tf)
        informative["rsi"] = ta.RSI(informative, timeperiod=14)
        # Renames the columns to rsi_1h etc. and merges without lookahead bias.
        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.inf_tf, ffill=True
        )
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe
```

`merge_informative_pair(dataframe, informative, timeframe, timeframe_inf, ffill=True)` renames every informative column with the timeframe suffix (`date_1h`, `open_1h`, `rsi_1h`, ...), merges without lookahead and forward-fills so the 1h value is present in every 5m row. Calculate all informative indicators before calling it. Always check `self.dp` is available in `populate_indicators` if the strategy may be loaded without a DataProvider (docs sample: `if not self.dp: return dataframe`).

`informative_pairs()` returns `(pair, timeframe)` tuples (optionally a third element for the candle type: `""`, `"spot"`, `"futures"`, `"mark"`). Use `self.dp.current_whitelist()` for dynamic whitelists.

## Funding rate and mark candles

On futures, historic funding rates have one row per funding event, not per candle. Merge them; do not assign the column directly (positional alignment gives wrong or `NaN` values). Docs example (not tested here, needs `funding_rate` data downloaded):

```python
funding_rates = self.dp.get_pair_dataframe(
    pair=metadata['pair'], timeframe='1h', candle_type="funding_rate"
)
# Adds the column as "funding_rate_1h", forward-filled between funding events.
dataframe = merge_informative_pair(
    dataframe, funding_rates, self.timeframe, '1h', ffill=True
)
```

The same works with `@informative('1h', candle_type='funding_rate')`. The bot refuses to start if the exchange cannot serve a requested candle type.
