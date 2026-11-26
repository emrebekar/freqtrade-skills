---
name: freqtrade-hyperopt
description: Use when you need to tune a Freqtrade strategy's parameters with hyperopt, read or apply hyperopt results, write a custom hyperopt loss function, or judge whether optimized parameters are overfitted. Covers IntParameter, DecimalParameter, RealParameter, CategoricalParameter, BooleanParameter (space, optimize, load), spaces (buy, sell, roi, stoploss, trailing, protection, trades), built-in loss functions, freqtrade hyperopt options (--spaces, --epochs, --hyperopt-loss, --timerange, --min-trades, --analyze-per-epoch, --random-state), hyperopt-list, hyperopt-show, the params JSON file and its precedence over strategy and config, custom IHyperOptLoss, and out-of-sample overfitting checks.
license: GPL-3.0
---

# Freqtrade hyperopt

Hyperopt runs the backtester many times with different parameter values and keeps the combination that minimizes a loss function. Pinned Freqtrade release: 2026.10. It needs the same historical data as backtesting. Users trade real money: hyperopt is the step where overfitting happens, so say plainly what its output does and does not prove. The example `HyperoptExample` ([tests/strategies/](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/)) and the custom loss ([tests/hyperopt_losses/](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/hyperopt_losses/)) were run on the repo's test data (BTC/USDT and ETH/USDT, 5m, 2026-08-01 to 2026-10-01). They are teaching examples, not profitable strategies; never present their numbers as a result.

Rules:
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives. That is the only blanket exception: pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives; explain each, never silently ignore. A pass does not prove the strategy is clean (see freqtrade-validation).
- Optimized parameters count only after the optimized strategy (the file plus the parameters actually loaded) passes freqtrade-validation. Validate the strategy before hyperopt too: hyperopt on a biased strategy optimizes the bias.
- A best epoch is a candidate, not a result. Never present in-sample numbers as expected performance, and never report "hyperopt found a profitable strategy" from the optimization range alone.
- Keep `dry_run: true`. Live trading is the user's separate, explicit decision.
- Hyperopt results depend on the config: `stoploss`, `max_open_trades`, `trailing_stop` and ROI set in the config override what hyperopt wrote. Never apply or commit a params JSON file the user did not ask for.
- Docs say hyperopt "will burn all your CPU cores"; run long jobs in `screen` or `tmux`, and tell the user the expected cost before starting 500+ epochs.

## Workflow

1. The strategy loads, data covers the range plus `startup_candle_count`, a plain backtest trades, and `lookahead-analysis` and `recursive-analysis` pass (freqtrade-setup, freqtrade-backtesting, freqtrade-validation).
2. Decide what to optimize and keep it small: few parameters, small ranges, one or two spaces (`buy sell`, or `roi stoploss`). Define parameters at class level and read them with `self.<name>.value` in `populate_entry_trend()` / `populate_exit_trend()` (references/parameters.md).
3. Split the data in time (see Overfitting): choose an optimization `--timerange` and keep a later range unseen.
4. Run hyperopt (below) with a fixed `--random-state`. Fewer than 30 epochs is only random exploration (docs); a real search is hundreds of epochs.
5. Read the result: `hyperopt-list`, `hyperopt-show` (references/results-overfitting.md). Reject epochs with few trades.
6. Apply parameters (JSON file or class-level blocks), check which values the backtest log shows, and backtest the unseen range, comparing against the unoptimized defaults.
7. Re-run `lookahead-analysis` and `recursive-analysis` on the optimized strategy (raise `startup_candle_count` if a searched period grew).
8. Only then trust the numbers, and only then suggest a dry run.

## Run

```bash
freqtrade hyperopt --strategy MyStrategy --hyperopt-loss SharpeHyperOptLossDaily --spaces buy sell -e 200 --timerange 20260801-20260915 --random-state 42 --min-trades 30
freqtrade hyperopt-list --best --no-details
freqtrade hyperopt-show --best -n -1
```

- `--hyperopt-loss NAME` (or `"hyperopt_loss"` in the config) is required: pick from `freqtrade list-hyperoptloss`.
- `--spaces`: `buy sell enter exit roi stoploss trailing trades protection all default` or a custom space name. Default is `default` (everything except `trailing`, `trades`, `protection`).
- `--timerange` limits the data. `-e` epochs (default 100). `--early-stop N` stops after N epochs without improvement. `-j` workers (`-1` all CPUs, `1` no parallelism). `--random-state` for reproducible runs.
- `--min-trades N`: epochs with fewer trades are not accepted; if none qualify the run ends with "No good result found" and exit code 0 (observed).
- `--analyze-per-epoch`: run `populate_indicators()` every epoch (less RAM, more CPU), needed when a parameter is used inside indicators.
- `--disable-param-export`: do not write the params JSON file.
- Results go to `<userdir>/hyperopt_results/*.fthypt`; `hyperopt-list` and `hyperopt-show` read the latest, or `--hyperopt-filename NAME`.

