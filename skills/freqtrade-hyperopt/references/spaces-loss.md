Source: docs/hyperopt.md#running-hyperopt-with-smaller-search-space
Source: docs/hyperopt.md#loss-functions
Source: docs/hyperopt.md#execute-hyperopt
Source: docs/hyperopt.md#default-roi-search-space
Source: docs/hyperopt.md#default-stoploss-search-space
Source: docs/hyperopt.md#default-trailing-stop-search-space
Source: docs/hyperopt.md#reproducible-results
Source: docs/hyperopt.md#position-stacking-and-disabling-max-market-positions
Source: docs/hyperopt.md#out-of-memory-errors
Source: docs/advanced-hyperopt.md#overriding-pre-defined-spaces
Source: docs/commands/hyperopt.md
Source: docs/commands/list-hyperoptloss.md

# Spaces, loss functions, command options

## Spaces (`--spaces`, docs)

| Space | Optimizes |
|-------|-----------|
| `buy` / `enter` | parameters assigned to that space (entry logic) |
| `sell` / `exit` | parameters assigned to that space (exit logic) |
| `roi` | the `minimal_roi` table (built in, no strategy change needed) |
| `stoploss` | the `stoploss` value (built in) |
| `trailing` | trailing stop values (built in) |
| `trades` | `max_open_trades` (built in) |
| `protection` | protection parameters (needs a `protections` property, see parameters.md) |
| `default` | `all` except `trailing`, `trades` and `protection` (used when `--spaces` is absent) |
| `all` | everything, including custom spaces |
| `custom_space_name` | any custom space used by a parameter in the strategy |

Several values are space-separated: `--spaces roi stoploss`. Docs recommend running `trailing` separately, after the other spaces' best parameters are "found, validated and pasted into your custom strategy". Docs flag the `exit` line as "just search for a new entry logic": that is a copy-paste typo in the docs, it means exit logic.

Docs tip: `roi`, `stoploss` and `trailing` need no strategy changes:

```bash
freqtrade hyperopt --hyperopt-loss SharpeHyperOptLossDaily --spaces roi stoploss trailing --strategy MyWorkingStrategy --config config.json -e 100
```

Smaller spaces search faster and overfit less (repo advice): start with `buy`/`sell` or `roi stoploss`, not `all`.

### Default built-in ranges (docs)

- ROI: 4 rows (steps); minutes scale linearly with the timeframe, values scale logarithmically. 5m: step 1 at minute 0 value 0.03..0.31; step 2 at 10..40 min value 0.02..0.11; step 3 at 20..100 min value 0.01..0.04; step 4 at 30..220 min value 0.0.
- Stoploss: -0.35 .. -0.02.
- Trailing: `trailing_stop` always True in the space; `trailing_only_offset_is_reached` True or False; `trailing_stop_positive` 0.02..0.35; `trailing_stop_positive_offset` 0.01..0.1.
- Decimals in these built-in spaces are limited to 3 places. Docs: finer precision "will usually result in overfitted results".
- Override with a nested `class HyperOpt:` (`roi_space`, `generate_roi_table`, `stoploss_space`, `trailing_space`, `max_open_trades_space`; all optional). Example in docs/advanced-hyperopt.md#overriding-pre-defined-spaces (untested here). Space types come from `freqtrade.optimize.space`: `Categorical`, `Integer`, `Real`, `SKDecimal` (docs: prefer `SKDecimal` to `Real`).
- Sampler: default `NSGAIIISampler`. Docs allow `generate_estimator()` in the nested `HyperOpt` class to return another optuna sampler name; docs say if unsure keep the default.

## Loss functions (`--hyperopt-loss NAME`, or `"hyperopt_loss"` in config)

A loss function returns a number; smaller is better. Docs descriptions of the built-ins:

| Name | Optimizes (docs) |
|------|------------------|
| `ShortTradeDurHyperOptLoss` | "default legacy" loss: short trade duration, avoid losses |
| `OnlyProfitHyperOptLoss` | profit only |
| `SharpeHyperOptLoss` | Sharpe ratio on trade returns |
| `SharpeHyperOptLossDaily` | Sharpe ratio on daily returns |
| `SortinoHyperOptLoss` | Sortino ratio on trade returns (downside deviation) |
| `SortinoHyperOptLossDaily` | Sortino ratio on daily returns |
| `MaxDrawDownHyperOptLoss` | maximum absolute drawdown |
| `MaxDrawDownRelativeHyperOptLoss` | absolute drawdown, also adjusting for relative drawdown |
| `MaxDrawDownPerPairHyperOptLoss` | worst per-pair profit/drawdown ratio, so no pair is ignored |
| `CalmarHyperOptLoss` | Calmar ratio (trade returns vs max drawdown) |
| `ProfitDrawDownHyperOptLoss` | max profit and min drawdown; `DRAWDOWN_MULT` in the loss file adjusts strictness |
| `MultiMetricHyperOptLoss` | profit and drawdown, plus profit factor, expectancy ratio, win rate; penalizes epochs with few trades |

