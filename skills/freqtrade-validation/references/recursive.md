Source: docs/recursive-analysis.md#recursive-analysis-command-reference
Source: docs/recursive-analysis.md#why-are-odd-numbered-default-startup-candles-used
Source: docs/recursive-analysis.md#how-does-the-command-work
Source: docs/recursive-analysis.md#understanding-the-recursive-analysis-output
Source: docs/recursive-analysis.md#caveats
Source: docs/strategy-customization.md#strategy-startup-period

# recursive-analysis

A recursive formula defines a term from previous terms (EMA, RSI and many others). In backtesting the bot has the full range; in dry/live it gets only what the exchange returns. Example in the docs: an indicator `steps` that adds 1 per row is 999 at the last of 1000 candles but 499 if only 500 candles were used. So a backtest can differ from dry/live.

## Options (2026.10 help)

```bash
freqtrade recursive-analysis --strategy MyStrategy --timerange 20260801-20261001 -p BTC/USDT --startup-candle 199 499 999 1999
```

- `-p, --pairs`: only one pair is needed (indicators only). Prefer a high-priced pair with moderate volatility (BTC, ETH) to avoid rounding issues; default is the first whitelist pair.
- `--timerange`: docs recommend at least 5000 candles so the benchmark has little recursive error itself (5m: about 18 days).
- `--startup-candle N [N ...]`: startup candle counts to test. Help examples: `199`, `499`, `999`, `1999`. Without it, the test run used 199, 399, the strategy's value (marked `(from strategy)`), 499, 999 and 1999 (observed).
- `--cache` is forced to none.

## Odd default values

The defaults are odd numbers on purpose: the last candle is the current one, the others are startup candles. Binance returns 1000 candles per call; asking for 1001 would make the bot fetch 2000. Exchanges also limit consecutive calls (Binance: 5), so about 5000 candles is the ceiling and the maximum `startup_candle_count` is 4999. The docs warn that exchange limits can change without notice. Observed warning at 1999: `Using 2 calls to get OHLCV ... Please check if you really need 1999 candles`.

## How it works

1. Initial indicator calculation on the full timerange as benchmark.
2. One extra run per startup candle value, with that many candles before the last row.
3. The last row values are compared and the percentage differences are printed.

It does not run the strategy or backtest; it only calculates indicators. It also does a simple lookahead check on indicator values; for the full check use lookahead-analysis.

## Reading the table

Real output (IndicatorsExample, `startup_candle_count = 200`, run with `--startup-candle 30 100 200 499`):

```text
┃     Indicators ┃      30 ┃     100 ┃ 200 (from strategy) ┃     499 ┃
│            rsi │  1.504% │ -0.013% │             -0.000% │       - │
│       ema_fast │ -0.000% │  0.000% │              0.000% │       - │
│       ema_slow │    nan% │  0.013% │             -0.000% │  0.000% │
│ volume_mean_12 │ -0.000% │       - │                   - │       - │
│   bb_lowerband │  0.000% │  0.000% │              0.000% │  0.000% │
```

- Header cells are startup candle counts; cell values are variance against the benchmark.
- `-` is no variance. `nan%` means the indicator cannot be calculated with so few candles (the docs' example: RSI length 30 needs more than 21 candles).
- Docs: assess the table per indicator and decide whether the chosen `startup_candle_count` leaves a variance small enough that the indicator has no effect on entries and exits. Absolute zero (`-`) is not necessarily best, since some indicators need a very long startup to get there.
- Repo rule (`tests/check_results.py`, a repo choice because the docs give no number): fail when any indicator at the `(from strategy)` column differs by more than 0.5%, shows `nan%`, or the column or table is missing.

## Caveats (docs)

- Only the values of the last row are compared. Whether the difference changes your entries or exits is not evaluated.
- The goal is low variance (so the recursion has no real impact on trading decisions), not necessarily exactly zero.
- Only `populate_indicators` and `@informative` methods are calculated. Indicators computed in `populate_entry_trend` or `populate_exit_trend` are skipped (move them into `populate_indicators`).
- Observed: on the lookahead-biased `LookaheadBad` fixture the command printed no result table. Fix lookahead bias first.
- Can also be run via the REST API in webserver mode (`POST /api/v1/recursive_analysis`, poll `/api/v1/background/{job_id}`, read `GET /api/v1/recursive_analysis/{job_id}`). Only one lookahead or recursive analysis runs at a time.

## Choosing startup_candle_count

Set it in the strategy (`startup_candle_count: int = 400`). Freqtrade then loads that many candles before the timerange start (backtesting log: `Loading data from 2026-07-30 14:40:00 up to ...` for a 2026-08-01 timerange and 400 candles). Raise it until every recursive indicator is below the limit you accept at that column. A generated template's default can be too low for its own indicators (see freqtrade-strategy and freqtrade-setup).
