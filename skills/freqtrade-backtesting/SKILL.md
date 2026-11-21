---
name: freqtrade-backtesting
description: Use when you need to run, read or compare Freqtrade backtests, analyze entry and exit tags, or plot results. Covers freqtrade backtesting (--timerange, --timeframe-detail, --breakdown, --export trades/signals, --cache none, --enable-protections, --strategy-list), the report tables and summary metrics, the backtesting assumptions that limit trust in results, backtesting-analysis (--analysis-groups, --indicator-list), backtesting-show, plot-dataframe and plot-profit.
license: GPL-3.0
---

# Freqtrade backtesting

Run a strategy over historical candles, read the result honestly, dig into which entries and exits made or lost money. Freqtrade version assumed: 2026.10. Outputs shown below were produced by running the repo's teaching strategy `IndicatorsExample` (tests/strategies/) on the repo's test data (BTC/USDT and ETH/USDT, 5m, 2026-08-01 to 2026-09-30). That strategy is not profitable in any meaningful sense; never present its numbers as a result.

Rules:
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass (see freqtrade-validation). A backtest of a biased strategy is meaningless, so run validation before trusting any number here. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives.
- A backtest result is an estimate under simplifying assumptions (see "Assumptions"). The docs say it never replaces dry-run. Never describe backtest profit as expected profit.
- Keep `dry_run: true`. Never set `dry_run: false` unless the user explicitly asks.
- Do not report numbers you did not run. Quote the actual output, with the timerange, pairs and fee settings used.

## Workflow

1. Data: download candles for every pair and timeframe the strategy uses, including informative timeframes and `--timeframe-detail`, covering the timerange plus `startup_candle_count` candles before it. Commands: freqtrade-setup (`download-data`, `list-data`).
2. Backtest (below). Always set `--timerange`, and `--cache none` after changing the strategy, imported modules or data.
3. Read the report top to bottom: trade count, exit reasons, then summary metrics. See references/results.md.
4. Sanity checks before believing it: enough trades, profit not concentrated in a few trades or one pair, exit reasons make sense, result compared with `Market change`, drawdown acceptable.
5. Dig deeper with `backtesting-analysis` (needs `--export signals`) and `backtesting-show`. See references/analysis.md.
6. Stress the result: `--timeframe-detail`, `--enable-protections`, different timeranges, a higher `--fee`. See references/assumptions.md.
7. Plot if useful (needs extra dependencies, see "Plotting").
8. Hand off to freqtrade-validation before any dry run. Hyperopt results only count after validation passes.

## Run a backtest

```bash
freqtrade backtesting --strategy MyStrategy --timerange 20260801-20261001 --cache none
```

