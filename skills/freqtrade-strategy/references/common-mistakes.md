Source: docs/strategy-customization.md#common-mistakes-when-developing-strategies
Source: docs/strategy-customization.md#colliding-signals
Source: docs/strategy-customization.md#dataframe
Source: docs/lookahead-analysis.md#examples-of-lookahead-bias
Source: docs/lookahead-analysis.md#caveats

# Common mistakes

Backtesting hands the full time range to `populate_*()` at once, so any use of data from later rows is invisible in a backtest and fatal in dry/live. Lookahead mistakes make backtests look great and trade badly. Run `lookahead-analysis` and `recursive-analysis` (see freqtrade-validation) and treat them as helpers: a clean result does not prove the strategy is clean, and `lookahead-analysis` only checks signals that fired in the tested timerange.

Each entry below shows a WRONG snippet (illustration only, never run by the tests) and a RIGHT snippet. RIGHT snippets marked "tested" are byte-identical to lines of a strategy that passes the repo checks; unmarked ones come straight from the docs.

## 1. Negative shift

```python
# WRONG: shift(-1) is the NEXT candle's close, unavailable live
dataframe["next_close"] = dataframe["close"].shift(-1)
```

Any negative shift (`shift(-10)` looks 10 candles ahead) is lookahead. Use positive shifts to look back.

RIGHT:

<!-- tested: tests/strategies/IndicatorsExample.py lines 46-46 -->
```python
                & (dataframe["close"] > dataframe["close"].shift(1))  # previous candle: shift(1), never shift(-1)
```

## 2. Whole-column aggregates

`mean()`, `min()`, `max()` and similar without a window compute over the whole dataframe, so every row "sees" future values.

```python
# WRONG
dataframe["mean_volume"] = dataframe["volume"].mean()
```

RIGHT:

<!-- tested: tests/strategies/IndicatorsExample.py lines 25-25 -->
```python
        dataframe["volume_mean_12"] = dataframe["volume"].rolling(12).mean()  # rolling, not .mean()
```

## 3. Absolute row access in populate methods

```python
# WRONG in populate_*(): different row in backtesting vs dry/live
last_rsi = dataframe["rsi"].iloc[-1]
```

Use vectorized columns and `shift()` instead. `.iloc[-1]` is fine inside callbacks where `get_analyzed_dataframe()` only returns visible candles. Loops over rows are slow and easily introduce lookahead.

## 4. Resampling the wrong edge

```python
# WRONG: labels a bucket with its left border, moving data to the start of the hour
dataframe.resample("1h").last()
# RIGHT (docs): label with the right border
dataframe.resample("1h", label="right").last()
```

Better: use an informative timeframe (next item) instead of resampling.

## 5. Plain merge of a longer timeframe

```python
# WRONG: candle date is the OPEN time; the 1h candle from 12:00 is visible at 12:05
dataframe = pd.merge(dataframe, informative_1h, on="date", how="left")
```

RIGHT (tested): `merge_informative_pair` shifts and forward-fills correctly, or use the `@informative` decorator (informative-pairs.md).

<!-- tested: tests/strategies/InformativeMergeExample.py lines 28-33 -->
```python
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.inf_tf)
        informative["rsi"] = ta.RSI(informative, timeperiod=14)
        # Renames the columns to rsi_1h etc. and merges without lookahead bias.
        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.inf_tf, ffill=True
        )
```

## 6. Indicators with a signal period of 1

`ta.MACD(dataframe, 12, 26, 1)` introduces bias (docs). Use the default signal period of 9 or another value above 1.

## 7. Colliding signals

If `enter_long` and `exit_long` (or `enter_long` and `enter_short`, or `enter_short` and `exit_short`) are both `1` on one candle, freqtrade ignores the entry. You silently lose trades.

```python
# WRONG: exit_long fires on every candle where RSI is above 55, including every
# candle where enter_short (RSI above 70) fires, so enter_short is always ignored
dataframe.loc[(dataframe["rsi"] > 55), "exit_long"] = 1
dataframe.loc[(dataframe["rsi"] > 70), "enter_short"] = 1
```

RIGHT (tested): exits that cannot overlap the opposite entry condition.

<!-- tested: tests/strategies/ShortExample.py lines 55-66 -->
```python
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when RSI returns to 50. Not above 65/below 35: that would collide with
        # the entry signals of the opposite side (enter_short vs exit_long).
        dataframe.loc[
            (qtpylib.crossed_above(dataframe["rsi"], 50) & (dataframe["volume"] > 0)),
            ["exit_long", "exit_tag"],
        ] = (1, "rsi_mid")
        dataframe.loc[
            (qtpylib.crossed_below(dataframe["rsi"], 50) & (dataframe["volume"] > 0)),
            ["exit_short", "exit_tag"],
        ] = (1, "rsi_mid")
        return dataframe
```

## 8. Too few startup candles

Indicators such as EMA and RSI are recursive and wrong during the first candles. Generated templates may default to a `startup_candle_count` that is too low (the setup skill's template check raised it to 200 for the same reason). Check with `recursive-analysis` and raise the value until variance is near zero. In the tested examples:

<!-- tested: tests/strategies/IndicatorsExample.py lines 18-19 -->
```python
    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200
```

## 9. Live-only data used in populate methods

`dp.orderbook()`, `dp.ticker()`, `dp.funding_rate()`, `dp.check_delisting()` return current values. In backtesting the whole column gets one value. Guard with `self.dp.runmode.value in ("live", "dry_run")` and do not base signals on them. Trade history (`Trade.get_trades_proxy`) and manual pair locks are also not usable in `populate_*` during backtesting.

## 10. Wrong column handling

- Short-only strategy without an `enter_long` column: `enter_long` must be set even if only shorting.
- `enter_short` signals with `can_short = False` (the default) are ignored, even on futures.
- Overwriting `open`, `high`, `low`, `close`, `volume`, sorting or reordering the dataframe, or forgetting `return dataframe`.
- `if dataframe["rsi"] > 30:` (use `.loc` with a boolean expression).
- Two `@informative` methods with the same name: the first silently disappears.
- Missing `dataframe["volume"] > 0` guard: trades in candles without volume.

## 11. Logic that depends on the pairlist

`lookahead-analysis` backtests each pair alone. A `populate_*` method, `leverage()` or `custom_stake_amount()` that uses `len(self.dp.current_whitelist())` or ranks against other pairs will be reported as biased (false positive).

## 12. Trusting the backtest

Backtests assume all orders fill and enter at the next candle's open. Dry-run differs (delays, unfilled limit orders). Dry-run before live, and do not assume results of public strategies are achievable.

Informative timeframe smaller than the strategy timeframe, a stoploss that sits beyond the liquidation price with leverage, and live-only values in signals are covered in informative-pairs.md, leverage-shorting.md and dataprovider.md.
