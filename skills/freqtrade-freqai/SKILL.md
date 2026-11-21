---
name: freqtrade-freqai
description: Use when you need to build, configure, train, backtest or debug a FreqAI (machine learning) Freqtrade strategy, pick a FreqAI model, or check an ML strategy for leakage. Covers the freqai config block (train_period_days, backtest_period_days, identifier, feature_parameters, data_split_parameters, model_training_parameters), feature_engineering_expand_all/expand_basic/standard, set_freqai_targets, the % and & prefixes, include_timeframes, include_corr_pairlist, include_shifted_candles, indicator_periods_candles, do_predict and DI_values, sliding-window retraining and --freqaimodel, model and prediction reuse by identifier, purge_old_models, outlier handling (DI, SVM, DBSCAN, PCA), list-freqaimodels, reinforcement learning, and look-ahead pitfalls specific to FreqAI.
license: GPL-3.0
---

# Freqtrade FreqAI

FreqAI trains a model on your features to predict targets (labels) you define, retrains it on a sliding window, and hands the predictions back to the strategy as dataframe columns. Freqtrade version assumed: 2026.10. Users trade real money and ML adds new ways to fool yourself: labels look into the future on purpose, a backtest hides retraining assumptions, and the usual look-ahead check cannot see most feature bugs. State plainly what a pass does not prove. The example `FreqaiExample` (tests/strategies/) was run on the repo's test data; it is a teaching example, not a profitable strategy, never present its numbers as a result (it lost money in the test range).

Rules:
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives (docs: "not biased and can safely be ignored"). That is the only blanket exception: pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives; explain each, never silently ignore. Read "Validation gate" below: both commands are much weaker on FreqAI strategies than on plain ones.
- Keep `dry_run: true`. Live trading is the user's separate, explicit decision.
- The `&` prefix on a target is not a free pass. Docs: `set_freqai_targets()` columns are false positives. Repo-observed on 2026.10 (a repo rule, not a docs rule): FreqAI's own outputs are flagged too, exact list `do_predict`, `DI_values`, `enter_long`, `enter_short`, `exit_long`, `exit_short`, `enter_tag`, `exit_tag` (only `do_predict`, `enter_long`, `exit_long`, `enter_tag`, `exit_tag` were observed; the rest are symmetric, unobserved), and they are acceptable only when at least one `&` column is also flagged and the biased entry/exit signal counts are 0. Any other flagged column, even one computed from predictions (for example the docs' `target_roi`), is a finding to explain.
- Features must not use future data. Backtesting computes `feature_engineering_*()` once over the whole training range (docs), so a feature with `shift(-n)` leaks. Only labels may look ahead.
- Same `identifier` means saved predictions are reused: after any change to features or labels use a new `identifier` (docs), or delete the models folder.
- Never load model files you did not train yourself (docs security notice: loading saved models can run untrusted code).
- FreqAI cannot be combined with a pairlist that adds or removes pairs dynamically (docs); `VolumePairList` only if the pair set stays constant.

## Workflow

1. Use an image or install with FreqAI dependencies (setup below), download data that covers the backtest range plus `train_period_days` plus `startup_candle_count` before it (freqtrade-setup).
2. Write the `freqai` config block (references/config.md) and a strategy with the required methods (references/feature-engineering.md).
3. Pick a model with `list-freqaimodels` (references/models.md); start small (one pair, few features, small model) and check training works before widening.
4. Backtest with `--freqaimodel` (references/running.md). Read the training log lines: windows, data points, NaN drops, features count.
5. Run `lookahead-analysis` and `recursive-analysis`, read the result with the FreqAI caveats below, and review by hand all `feature_engineering_*()` code, `populate_entry_trend()`, `populate_exit_trend()` and any code after `self.freqai.start()` against the leakage list.
6. Evaluate out of sample: a time range after the one you tuned on, with a fresh `identifier`, and report trade counts. Only then suggest a dry run.

## Setup

