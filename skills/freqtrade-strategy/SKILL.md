---
name: freqtrade-strategy
description: Use when you need to write, edit or debug a Freqtrade strategy class (IStrategy) in Python - populate_indicators, populate_entry_trend, populate_exit_trend, enter_long/enter_short/exit_long/exit_short, enter_tag/exit_tag, minimal_roi, stoploss, timeframe, startup_candle_count, informative pairs (@informative, merge_informative_pair), DataProvider, can_short, leverage. Covers strategy anatomy, signals, colliding signals, stoploss types, futures shorting, Trade object, and common lookahead mistakes.
license: GPL-3.0
---

# Freqtrade strategy development

How to write a correct Freqtrade strategy. Freqtrade version assumed: 2026.10, strategy interface version 3. Every example class here was run through backtesting, `lookahead-analysis` and `recursive-analysis` on test data ([tests/strategies/](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/)). They are teaching examples, not profitable strategies; never present them as such.
Sample outputs and trade counts in this skill and its references were observed on Binance sample data (2026-07..10), before the repo test data moved to OKX; rerun the commands on your data, expect different numbers.

Rules:
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives. A pass does not prove the strategy is clean; it only checks signals that fired in the tested timerange.
- Keep `dry_run: true`. Never set `dry_run: false` unless the user explicitly asks.
- Look names up in the references; do not invent attributes, columns or callback signatures. If unsure, run `freqtrade list-strategies` and the commands below to find out.
- Futures and shorting need `trading_mode` and `margin_mode` in the config and `can_short = True` in the strategy. Leverage can liquidate the position: warn the user.
- Read the user's existing strategy before editing; change only what was asked.

## Workflow

1. Anatomy: generate or open the file, confirm class name, `INTERFACE_VERSION = 3`, `timeframe`, and that it is in the strategy folder. See references/anatomy.md.
2. Indicators: add only the columns the signals use in `populate_indicators`. Use vectorized pandas, ta-lib (`talib.abstract`), `qtpylib` or pandas-ta. Set `startup_candle_count`. See references/anatomy.md.
3. Entry and exit signals: set `enter_long` / `exit_long` to `1` with `enter_tag` / `exit_tag`, add `volume > 0`, make sure signals cannot collide. See references/signals.md.
4. ROI, stoploss and timeframe: `minimal_roi`, `stoploss` (negative ratio), optional trailing. See references/signals.md and references/stoploss.md.
5. Higher timeframes or other pairs: `@informative` or `merge_informative_pair`. Use DataProvider only with run-mode guards for live-only data. See references/informative-pairs.md and references/dataprovider.md.
6. Shorting and leverage (futures): `can_short`, `enter_short` / `exit_short`, `leverage()` callback. See references/leverage-shorting.md.
7. Check the code against references/common-mistakes.md (lookahead, collisions, startup candles).
8. Advanced exits and stoploss that need trade data (`custom_exit`, `custom_stoploss`, `custom_roi`, position adjustment, confirm callbacks): hand off to freqtrade-callbacks. Backtest and read results: freqtrade-backtesting. Lookahead and recursive checks and hyperopt gating: freqtrade-validation.
9. Run the validation gate below.

## Minimal strategy (tested)

Class IndicatorsExample from [tests/strategies/IndicatorsExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/IndicatorsExample.py): RSI, EMAs and Bollinger Bands, two tagged entries, one tagged exit, ROI, stoploss, startup candles. Full code and explanation: references/anatomy.md and references/signals.md.

<!-- tested: tests/strategies/IndicatorsExample.py lines 9-19 -->
```python
class IndicatorsExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200
```

The exit signal: a column set to `1` (with a tag) for rows where the condition holds:

