Source: docs/advanced-backtesting.md#analyze-the-buyentry-and-sellexit-tags
Source: docs/commands/backtesting-analysis.md
Source: docs/commands/backtesting-show.md
Source: docs/data-analysis.md#recommended-workflow

# backtesting-analysis and backtesting-show

`backtesting-analysis` is only available for backtesting, not hyperopt. It needs the result of a backtest run with `--export signals`:

```bash
freqtrade backtesting --strategy IndicatorsExample --timerange 20260801-20261001 --export signals --cache none
freqtrade backtesting-analysis --analysis-groups 0 1 2 3 4 5
```

Old results can be reused by the cache; delete them or use `--cache none` before exporting new signals. By default it reads the latest result in `<userdir>/backtest_results/`.

## Groups (`--analysis-groups`)

| Group | Content |
|-------|---------|
| 0 | overall win rate and profit by `enter_tag` (docs: simple wins/losses) |
| 1 | profit summaries by `enter_tag` |
| 2 | by `enter_tag` and `exit_tag` |
| 3 | by pair and `enter_tag` |
| 4 | by pair, `enter_tag` and `exit_tag` (can get large) |
| 5 | by `exit_tag` |

Real output on 2026.10 (IndicatorsExample, test data; trimmed to some columns):

```text
Group 2:
┃ enter_reason ┃ exit_reason ┃ num_buys ┃ profit_abs_sum ┃ mean_profit_pct ┃ total_profit_pct ┃
│   rsi_bb_low │    rsi_high │      143 │        -11.926 │          -0.083 │          -11.940 │
│    ema_cross │    rsi_high │       26 │         -1.302 │          -0.050 │           -1.297 │
│   rsi_bb_low │         roi │       27 │         27.304 │           1.012 │           27.336 │
```

## Options (from the 2026.10 help)

| Option | Meaning |
|--------|---------|
| `--backtest-filename PATH`, `--backtest-directory PATH` | Analyze an older result or another folder. |
| `--enter-reason-list a b`, `--exit-reason-list roi stop_loss` | Limit to tags/reasons (default all). |
| `--indicator-list rsi bb_lowerband` | Print these dataframe columns at entry and exit; `(entry)` and `(exit)` suffixes; unknown names are ignored; `all` prints entry only. |
| `--entry-only`, `--exit-only` | Show indicators for one side only (no suffixes). |
| `--timerange` | Filter output trades (start inclusive, end exclusive). |
| `--rejected-signals` | Print rejected signals. |
| `--analysis-to-csv`, `--analysis-csv-path PATH` | Write tables to CSV (`group_0.csv`, `rejected_signals.csv`, ...) instead of printing. |

Extra fields usable in `--indicator-list`: `open_date`, `close_date`, `min_rate`, `max_rate`, `open`, `close`, `high`, `low`, `volume`, `profit_ratio`, `profit_abs`; trade-wide fields have no suffix (`pair`, `stake_amount`, `open_rate`, `close_rate`, `trade_duration`, `exit_reason`, `enter_tag`, `leverage`, `is_short`, `orders`, and others listed in the docs).

Indicator values are those on the signal candle. Use them to tune entry conditions, but see freqtrade-validation: tuning on results of the same timerange overfits.

## backtesting-show

```bash
freqtrade backtesting-show --breakdown weekday
freqtrade backtesting-show --show-pair-list
freqtrade backtesting-show --show-params
```

Re-displays a stored result without re-running. `--show-pair-list` prints the pairlist sorted by profit (real output: `"BTC/USDT",  // 0.08%`), `--show-params` prints stored parameters, `--export-params` writes them to the strategy's parameter file, `--breakdown` takes day, week, month, year, weekday.

## Notebooks

The docs recommend CLI for operations, shell scripts for repeated tasks and Jupyter notebooks for visualization and analysis (`user_data/notebooks/` after `create-userdir`; Docker: `docker compose -f docker/docker-compose-jupyter.yml up`). Backtest results load into pandas; see docs `strategy_analysis_example.md` (not covered here).