Common options (all verified against `freqtrade backtesting --help` on 2026.10 by the repo's CLI checker):

| Goal | Option |
|------|--------|
| Limit dates (UTC; `yyyymmdd`, `yyyymmddThhmm`, epoch) | `--timerange 20260801-20261001`, `20260801-`, `-20261001` |
| Override timeframe | `-i 1h` (data for it must exist) |
| Simulate intra-candle moves with smaller candles | `--timeframe-detail 5m` (must be smaller than the timeframe) |
| Monthly or other breakdown | `--breakdown month` (`day`, `week`, `month`, `year`, `weekday`; several allowed) |
| Keep signal candles for tag analysis | `--export signals` (also exports trades); default is `--export trades`; `--export none` skips files |
| Force a fresh run | `--cache none` (default reuses results up to a day old when strategy and config match) |
| Include configured protections | `--enable-protections` (slower) |
| Compare strategies | `--strategy-list A B` (one timeframe per run, same folder) |
| Limit pairs, slots, stake, wallet, fee | `-p BTC/USDT ETH/USDT`, `--max-open-trades 3`, `--stake-amount 100`, `--dry-run-wallet 1000`, `--fee 0.001` |
| Other data or strategy folder | `-d PATH`, `--strategy-path PATH`, `--userdir PATH`, `-c config.json` |
| Notes saved with the result | `--notes "text"` |

`--fee` is a ratio applied on entry and exit; without it Freqtrade uses the exchange default fee. `--eps` (position stacking) highlights hidden signals but its results cannot be reproduced in dry or live trading, so do not use it for performance claims. Output file names: the result is a `.zip` (plus a `.meta.json`) in `<userdir>/backtest_results/`. More on options and files: references/commands.md.

Example with the options this skill relies on:

```bash
freqtrade backtesting --strategy IndicatorsExample --timerange 20260801-20261001 --breakdown month --export signals --cache none
```

Compare two strategies on the same data:

```bash
freqtrade backtesting --strategy-list IndicatorsExample ValidationExample --timerange 20260801-20261001 --export none --cache none
```

## Read the result

The report prints, in order: backtesting report per pair (with TOTAL), left open trades, enter tag stats, exit reason stats, mixed tag stats, optional breakdowns, summary metrics, and a strategy summary. Real output (trimmed; IndicatorsExample, test data, labeled as a teaching example):

```text
                                             EXIT REASON STATS
┃ Exit Reason ┃ Exits ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃
│         roi │    29 │         1.01 │          29.305 │         2.93 │      3:12:00 │   29     0     0   100 │
│  force_exit │     2 │        -0.13 │          -0.266 │        -0.03 │      6:45:00 │    0     0     2     0 │
│    rsi_high │   169 │        -0.08 │         -13.228 │        -1.32 │      9:17:00 │  100     0    69  59.2 │
│       TOTAL │   200 │         0.08 │          15.811 │         1.58 │      8:23:00 │  129     0    71  64.5 │
                                 MONTH BREAKDOWN
┃      Month ┃ Trades ┃ Tot Profit USDT ┃ Profit Factor ┃  Win  Draw  Loss  Win% ┃
│ 31/08/2026 │    106 │          10.571 │          1.44 │   67     0    39  63.2 │
│ 30/09/2026 │     94 │            5.24 │          1.18 │   62     0    32  66.0 │
│ Total/Daily Avg Trades                 │ 200 / 3.33                                │
│ Total profit %                         │ 1.58%                                     │
│ Mean profit p-value                    │ 0.1838                                    │
│ Market change                          │ 38.43%                                    │
│ Max % of account underwater            │ 0.96%                                     │
```

What to take from it: the exit reasons show the whole profit comes from `roi` exits (29 trades) while the 169 `rsi_high` exits lose money in total, so the exit signal is the weak part. The p-value of 0.1838 is above the docs' rule-of-thumb bar of 0.05, so the average trade profit is not distinguishable from noise. The market rose 38.43% in the same period while the strategy made 1.58%.

Key metrics (full list with docs definitions: references/results.md):

| Metric | Meaning (docs) | Caution |
|--------|----------------|---------|
| `Total profit %` | (end capital - start capital) / start capital | Depends on `max_open_trades`, stake and wallet. |
| `Max % of account underwater` | Largest fall from a balance peak | Based on closed trades; the wallet-based block includes open trades. |
| `Profit factor` | Sum of winning profits / sum of losses | Above 1 means wins outweigh losses in this sample only. |
| `Mean profit p-value` | Two-sided t-test of mean trade return vs zero | Docs: below 0.05 is the usual bar; the test assumes independent trades, so it is optimistic; many tested strategies will score low by chance. |
| `Market change` | Average change of all pairs, first to last candle | Compare with profit: beating a rising market needs more than profit. |
| `Rejected Entry signals` | Signals skipped because `max_open_trades` was full | Not the same as `confirm_trade_entry` rejections. |
| `Sharpe / Sortino / Calmar` | Annualized, closed trades or wallet-based | Short timeranges make them unstable. |

The docs' FAQ says 12 trades are "not enough to say anything". Treat small trade counts, one lucky month or one dominant pair as weak evidence. The docs give no minimum number; do not invent one.

## Assumptions that limit trust

Backtesting does not know what happened inside a candle. The docs list these assumptions (full list: references/assumptions.md):

- Entries fill at the open price unless custom pricing is used; exit signals fill at the next candle's open; all orders fill at the requested price if it is inside the candle's high/low (no slippage).
- Within one candle: exit signal first, then stoploss, then ROI, then trailing stoploss. Stoploss is evaluated before ROI, so more `stop_loss` exits than in dry-run are normal. Low is assumed before high for stoploss.
- ROI exits use the ROI value even if high was higher; stoploss exits happen exactly at the stoploss price (plus `2 * fees` loss).
- Exchange trading limits and precision come from today's market data, not history.
- Dynamic pairlists reflect today's market, so results are not reproducible; use a static list from `test-pairlist`.
- `--timeframe-detail` reduces the intra-candle guesswork; the docs suggest it as a last development step. Callbacks then run once per detail candle.

## Analysis, show, plot

```bash
freqtrade backtesting --strategy IndicatorsExample --timerange 20260801-20261001 --export signals --cache none
freqtrade backtesting-analysis --analysis-groups 0 1 2 5 --indicator-list rsi bb_lowerband
freqtrade backtesting-show --breakdown weekday
```

- `backtesting-analysis` reads the latest result in the userdir. Groups: 0 win/loss by enter_tag, 1 by enter_tag, 2 by enter_tag and exit_tag, 3 by pair and enter_tag, 4 by pair, enter_tag and exit_tag, 5 by exit_tag. `--indicator-list` prints indicator values at entry and exit; names must be columns in the strategy dataframe. See references/analysis.md.
- `backtesting-show` re-displays a saved result (`--breakdown`, `--show-pair-list`, `--show-params`).
- Real output of group 2 on the example (trimmed): `rsi_bb_low` with `rsi_high` exit: 143 trades, `profit_abs_sum` -11.926; with `roi` exit: 27 trades, +27.304.

### Plotting

`plot-dataframe` and `plot-profit` need Plotly, which the standard images do not contain. Verified on 2026.10: `freqtradeorg/freqtrade:2026.10` and `2026.10_freqai` fail with `ModuleNotFoundError: No module named 'plotly'`; `freqtradeorg/freqtrade:2026.10_plot` exists and generated both HTML plots into `<userdir>/plot/`. Native installs: `pip install -U -r requirements-plot.txt`. The docs mark both commands deprecated (maintenance mode) and recommend FreqUI. Details and `plot_config`: references/plotting.md.

```bash
freqtrade plot-dataframe --strategy IndicatorsExample -p BTC/USDT --timerange 20260801-20260805 --indicators1 ema_fast ema_slow --indicators2 rsi
freqtrade plot-profit --strategy IndicatorsExample
```

## Validation gate

Before reporting the strategy as done:

1. The backtest runs without errors and produces trades; exit reasons and tags were looked at.
2. `lookahead-analysis` reports no bias. The only blanket exception is FreqAI `set_freqai_targets()` columns. Pairlist-dependent logic and limit orders with `custom_entry_price()` or `custom_exit_price()` can also give documented false positives; each must be explained to the user, never silently ignored.
3. `recursive-analysis` shows near-zero variance at the declared `startup_candle_count` (the project checks use at most 0.5%; this is a repo choice, the docs give no number); otherwise raise `startup_candle_count`.
4. Only after 1 to 3, suggest a dry run. Live trading is the user's separate, explicit decision.

Details and fixes: freqtrade-validation.

## References

- references/commands.md - backtesting options, timerange formats, result files, cache, multiple strategies, docs inconsistencies
- references/results.md - every report table and summary metric with its docs definition
- references/assumptions.md - backtesting assumptions, trading limits, `--timeframe-detail`
- references/analysis.md - `backtesting-analysis` groups and options, `backtesting-show`, notebooks
- references/plotting.md - `plot-dataframe`, `plot-profit`, `plot_config`, plot image

## Related skills

freqtrade-setup (download data), freqtrade-config (fees, pairlists, protections), freqtrade-strategy (signals, ROI, stoploss), freqtrade-callbacks (callbacks and their backtest behavior), freqtrade-validation (lookahead, recursive, fix catalog, hyperopt gating).

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
