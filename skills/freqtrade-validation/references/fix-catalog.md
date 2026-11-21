Source: docs/strategy-customization.md#looking-into-the-future-while-backtesting
Source: docs/lookahead-analysis.md#examples-of-lookahead-bias
Source: docs/recursive-analysis.md#understanding-the-recursive-analysis-output
Source: docs/strategy-customization.md#strategy-startup-period

# Fix catalog

Backtesting hands the whole dataframe to `populate_*()` at once, so anything that reads other rows' data than the past is invisible in a backtest and wrong live. Each entry shows the WRONG pattern and a RIGHT one. How to read the labels:

- `fixture:` the WRONG code is in tests/fixtures/strategies/ and was run through `lookahead-analysis` (outcome stated). Run `tests/test_lookahead_fixtures.sh` to reproduce.
- `WRONG (untested illustration)`: never run by the repo tests.
- RIGHT blocks with a `tested:` comment are byte-identical to lines of a strategy that passes backtesting, `lookahead-analysis` and `recursive-analysis` in this repo. RIGHT blocks marked docs are copied from the Freqtrade docs and not run.

Fix entries first, then exits, then indicators; re-run both checks after each change.

## 1. Negative shift

Any negative shift looks into the future: `shift(-1)` is the next candle, `shift(-10)` ten candles ahead.

```python
# WRONG, fixture: tests/fixtures/strategies/LookaheadBad.py (flagged: rsi, enter_long, exit_long)
dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14).shift(-1)
```

RIGHT: use positive shifts to look back.

<!-- tested: tests/strategies/ValidationExample.py lines 37-37 -->
```python
                & (dataframe["close"] > dataframe["close"].shift(1))  # previous candle only
```

## 2. Whole-dataframe statistics and normalization

`.mean()`, `.min()`, `.max()`, `.std()`, `.sum()`, `.rank()` and similar without a window compute over the whole dataframe, so every row sees future values. Z-scores, min-max scaling and "relative to the average" columns have the same problem.

```python
# WRONG, fixture: tests/fixtures/strategies/LookaheadBadMean.py (flagged: vol_mean, enter_long)
dataframe["vol_mean"] = dataframe["volume"].mean()
# WRONG, fixture: tests/fixtures/strategies/LookaheadBadZscore.py (flagged: z, enter_long)
dataframe["z"] = (dataframe["close"] - dataframe["close"].mean()) / dataframe["close"].std()
```

RIGHT: windowed statistics. Each row then uses only its own past (the first window rows are NaN, which `startup_candle_count` covers).

<!-- tested: tests/strategies/ValidationExample.py lines 25-28 -->
```python
        # Windowed statistics only: each row sees its own past, never the whole column.
        dataframe["close_mean_48"] = dataframe["close"].rolling(48).mean()
        dataframe["close_std_48"] = dataframe["close"].rolling(48).std()
        dataframe["zscore_48"] = (dataframe["close"] - dataframe["close_mean_48"]) / dataframe["close_std_48"]
```

## 3. Absolute row access in populate methods

`.iloc[-1]`, `.iloc[0]`, `.at[...]` or any fixed position inside `populate_*()` returns a different row in backtesting (the whole range) than in dry/live (only the recent candles). For-loops over rows are slow and easily bias results if the index range is not tightly controlled.

```python
# WRONG, fixture: tests/fixtures/strategies/LookaheadBadIloc.py (flagged: rsi_last)
dataframe["rsi_last"] = dataframe["rsi"].iloc[-1]
```

RIGHT: vectorized columns and `shift()` (see 1). Absolute `iloc` is fine in callbacks, where `self.dp.get_analyzed_dataframe()` returns only candles visible at that time (freqtrade-callbacks).

## 4. Resampling

The docs: `.resample('1h')` uses the left border of the period, so it moves data from the hour boundary to the start of the hour. Mapping a resampled value back to 5m rows with the left edge gave a flagged bias in our fixture.

```python
# WRONG, fixture: tests/fixtures/strategies/LookaheadBadResample.py (flagged: close_1h, enter_long)
h = dataframe.set_index("date")["close"].resample("1h").last()
dataframe["close_1h"] = dataframe["date"].dt.floor("1h").map(h)
# docs RIGHT (not run here): label with the right border
dataframe.resample("1h", label="right").last()
```