In the freqtrade-skills repository (/tests): `tests/run_hyperopt.sh HyperoptExample` runs a 5-epoch smoke test on a temp copy under tests/out/hyperopt/ (never writes into [tests/strategies/](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/)), then `hyperopt-list` and `hyperopt-show`.

## Parameters at a glance

| Type | For | Note |
|------|-----|------|
| `IntParameter(low, high, default=, space=)` | whole numbers | |
| `DecimalParameter(low, high, decimals=3, default=, space=)` | floats | preferred over `RealParameter` |
| `RealParameter(low, high, default=, space=)` | floats, full precision | huge space, rarely useful, no `.range` |
| `CategoricalParameter([..], default=, space=)` | a choice | |
| `BooleanParameter(default=, space=)` | on/off switch | `CategoricalParameter([True, False])` |

Options on all: `space`, `optimize=False` (not searched), `load=False` (ignore earlier results, use the default; backtesting then uses the default too). The space comes from the name prefix (`buy_`, `sell_`, `enter_`, `exit_`, `protection_`) or from `space=`; a parameter with neither is silently ignored. Do not use `.value` of a searched parameter inside `populate_indicators()` (computed once for all epochs): use `.range`, `--analyze-per-epoch`, or compute in the signal methods. Details and the tested code: references/parameters.md.

## Which values win: precedence

Docs: config > parameter file (`MyStrategy.json` next to the strategy) > strategy `*_params` > parameter default. Observed on the pinned release: JSON beat strategy `buy_params`, and a config `stoploss` beat the JSON. A leftover JSON file silently changes backtests: read the `Strategy Parameter: ...` log lines. Details: references/results-overfitting.md.

## Overfitting (read this before showing results)

- Hyperopt optimizes the loss on the data it sees. More parameters, wider ranges, more epochs and a looser `--min-trades` mean more fitting of noise.
- Optimize on one timerange, then backtest a later range hyperopt never saw. Do not hyperopt on a range and call a backtest of the same range a confirmation (repo advice; the docs describe no split).
- Few trades mean nothing: in the test run an out-of-sample result of 11 trades (+0.30%, 9 wins) says nothing either way, and the "best" epoch by loss was the one with only 33 trades.
- The best objective is not a profitable strategy: with 5 epochs on test data every epoch lost money.
- Run with several `--random-state` values; if the best parameters differ a lot, the optimum is not stable (docs: runs with different states "will most likely produce different results").
- Small steps: low `decimals`, narrow ranges, one space at a time (docs recommend `trailing` last, separately).
- Report in-sample and out-of-sample numbers side by side, with trade counts, and say what was not tested.

Docs advice versus repo advice is labeled in references/results-overfitting.md.

## Validation gate

Before reporting optimized parameters as usable, show the user:

1. The command, `--timerange`, loss, epochs, `--random-state`, `--min-trades`, and the chosen epoch's trade count.
2. A backtest on a timerange hyperopt did not use, with trade count, next to the unoptimized defaults.
3. `lookahead-analysis`: `has_bias` No on the optimized strategy (the only blanket exception is FreqAI `set_freqai_targets()` columns; pairlist-dependent logic and limit orders with `custom_*_price` can also give documented false positives, each explained, never silently ignored).
4. `recursive-analysis`: low variance at the declared `startup_candle_count` (the repo checks use at most 0.5%; a repo choice, not a Freqtrade rule).
5. The honest limits: the optimization range was fitted; few trades prove nothing; backtests assume perfect fills (freqtrade-backtesting).

Only then suggest a dry run. Live trading is the user's separate, explicit decision.

## References

- references/parameters.md - parameter types and options, space assignment, `.range`, protections, tested code
- references/spaces-loss.md - spaces, default ranges, built-in loss functions, command options, observed behavior
- references/results-overfitting.md - reading results, params JSON, precedence, hyperopt-list/show, train/test split, gate
- references/custom-loss.md - `IHyperOptLoss` signature (verbatim), arguments, tested custom loss

## Related skills

freqtrade-validation (the gate, lookahead and recursive checks), freqtrade-backtesting (read and compare backtests), freqtrade-strategy (signals, ROI, stoploss), freqtrade-config (config overrides, protections), freqtrade-setup (download data).

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