Observed (`list-hyperoptloss` in the 2026.10 image, test userdir) 14 names: the 12 above plus `DefaultHyperOptLoss` (loaded from `hyperopt_loss_short_trade_dur.py`, not in the docs' list) and `SampleHyperOptLoss` (the template file `sample_hyperopt_loss.py` created by `create-userdir` in the user dir). Check your own install:

```bash
freqtrade list-hyperoptloss
freqtrade list-hyperoptloss -1
```

Docs: failed loads print red (LOAD FAILED) and duplicate names yellow (DUPLICATE NAME). Custom loss classes: custom-loss.md. Which loss to pick is not specified by the docs; Sharpe/Sortino/Calmar/drawdown losses look at risk, `OnlyProfitHyperOptLoss` does not (repo observation, not a docs claim).

The tested run used `SharpeHyperOptLossDaily`. With 5 epochs and a loss-making strategy the "best" epoch (lowest objective) was the one with only 33 trades and total profit -0.16%, against 151 to 217 trades and -0.8% to -2.8% for the others (observed, test data): a loss function can rank a barely-trading epoch first.

## Command options (2026.10 help)

```bash
freqtrade hyperopt --strategy MyStrategy --hyperopt-loss SharpeHyperOptLossDaily --spaces buy sell -e 100 --timerange 20260101-20260601 --random-state 42 --min-trades 30 --early-stop 25 -j -2
```

- `-e, --epochs INT`: default 100. Docs: best results usually stop improving after 500 to 1000 epochs; "doing multiple runs with a few 1000 epochs and different random state will most likely produce different results".
- `--early-stop INT`: stop after that many epochs without improvement (default 0 = off). Docs: a good value is 20-30% of the epochs; a value above 0 and below 20 is replaced by 20.
- `--timerange`: limit the data used (see results-overfitting.md for the train/test split).
- `--min-trades INT`: minimal desired number of trades for evaluations (default 1). Observed: with `--min-trades 100` on two weeks of test data all 3 epochs were rejected, hyperopt printed "No good result found for given optimization function in 3 epochs." and the exit code was still 0.
- `-j, --job-workers`: -1 (default) all CPUs, -2 all but one, 1 means no parallel code. Docs carry a note "Hyperopt can crash when used with only 1 CPU Core" (issue #1133, an old report) while the help describes `-j 1` as supported; `-j 1` worked in the repo test (5 epochs, 2026.10). Docs: `print()` output shows only with `-j 1`.
- `--random-state INT`: reproducibility. The first 30 epochs (docs: "currently 30") are random and marked `*`; with unchanged options, data, strategy and loss the same random state gives the same results. Observed: two identical runs with `--random-state 42` produced the same 5 epochs, objectives and parameters. With fewer than 30 epochs the whole run is random exploration, not optimization.
- `--analyze-per-epoch`, `--disable-param-export`, `--ignore-missing-spaces`: see parameters.md and results-overfitting.md.
- `--print-all`, `--print-json`, `--no-color`: output formatting.
- `--eps`: position stacking (buy the same pair many times). Help: results "cannot be reproduced in dry/live trading". Docs: validate without it.
- `--enable-protections`: help text "Enable protections for backtesting"; docs: selecting the `protection` space enables them. Docs: protections enabled in backtesting must also be enabled when hyperopting, and vice versa.
- `--timeframe-detail`: loads a lot more data into memory (docs: avoid it when out of memory).
- `--max-open-trades`, `--stake-amount`, `--fee`, `--dry-run-wallet`, `-p/--pairs`, `-i/--timeframe`, `--hyperopt-path`: as in backtesting.

Docs: run long jobs in `screen` or `tmux`. Out of memory (data is held once per worker): fewer pairs, shorter `--timerange`, no `--timeframe-detail`, fewer `-j`, `--analyze-per-epoch` when many `.range` columns.

## Running it in this repo (tests)

In the freqtrade-skills repository (/tests): `tests/run_hyperopt.sh <Strategy> [--epochs N] [--spaces "buy sell"] [--loss NAME] [--timerange R]` copies the strategy to `tests/out/hyperopt/strategies/`, runs `hyperopt -j 1 --random-state 42` there (defaults: 5 epochs, `buy sell`, `SharpeHyperOptLossDaily`, timerange 20260801-20260915), then `hyperopt-list` and `hyperopt-show`. The params JSON lands in the temp copy only (gitignored), never in [`tests/strategies/`](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/). These test runs are smoke tests of the commands on test data, not a recommended setup.