Better than resampling by hand: use an informative timeframe (entries 5 and 6), which handles the candle open/close offset for you.

## 5. Merging a longer timeframe with a plain merge

A candle's `date` is its open time, so the 12:00 1h candle (closing at 13:00) would be visible on the 12:05 row. The docs: do not use `.merge()` to combine longer timeframes onto shorter ones.

```python
# WRONG, fixture: tests/fixtures/strategies/LookaheadBadMerge.py
# lookahead-analysis did NOT flag it (false negative); the docs still list it as a bias
dataframe = pd.merge(dataframe, inf[["date", "rsi_1h"]], on="date", how="left").ffill()
```

RIGHT: `merge_informative_pair` (renames to `rsi_1h`, shifts and forward-fills correctly):

<!-- tested: tests/strategies/InformativeMergeExample.py lines 28-33 -->
```python
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.inf_tf)
        informative["rsi"] = ta.RSI(informative, timeperiod=14)
        # Renames the columns to rsi_1h etc. and merges without lookahead bias.
        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.inf_tf, ffill=True
        )
```

Or the `@informative` decorator (method names must be unique):

<!-- tested: tests/strategies/InformativeExample.py lines 23-26 -->
```python
    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe
```

More: freqtrade-strategy references/informative-pairs.md.

## 6. Indicators with a signal period of 1

The docs list `ta.MACD(dataframe, 12, 26, 1)` as introducing bias. In our fixture `lookahead-analysis` did not flag it (so a pass proves nothing here).

```python
# WRONG (docs), fixture: tests/fixtures/strategies/LookaheadBadMacd1.py (not flagged)
macd = ta.MACD(dataframe, 12, 26, 1)
```

RIGHT: keep the signal period at its default (9) or another value above 1:

<!-- tested: tests/strategies/ValidationExample.py lines 22-24 -->
```python
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)  # docs: signalperiod 1 introduces bias
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
```

## 7. Too few startup candles

Recursive indicators (EMA, RSI, MACD, ATR) change with the number of candles they are given. If `startup_candle_count` is too small, backtest values differ from live values. Symptom in `recursive-analysis`: percentages above your limit at the `(from strategy)` column (the example output in SKILL.md shows RSI at 1.504% with 30 candles and about 0 at 200) or `nan%`.

```python
# WRONG (untested illustration): default too low for the indicators used
startup_candle_count: int = 20  # EMA 50 and RSI 14 need far more
```

RIGHT: raise it until `recursive-analysis` is clean for every indicator, and say which run chose the number:

<!-- tested: tests/strategies/ValidationExample.py lines 17-18 -->
```python
    # EMA/RSI/MACD are recursive: recursive-analysis showed 400 candles is enough (see freqtrade-validation).
    startup_candle_count: int = 400
```

The same applies to informative timeframes: the startup count is in main-timeframe candles, so a 1h indicator needs enough 5m candles to cover its own startup.

## 8. Indicators computed outside populate_indicators

`recursive-analysis` only calculates `populate_indicators` and `@informative` methods. Move indicator math out of `populate_entry_trend` / `populate_exit_trend`, otherwise it is not checked.

```python
# WRONG (untested illustration): indicator created in the entry method is not checked
def populate_entry_trend(self, dataframe, metadata):
    dataframe["ema"] = ta.EMA(dataframe, timeperiod=50)
```

RIGHT: create the column in `populate_indicators` (see lines 20-29 of tests/strategies/ValidationExample.py, quoted above in parts).

## 9. Logic that depends on the pairlist (false positive)

`lookahead-analysis` backtests each pair alone. `len(self.dp.current_whitelist())` in `leverage()` or `custom_stake_amount()`, or ranking one pair against others in `populate_*`, is reported as biased. Remove the dependence or explain the flag to the user.

## 10. Biased logic in callbacks

Callbacks read the dataframe through `self.dp.get_analyzed_dataframe()`; they are only as safe as the indicators in it. `lookahead-analysis` forces market orders, so `custom_entry_price()` and `custom_exit_price()` are not exercised by it.

## After the fix

Re-run `lookahead-analysis` and `recursive-analysis` (SKILL.md). Then run a normal backtest (freqtrade-backtesting) and expect results to get worse than before: that is usually the true performance (docs: removing biased conditions "will usually make the strategy significantly worse").
