Source: docs/hyperopt.md#understand-the-hyperopt-result
Source: docs/hyperopt.md#automatic-parameter-application-to-the-strategy
Source: docs/hyperopt.md#understand-hyperopt-roi-results
Source: docs/hyperopt.md#understand-hyperopt-stoploss-results
Source: docs/hyperopt.md#understand-hyperopt-trailing-stop-results
Source: docs/hyperopt.md#validate-backtesting-results
Source: docs/hyperopt.md#why-do-my-backtest-results-not-match-my-hyperopt-results
Source: docs/hyperopt.md#show-details-of-hyperopt-results
Source: docs/utils.md#list-hyperopt-results
Source: docs/utils.md#show-details-of-hyperopt-results
Source: docs/commands/hyperopt-list.md
Source: docs/commands/hyperopt-show.md

# Reading results, applying parameters, avoiding overfitting

## Reading the result (docs)

Hyperopt prints the best epoch: epoch number, trades, average profit, total profit, average duration and the objective (loss) value, then parameter blocks:

```text
Best result:

*    3/5:     33 trades. 14/0/19 Wins/Draws/Losses. Avg profit  -0.05%. Median profit  -0.11%. Total profit -1.61928713 USDT (  -0.16%). Avg duration 4:14:00 min. Objective: 2.86843

    # Buy parameters:
    buy_params = {
        "buy_rsi": 20,
        "buy_rsi_enabled": True,
        "buy_zscore": -2.1,
    }
```

(Real output, tests/run_hyperopt.sh, 5 epochs on test data, trimmed.) `buy_rsi_enabled: False` means that guard should not be used (docs). Docs: "consider" using the values, they are a result of one search, not a truth. ROI results print a `minimal_roi = {...}` table, stoploss `stoploss = ...`, trailing the four `trailing_*` values. Values marked `# value loaded from strategy` were not searched.

## Where the optimized values live (docs + observed)

After a run hyperopt writes a JSON file next to the strategy: `MyAwesomeStrategy.json` beside `MyAwesomeStrategy.py`. Log line observed: `Dumping parameters to .../HyperoptExample.json`. Docs: the file is also updated by `hyperopt-show` unless `--disable-param-export` is given to either command. (Observed once: running `hyperopt-show` as in the test script left the file untouched: the `export_time` stayed that of the hyperopt run.) Contents (observed, trimmed):

```json
{
  "strategy_name": "HyperoptExample",
  "params": {
    "stoploss": {"stoploss": -0.1},
    "sell": {"sell_rsi": 60, "sell_zscore": 0.8},
    "buy": {"buy_rsi": 20, "buy_rsi_enabled": true, "buy_zscore": -2.1}
  },
  "ft_stratparam_v": 1
}
```

You can also paste the printed blocks (`buy_params = {...}`, `sell_params`, `minimal_roi`, `stoploss`, `trailing_*`) at class level in the strategy. Docs precedence:

> config > parameter file > strategy `*_params` > parameter default

Observed in a backtest on the 2026.10 image (temp copy, not committed): strategy `buy_params = {"buy_rsi": 30}` with a JSON file holding `buy_rsi: 20` loaded `buy_rsi = 20` (file beats strategy `*_params`); a JSON `stoploss: -0.2` was used ("Strategy using stoploss: -0.2") until the config set `"stoploss": -0.05`, which then won ("Override strategy 'stoploss' with value from the configuration: -0.05"). A parameter with no value anywhere logged `Strategy Parameter(default)`.

Consequences:
- A forgotten JSON file silently overrides the values in your strategy. Docs: "Verify that you do not have an unexpected parameters JSON file overriding the parameters". Check the backtest log lines `Strategy Parameter: ...` for what was actually used.
- `stoploss`, `max_open_trades`, `trailing_stop`, ROI in the config override hyperopt results (docs).
- Repo rule: params JSON files are run output. This repo never commits them (tests run hyperopt on a temp copy). In a user project, commit one only deliberately, after validation, and say so.

## hyperopt-list and hyperopt-show (docs + observed)

Both read the latest results file in `<userdir>/hyperopt_results/` (`.fthypt`); `--hyperopt-filename FILENAME` selects an older one (name only, no path).

```bash
freqtrade hyperopt-list --best --no-details
freqtrade hyperopt-list --profitable --min-trades 30 --export-csv hyperopt.csv
freqtrade hyperopt-show -n 168
freqtrade hyperopt-show --best -n -1 --print-json --no-header
```

- `hyperopt-list` filters: `--best`, `--profitable`, `--min-trades`/`--max-trades`, `--min-avg-time`/`--max-avg-time`, `--min-avg-profit`/`--max-avg-profit`, `--min-total-profit`/`--max-total-profit`, `--min-objective`/`--max-objective`; `--print-json`, `--no-details`, `--export-csv FILE` (disables the table).
- `hyperopt-show`: `-n/--index INT`, `--best`, `--profitable`, `--print-json`, `--no-header`, `--disable-param-export`, `--breakdown {day,week,month,year,weekday}`. It has no `--strategy` option (observed: `-s` is rejected as an unrecognized argument).
- The `-n` index applies to the filtered list: observed `--best -n 1` showed the first best epoch (1/5), not the lowest objective (3/5). The docs example `--best -n -1` shows the last best epoch, "the best of all epochs"; observed to show epoch 3/5.
- Observed `hyperopt-list` table (columns Best, Epoch, Trades, Win/Draw/Loss/Win%, Avg profit, Profit, Avg duration, Objective, Max Drawdown):

