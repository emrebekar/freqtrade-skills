Source: docs/strategy-customization.md#entry-signal-rules
Source: docs/strategy-customization.md#exit-signal-rules
Source: docs/strategy-customization.md#minimal-roi
Source: docs/strategy-customization.md#colliding-signals
Source: docs/strategy-advanced.md#enter-tag
Source: docs/strategy-advanced.md#exit-tag
Source: docs/includes/strategy-exit-comparisons.md#exit-logic-comparisons
Source: docs/strategy-101.md#making-trades

# Entry and exit signals

Signals are dataframe columns set to `1`. They are evaluated at candle close; the order is placed at the next candle.

| Column | Meaning |
|--------|---------|
| `enter_long` | Open a long. Mandatory column, even for short-only strategies. |
| `enter_short` | Open a short. Needs `can_short = True` and futures. |
| `exit_long` / `exit_short` | Exit the long / short by signal. |
| `enter_tag` / `exit_tag` | Names for the signal. Shown in backtest results; the exit tag becomes the exit reason. |

Always include `dataframe["volume"] > 0` so the bot does not trade in no-activity periods. Use `use_exit_signal = False` (strategy or config) to turn exit signals off; collision rules still apply.

## Tagged entries and exits (tested)

Two entry signals with different tags, one exit signal. Setting value and tag in one `.loc` assignment keeps them together:

<!-- tested: tests/strategies/IndicatorsExample.py lines 32-61 -->
```python
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)  # Signal: oversold
                & (dataframe["close"] < dataframe["bb_lowerband"])  # Guard: below lower band
                & (dataframe["volume"] > dataframe["volume_mean_12"])
                & (dataframe["volume"] > 0)  # Make sure Volume is not 0
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_bb_low")
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])  # Signal
                & (dataframe["rsi"] < 60)  # Guard: keeps it away from the exit signal below
                & (dataframe["close"] > dataframe["close"].shift(1))  # previous candle: shift(1), never shift(-1)
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "ema_cross")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] > 70)
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "rsi_high")
        return dataframe
```

Tag facts from the docs:
- There is a single `enter_tag` column used for long and short. It is "last write wins": when several signals fire on the same candle, the last assignment's tag sticks. To keep all tags, start with `dataframe["enter_tag"] = ""` and append with `+=` per signal (same for `exit_tag`).
- `enter_tag` is limited to 255 characters, `exit_reason` to 100; the rest is truncated.
- `trade.enter_tag` is readable in callbacks such as `custom_exit` (see freqtrade-callbacks).

## Short signals (tested)

Short entries and exits use the same pattern with `enter_short` / `exit_short`. See leverage-shorting.md for the config and the full strategy.

<!-- tested: tests/strategies/ShortExample.py lines 36-66 -->
```python
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)
                & (dataframe["close"] < dataframe["bb_lowerband"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_low")
        dataframe.loc[
            (
                (dataframe["rsi"] > 65)
                & (dataframe["close"] > dataframe["bb_upperband"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_short", "enter_tag"],
        ] = (1, "rsi_high")
        return dataframe

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

## Colliding signals

When conflicting signals are `1` on the same candle, freqtrade does nothing and ignores the entry. The entry is lost, no trade opens. Entry is ignored when more than one of these is set:

- `enter_long` with `exit_long` or `enter_short`
- `enter_short` with `exit_short` or `enter_long`

In ShortExample the exits use `crossed_above/below(rsi, 50)` so that `exit_long` can never be `1` on a candle where `enter_short` (RSI above 65) is `1`.

## Minimal ROI

`minimal_roi` is a dict `{minutes_since_open: required_profit_ratio}`. The trade exits when the profit has reached the value of the longest elapsed key. Fees are included. The tested examples use:

```python
minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
```

That means: exit at 4% any time, at 2% after 30 minutes, at 1% after 60 minutes. A key `"40": 0.0` means "exit when not losing after 40 minutes". `minimal_roi = {}` disables ROI. Per the docs (minimal ROI), `minimal_roi` takes `trade.open_date` as reference: the time the first order was placed, even if that order fills late. `minimal_roi` and `stoploss` in the config override the strategy values.

ROI times in candles instead of minutes (docs example, not tested here):

```python
from freqtrade.exchange import timeframe_to_minutes

class AwesomeStrategy(IStrategy):
    timeframe = "1d"
    timeframe_mins = timeframe_to_minutes(timeframe)
    minimal_roi = {
        "0": 0.05,                      # 5% for the first 3 candles
        str(timeframe_mins * 3): 0.02,  # 2% after 3 candles
        str(timeframe_mins * 6): 0.01,  # 1% After 6 candles
    }
```

## Which exit mechanism

| Mechanism | Use for | Do not use for |
|-----------|---------|----------------|
| `populate_exit_trend()` | Exit signals computed from indicators, vectorized | Per-trade conditions or anything needing trade data |
| `custom_exit()` | Per-trade conditions, profit-based exits, fully closes the trade | Indicator-only exits; as a proxy for `custom_stoploss()` (rate-based exits are inaccurate in backtesting) |
| `custom_stoploss()` | Dynamic stoploss from trade data (also used for stoploss on exchange) | Immediate exit on a condition |
| `custom_roi()` | Dynamic take-profit threshold | Immediate exit; static ROI (use `minimal_roi`) |

The three `custom_*` callbacks are covered by freqtrade-callbacks.

## Why a signal may not open a trade

Not enough stake or wallet funds; all `max_open_trades` slots used; a trade for that pair is already open (positions do not stack, apart from position adjustment); entry and exit collide; or a confirm callback rejects it.

## Docs inconsistencies to avoid copying

The exit-tag example in strategy-advanced.md references an undefined variable (`rsi_exit_signal2`) and its `custom_exit` example contains syntax errors (missing colon after `else`, `and if`, an unclosed string). Treat the tag pattern as the idea and write your own variables.