<!-- tested: tests/strategies/IndicatorsExample.py lines 53-61 -->
```python
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

## Key rules

- The dataframe holds one pair; the last row is the latest closed candle. Never reorder rows or change `open`, `high`, `low`, `close`, `volume`. Always `return dataframe`.
- Signals fire at candle close; the trade opens on the next candle. Vectorize: no row loops, no `iloc` in `populate_*`, use `shift(1)` (never `shift(-1)`) and `rolling()` (never a bare `.mean()`).
- `enter_long` must exist even for a short-only strategy. Exits of one side must not overlap entries of the other (colliding signals are silently ignored).
- `startup_candle_count`: set it from `recursive-analysis`, not by guess. Generated templates can default too low.
- Informative timeframes must be at least the strategy timeframe; merge only through `@informative` or `merge_informative_pair`, never a plain `merge`. `@informative` method names must be unique.
- `orderbook()`, `ticker()`, `funding_rate()` and trade-history calls return live values; do not use them for signals without a run-mode guard, and expect backtests to differ.
- Config values (`stoploss`, `minimal_roi`, `timeframe`, ...) override strategy values.
- Always set a stoploss. Stoploss is leverage-adjusted (at 10x, -0.10 triggers on a 1% move). Compare `trade.liquidation_price` with the stop price rather than assuming the stop fires before liquidation.

## Commands

Check that the strategy loads, then test (add `--config`, `--timerange`, `--strategy-path` as needed; pass global flags after the subcommand):

```bash
freqtrade list-strategies --strategy-path user_data/strategies
freqtrade backtesting --strategy MyStrategy --timerange 20260801-20261001
freqtrade lookahead-analysis --strategy MyStrategy --timerange 20260801-20261001
freqtrade recursive-analysis --strategy MyStrategy --timerange 20260801-20261001
```

## Validation gate

Before reporting the strategy as done:

1. The strategy loads (`freqtrade list-strategies`) and backtests without errors and with trades (`lookahead-analysis` needs trades; widen the timerange if it reports too few).
2. `lookahead-analysis` reports no bias (`has_bias` No, no biased entry/exit signals or indicators). Fix entries before exits. The only blanket exception is FreqAI `set_freqai_targets()` columns. Pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives; explain each to the user, never silently ignore.
3. `recursive-analysis` shows near-zero variance (the project checks use at most 0.5% at the declared `startup_candle_count`); otherwise raise `startup_candle_count`, not the tolerance.
4. Only after 1 to 3, suggest a dry run. Live trading is the user's separate, explicit decision.

Details of these commands and hyperopt: freqtrade-validation.

## Examples in this repo

| File | Shows |
|------|-------|
| [tests/strategies/IndicatorsExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/IndicatorsExample.py) | Indicators, tagged signals, ROI, stoploss, startup candles |
| [tests/strategies/InformativeExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/InformativeExample.py) | `@informative("1h")` decorator |
| [tests/strategies/InformativeMergeExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/InformativeMergeExample.py) | `dp.get_pair_dataframe` plus `merge_informative_pair` |
| [tests/strategies/ShortExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/ShortExample.py) | `can_short`, `enter_short`, `exit_short`, `leverage()` (needs [tests/config.futures.json](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/config.futures.json)) |

## References

- references/anatomy.md - class layout, dataframe rules, imports, startup candles, derived strategies
- references/signals.md - entry/exit columns, tags, collisions, minimal ROI, choosing an exit mechanism
- references/informative-pairs.md - `@informative`, `merge_informative_pair`, funding-rate candles
- references/dataprovider.md - DataProvider methods and backtesting traps, wallets, trades, pair locks, custom data
- references/stoploss.md - static, trailing, on-exchange stoploss, stoploss with leverage
- references/leverage-shorting.md - futures config, `can_short`, `leverage()`, liquidation
- references/trade-object.md - Trade and Order attributes and class methods
- references/common-mistakes.md - wrong vs right snippets for lookahead and signal bugs

## Related skills

freqtrade-setup (install, user directory, data download), freqtrade-config (config keys, pairlists, pricing), freqtrade-callbacks (custom_exit, custom_stoploss, position adjustment), freqtrade-backtesting, freqtrade-validation.

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