```text
│ * Best │   1/5 │    151 │   65     0    86  43.0 │     -0.14% │ -20.784 USDT   (-2.08%) │      3:57:00 │   9.00004 │
│ * Best │   2/5 │    205 │  109     0    96  53.2 │     -0.04% │  -7.918 USDT   (-0.79%) │      5:36:00 │   4.14694 │
│ * Best │   3/5 │     33 │   14     0    19  42.4 │     -0.05% │  -1.619 USDT   (-0.16%) │      4:14:00 │   2.86843 │
```

- Observed: freqtrade returned exit code 0 on an argument error (`hyperopt-show -s X`: "unrecognized arguments"), so scripts must also read the output. `tests/run_hyperopt.sh` does.
- `hyperopt-show` prints a normal backtest report for that epoch, useful to see per-pair trades.

## Validate the optimized strategy (docs)

Backtest the optimized strategy with the same configuration and timerange as hyperopt: trades, durations and profit should match. Observed: the optimized copy backtested on 20260801-20260915 gave 33 trades and -1.619 USDT, identical to epoch 3/5.

If they do not match (docs): parameters in `populate_indicators()` (computed once for all epochs); params not transferred after `--disable-param-export`; a config `stoploss`/`max_open_trades`/`trailing_stop` overriding; an unexpected params JSON file; protections enabled in one run and not the other.

## Overfitting (honest limits)

Hyperopt picks the parameters that fit one stretch of history best. The more parameters, epochs and degrees of freedom, the more it fits noise. The docs say so in places: decimals limited to 3 places because finer values "will usually result in overfitted results"; multiple runs with different random states "will most likely produce different results"; best results usually do not improve after 500-1000 epochs. Their remedies are limited, so the rest here is labeled.

| Advice | Origin |
|--------|--------|
| Fewer parameters, smaller ranges, smaller spaces (`buy`/`sell` or `roi stoploss` before `all`); keep `decimals` low | docs (3 decimals, "as small as possible") and repo choice |
| Treat the printed best epoch as one candidate; run again with other `--random-state` values and compare | docs (different states give different results) + repo choice |
| Fewer than 30 epochs is all random exploration | docs (first 30 epochs are random) |
| Few trades prove nothing: set `--min-trades` to a number that makes sense for your timeframe and range, and distrust any epoch near it | repo advice; `--min-trades` is docs; no number given by the docs |
| Split the timerange: optimize on the first part, test on a later part never shown to hyperopt | repo advice (docs do not describe a split) |
| Never hyperopt on a range and then call a backtest of the same range a confirmation | repo advice |
| Re-run `lookahead-analysis` and `recursive-analysis` on the optimized strategy | repo gate, see freqtrade-validation |
| Prefer losses that account for risk and trade count (`MultiMetricHyperOptLoss` penalizes few trades per docs) over pure profit | repo advice |
| A good in-sample number is a fitted number | repo advice |

### Train/test split in practice (repo workflow, observed on test data)

```bash
freqtrade hyperopt --strategy MyStrategy --hyperopt-loss SharpeHyperOptLossDaily --spaces buy sell -e 200 --timerange 20260801-20260915 --random-state 42
freqtrade backtesting --strategy MyStrategy --timerange 20260915-20261001
```

Test data run (HyperoptExample, 5 epochs, so a smoke test, not a method): the optimized values gave 33 trades and -0.16% in the optimization range, and 11 trades, +0.30%, 9 wins of 11 in the later range. Eleven trades are far too few to conclude anything, in either direction; a good-looking out-of-sample line from so few trades is luck until proven otherwise. The honest reading needs many trades in both parts, several market conditions, and a comparison against the unoptimized defaults on the same later range.

Better still (repo advice, untested here): several consecutive windows, and a final dry-run before any real money. The docs say nothing about walk-forward testing. A split reduces overfitting risk; it does not remove it, and the test part is "used up" once you adjust the strategy based on it.

## Gate before the numbers count

Optimized parameters count only after the optimized strategy (strategy file plus the parameters actually loaded) passes freqtrade-validation: `lookahead-analysis` and `recursive-analysis`, re-run after the parameters are applied, on the same files you will backtest. Hyperopt can push a parameter into a region where an indicator is biased or recursive-unstable (for example a longer period needs a larger `startup_candle_count`). Raise `startup_candle_count` for the largest period in the search space, not for the default.

Observed: `tests/run_checks.sh HyperoptExample --strategy-path tests/out/hyperopt/strategies` (the optimized copy with its JSON): backtest OK, lookahead OK, recursive OK (startup 400, all indicators <= 0.5%).