FreqAI needs extra Python packages. Docker image tag with them (docs name the `:freqai` tag; `2026.10_freqai` was pulled and used in this repo's tests): `freqtradeorg/freqtrade:2026.10_freqai` (LightGBM, XGBoost, scikit-learn). Docs: the torch tag (`stable_freqaitorch`) for PyTorch and the RL tag (`stable_freqairl`) for reinforcement learning (not pulled or run here). Native install: answer yes to the FreqAI question in `setup.sh`, or `pip install -r requirements-freqai.txt`. In the `_freqai` image the PyTorch and RL models log "Could not import ... No module named 'torch'" (observed) and are absent from `list-freqaimodels`.

```bash
freqtrade list-freqaimodels --one-column
freqtrade backtesting --strategy MyFreqaiStrategy --config config.json --freqaimodel LightGBMRegressor --timerange 20260801-20261001
freqtrade lookahead-analysis --strategy MyFreqaiStrategy --config config.json --freqaimodel LightGBMRegressor --timerange 20260801-20261001
freqtrade recursive-analysis --strategy MyFreqaiStrategy --config config.json --freqaimodel LightGBMRegressor --timerange 20260801-20261001
```

`--freqaimodel NAME` is the class name of a built-in model or of a file in `user_data/freqaimodels/` (`--freqaimodel-path` adds a search path). Pass it to `lookahead-analysis` and `recursive-analysis` too (observed to work on 2026.10).

## Strategy skeleton

Required: `startup_candle_count`, `populate_indicators()` calling `self.freqai.start()`, at least one `feature_engineering_*()` that sets `%`-prefixed columns, and `set_freqai_targets()` that sets `&`-prefixed columns. The tested code is in references/feature-engineering.md; the shape:

```python
    startup_candle_count: int = 40  # largest indicator period, docs advise doubling it

    def feature_engineering_expand_all(self, dataframe, period, metadata, **kwargs): ...
    def feature_engineering_expand_basic(self, dataframe, metadata, **kwargs): ...
    def feature_engineering_standard(self, dataframe, metadata, **kwargs): ...
    def set_freqai_targets(self, dataframe, metadata, **kwargs): ...

    def populate_indicators(self, dataframe, metadata):
        return self.freqai.start(dataframe, metadata, self)
```

- Features go in `feature_engineering_*()` only. Features defined in `populate_indicators()` make FreqAI fail in dry/live (docs). `self.freqai.start()` only inside `populate_indicators()`.
- Prefix `%` marks a feature, `%%` a feature that is also returned to the strategy (plotting; see leakage notes), `&` a target. Features are removed from the dataframe FreqAI returns.
- Expansion: `expand_all` features are repeated for every `indicator_periods_candles` value, every `include_timeframes`, every `include_corr_pairlist` pair and every shift of `include_shifted_candles`; `expand_basic` skips the periods; `standard` runs once on the base timeframe. In the tested example 58 features were trained from 9 features written.
- Use the column names FreqAI gives back: `&-s_close` (prediction), `&-s_close_mean`/`&-s_close_std` (training statistics), `do_predict` (1 means trustworthy), `DI_values`. Trade only where `do_predict == 1` (docs: 1 is trustworthy, 0, -1, -2 mean outlier detectors fired, 2 means the model expired).
- Classifiers need string targets and a classifier model (`LightGBMClassifier`); regressors need numbers. Details in references/models.md.

## Training and backtesting in short

- `train_period_days` is the width of the training window; `backtest_period_days` is how many days are predicted before the window slides and the model is retrained. A 61-day range with 7-day steps trained 9 models (observed). More retrains mean slower backtests (docs: a 0.1-day step over 10 days trains 100 models per pair).
- Backtesting needs data before `--timerange` start: about `train_period_days` plus the startup candles of the largest timeframe (worked example in references/running.md).
- Backtest models are not kept by default; metadata and predictions are (observed). `save_backtest_models: true` keeps models for a dry/live start from them.
- Same `identifier` and config: the next backtest loads saved predictions and trains nothing (observed: 9 trainings 29 s, 0 trainings 25 s, identical trades). Changed feature names with the same identifier gave an `ERROR ... found different features` (observed). Changed values under the same names were not tested; docs say a new `identifier` is required for any feature change.
- Dry/live: models retrain in a background thread as often as possible unless `live_retrain_hours` is set; `expiration_hours` stops predictions from old models; `purge_old_models` keeps the newest N models on disk.
- Hyperopt works only on entry/exit thresholds, not on features or FreqAI config; `--analyze-per-epoch` is not compatible (docs, references/running.md).

## Outliers and data options (brief)

`DI_threshold` (Dissimilarity Index) lowers `do_predict` for points unlike the training data; `use_SVM_to_remove_outliers`, `use_DBSCAN_to_remove_outliers`, `principal_component_analysis`, `noise_standard_deviation`, `weight_factor`. Details and defaults in references/parameters.md and references/feature-engineering.md. These change what the model sees: re-validate and use a new `identifier` after changing them.

## Reinforcement learning

`ReinforcementLearner` trains an agent in a simplified environment; `&-action` carries its decisions; `rl_config` controls it. It needs the RL image and was not run in this repo: everything about it in references/reinforcement-learning.md is documented but untested. Docs warn the shipped reward function is a showcase, not for production, and that agents can find "cheats" that maximize reward without winning trades.

## Leakage and self-deception checklist

1. A feature, entry/exit or post-`freqai.start()` line that uses `shift(-n)`, a whole-column statistic, `iloc`, or a resample/merge that peeks forward leaks. Labels are the only place for future data.
2. The `lookahead-analysis` of a FreqAI strategy flags all target columns, `do_predict` and the enter/exit columns, and in tests a leaky `%` feature gave the same result as a clean strategy (false negative, observed). A `%%` feature does show up, but so does a clean one, so it is no better as a test. Review feature code by hand.
3. `recursive-analysis` lists only the `&` columns for a FreqAI strategy, with large percentages that come from different training data per startup count, not from indicator recursion (observed). It cannot assess feature recursion.
4. Backtest trains on past data only per window, but retraining cadence in live differs (continuous, queue of pairs, model age discrepancy); a model that is hours old trades differently than a fresh one (docs: `expiration_hours`).
5. In-sample fit: predictions inside the training window look great. Judge only on windows after the training range, and on trade counts, not on one profit number.
6. Do not tune features/config on the same range you report. Hyperopt of thresholds on stored predictions optimizes against predictions that already exist: check on an unseen range.
7. `fit_live_predictions_candles`, `&*_mean`/`_std` thresholds and `DI` are derived from past data only; do not replace them with whole-dataframe statistics.

## Validation gate

Before reporting a FreqAI strategy as done, show the user:

1. The training log: windows, number of features and data points, no unexpected NaN drops, the model name and `identifier`.
2. `lookahead-analysis`: 0 biased entry/exit signals; flagged columns limited to the `set_freqai_targets()` columns (`&`, docs) and, repo-observed, FreqAI's own outputs (`do_predict`, `DI_values`, `enter_long`, `enter_short`, `exit_long`, `exit_short`, `enter_tag`, `exit_tag`), only when an `&` column is also flagged. The only blanket docs exception is FreqAI `set_freqai_targets()` columns; pairlist-dependent logic and limit orders with `custom_*_price` can also give documented false positives, each explained, never silently ignored. Any other flagged column (a `%%` feature, a column computed from predictions) is an open finding.
3. `recursive-analysis`: run it, and say that for FreqAI it only lists model outputs and does not assess the features. The repo harness prints `NOT ASSESSED` for this case rather than a pass. To test feature recursion, compute the same indicators in a plain strategy and run recursive-analysis there (a repo suggestion, not tested).
4. A manual review of every `feature_engineering_*()` line, `populate_entry_trend()`, `populate_exit_trend()` and any code after `self.freqai.start()` against the leakage checklist. Under `--freqai` an inline leak in signal code is caught only by the biased entry/exit signal counts, and the tools cannot see `%` features at all.
5. An out-of-sample backtest with a fresh `identifier`, with trade counts, and the honest limits: backtest retraining is simulated, fills are idealized, live retraining behavior was not tested.

Only then suggest a dry run. Live trading is the user's separate, explicit decision.

In this repo: `tests/run_checks.sh FreqaiExample --config tests/config.freqai.json --image freqtradeorg/freqtrade:2026.10_freqai --freqai --freqaimodel LightGBMRegressor` (about 3 minutes cold), `tests/test_freqai_fixtures.sh` for the false-negative and flagged fixtures.

## References

- references/config.md - the `freqai` block, required keys, tested minimal config, pairlist and data notes
- references/feature-engineering.md - feature and target functions (tested code), prefixes, expansion, `metadata`, startup candles, dataframe keys
- references/running.md - backtesting, retraining windows, data range math, model and prediction reuse, live, hyperopt, observed behavior
- references/models.md - `list-freqaimodels` output, regressors vs classifiers, custom models, PyTorch
- references/reinforcement-learning.md - RL overview, `rl_config`, rewards (untested)
- references/parameters.md - FreqAI parameter table with defaults, outlier methods, doc inconsistencies

## Related skills

freqtrade-validation (the gate, lookahead and recursive checks), freqtrade-backtesting (read backtests), freqtrade-hyperopt (thresholds only), freqtrade-strategy (signals, ROI, stoploss), freqtrade-config (config keys, pairlists), freqtrade-setup (install, data download).

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
