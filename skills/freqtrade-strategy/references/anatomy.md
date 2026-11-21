Source: docs/strategy-101.md#structure-of-a-basic-strategy
Source: docs/strategy-customization.md#anatomy-of-a-strategy
Source: docs/strategy-customization.md#dataframe
Source: docs/strategy-customization.md#strategy-startup-period
Source: docs/strategy-customization.md#strategy-file-loading
Source: docs/includes/strategy-imports.md#imports-necessary-for-a-strategy
Source: docs/strategy-advanced.md#derived-strategies

# Strategy anatomy

A strategy is a Python class that subclasses `IStrategy`. It lives in `user_data/strategies/` (or any folder passed with `--strategy-path`). Commands take the class name, not the file name. `freqtrade list-strategies` shows every loadable strategy with a status field.

```bash
freqtrade new-strategy --strategy AwesomeStrategy
freqtrade new-strategy --strategy AwesomeStrategy --template minimal
freqtrade list-strategies
```

`--template` accepts `minimal` (empty), `full` (default, many sample indicators) and `advanced` (all callbacks; per the CLI help, verified on 2026.10). Generated templates are starting points and not profitable. Check the template's `startup_candle_count`: the template default can be too low for its own indicators (see "Startup candles").

## Required pieces

| Piece | Purpose |
|-------|---------|
| `INTERFACE_VERSION = 3` | Interface version; 3 is the current one and the default. |
| `timeframe` | Candle size, e.g. `"5m"`. Also readable as `self.timeframe`. |
| `populate_indicators(self, dataframe, metadata)` | Adds indicator columns. Must return the dataframe. |
| `populate_entry_trend(...)` | Sets `enter_long` (and `enter_short`) to `1`. `enter_long` is mandatory even for short-only strategies. |
| `populate_exit_trend(...)` | Sets `exit_long` (and `exit_short`) to `1`. |
| `minimal_roi`, `stoploss` | Exit rules independent of signals. Strongly recommended. |
| `can_short` | `False` by default; `True` enables short signals (futures only). |
| `startup_candle_count` | Candles needed before indicators are stable. |

Never remove or change the columns `open`, `high`, `low`, `close`, `volume`. Never sort, shuffle or reorder rows: the last row is assumed to be the latest closed candle. `metadata["pair"]` is the pair (`XRP/BTC`, or `XRP/BTC:BTC` on futures). Do not modify `metadata`; it does not persist between methods.

## Dataframe rules

- Each pair has its own dataframe indexed by candle; the latest complete candle is the last row. Incomplete candles are never in it.
- In backtesting the full time range is passed to the `populate_*` methods at once. Use vectorized pandas operations, not loops, and `shift()` instead of `iloc`.
- `if dataframe["rsi"] > 30:` fails with "truth value of a Series is ambiguous". Write `dataframe.loc[(dataframe["rsi"] > 30), "enter_long"] = 1`.
- Signals are generated on candle close. In backtesting the trade opens at the next candle's open; in dry/live it opens a few seconds after that.
- Only add indicators that entry/exit logic (or another indicator) uses.

## Tested minimal example

Source file: IndicatorsExample, a teaching strategy that is not profitable. It passes `lookahead-analysis` and `recursive-analysis` on the repo test data (2026-08-01 to 2026-10-01, 5m, BTC/USDT and ETH/USDT).

<!-- tested: tests/strategies/IndicatorsExample.py lines 12-30 -->
```python
    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["volume_mean_12"] = dataframe["volume"].rolling(12).mean()  # rolling, not .mean()
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        return dataframe
```

Indicator libraries installed with Freqtrade: ta-lib (`import talib.abstract as ta`), pandas-ta, technical (`from technical import qtpylib`).

## Startup candles

Some indicators need history before their values are right (EMA, RSI and other recursive indicators). Set `startup_candle_count` to the maximum candles needed. Backtesting then loads that many extra candles before `--timerange` and drops the unstable part. Do not guess: run `recursive-analysis` and raise the value until the variance of every indicator is near 0% (see freqtrade-validation). With informative timeframes the value does not necessarily change: it is the maximum period (in candles) that any of the informative timeframes needs for stable indicators.

- Keep it below `ohlcv_candle_limit * 5` (500 * 5 on most exchanges); that is all that is available in dry/live.
- Warning "Using x calls to get OHLCV" means the value is large; each extra call slows candle refresh. Capped at 5 calls.
- If startup data is missing, backtesting shifts the start of the timerange forward.

## Imports

The docs recommend this baseline import block. The tested examples import only what they use. `AnnotationType` appears in the generated template but is not in the docs block.

```python
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Dict, Optional, Union, Tuple

from freqtrade.strategy import (
    IStrategy,
    Trade, 
    Order,
    PairLocks,
    informative,  # @informative decorator
    # Hyperopt Parameters
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # timeframe helpers
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    # Strategy helper functions
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from technical import qtpylib
```

## Derived strategies and versioning

A strategy can subclass another strategy and override attributes or methods. Keep each in its own file and import the parent (`from myawesomestrategy import MyAwesomeStrategy`). Same-file subclasses cause problems with hyperopt parameter files. After changing a parent file, run backtesting once with `--cache none`; only changes in the child file invalidate the backtest cache.

`def version(self) -> str: return "1.1"` sets a strategy version. Freqtrade keeps no history, so use git.

## Bot modes

Strategies run in backtesting, hyperopt, dry-run (forward test), live and FreqAI. Always dry-run before live. Pass the strategy to the bot with `freqtrade trade --strategy AwesomeStrategy` (dry-run or live depends on `dry_run` in the config; keep `dry_run: true` until validated).
