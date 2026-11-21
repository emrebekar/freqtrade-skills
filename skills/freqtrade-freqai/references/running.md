Source: docs/freqai-running.md#running-freqai
Source: docs/freqai-running.md#live-deployments
Source: docs/freqai-running.md#backtesting
Source: docs/freqai-running.md#downloading-data-to-cover-the-full-backtest-period
Source: docs/freqai-running.md#deciding-the-size-of-the-sliding-training-window-and-backtesting-duration
Source: docs/freqai-running.md#defining-model-expirations
Source: docs/freqai-running.md#controlling-the-model-learning-process
Source: docs/freqai-running.md#continual-learning
Source: docs/freqai-running.md#hyperopt
Source: docs/freqai-running.md#using-tensorboard
Source: docs/lookahead-analysis.md
Source: docs/recursive-analysis.md

# Running FreqAI: backtesting, live, reuse, validation

## Backtesting

```bash
freqtrade backtesting --strategy MyFreqaiStrategy --config config.json --freqaimodel LightGBMRegressor --timerange 20260801-20261001
```

Tested in this repo as `tests/run_checks.sh FreqaiExample --config tests/config.freqai.json --image freqtradeorg/freqtrade:2026.10_freqai --freqai --freqaimodel LightGBMRegressor`, which runs backtesting, lookahead-analysis and recursive-analysis with the image's FreqAI dependencies.

How it works (docs, observed values from that run):
- For every backtest window FreqAI trains a model on the preceding `train_period_days`, predicts the next `backtest_period_days`, then slides the window forward and retrains. A 61-day `--timerange` with `backtest_period_days: 7` logged `Training 9 timeranges` and `1/9 trains`... `9/9 trains` (observed). The first window was `2026-07-17` to `2026-08-01`, before the backtest start.
- Docs: `set_freqai_targets()` is called once per backtest window, so targets simulate dry/live without look-ahead. `feature_engineering_*()` is evaluated once over the whole training range: features must not look ahead.
- Each training in the test took about 0.5 s (15 days, 58 features, 3231 data points, `n_estimators: 50`); data preparation dominated the backtest time. The whole `run_checks.sh` for `FreqaiExample` took about 2 min 45 s, a backtest alone about 30 s.
- Backtest uses data only; FreqAI does not download in backtesting. Docs: download data first with `download-data`.
- A model trained for a window predicts every candle of that window. Docs: the sliding window emulates weekly retraining; real live retraining is continuous (below), so it is an emulation.

### Data range to download (docs, worked example)

Move the start of the range back by `train_period_days` and by the `startup_candle_count` of the largest `include_timeframes` entry. Docs example: `20210501` - 30 days - 40 x 1h / 24 = `20210330` (31.7 days earlier). Observed in the repo test: FreqAI raised the loaded data to `startup_candle_count` 4360 on 5m (15 x 288 + 40) and 400 on 1h; the backtest loaded `2026-07-16 20:40` to `2026-09-30 23:55`.

### Choosing the window (docs)

- `train_period_days` is the training width; `backtest_period_days` the prediction step. Docs example: 30 days train, 7 days step; `--timerange 20210501-20210701` trains 8 models.
- A fractional step is allowed, but the range is divided by it: 10 days with 0.1 trains 100 models per pair. Docs: the best test of an adaptive model is to run it dry.
- In dry/live, `live_retrain_hours` sets the retraining cadence, not `backtest_period_days` (the docs sentence that `backtest_period_days` "can be a float to indicate sub-daily retraining in live/dry mode" contradicts the parameter table, which ties it to backtesting; use `live_retrain_hours` live).

## Model and prediction reuse

- Same `identifier`, same config: FreqAI finds saved predictions and trains nothing. Observed on 2026.10: second backtest logged `Found backtesting prediction file ...` for every window, `0` trainings, and identical results (570 trades, same totals).
- Docs: this exists so you can tune entry/exit criteria quickly. To change features, set a new `identifier`. Observed: running a strategy with an extra feature under the old `identifier` logged `ERROR ... Trying to access pretrained model with identifier but found different features furnished by current strategy. Change identifier to train from scratch` (the harness regex treats `ERROR` as failure, so this cannot pass silently).
- Not tested: changing a feature's formula but keeping its name. Treat any change in feature or label code, `label_period_candles`, timeframes, pairs, outlier options or model as requiring a new `identifier` (docs).
- Predictions are stored in `backtesting_predictions/` (feather) and, for dry/live, `historic_predictions.pkl` (docs).
- `save_backtest_models: true` (default false) keeps the models trained in a backtest so a dry/live run with the same `identifier` can start from them (docs). Observed with the default: only `*_metadata.json` and the predictions were on disk. Docs note for reuse in live: FreqAI calls the strategy with a dataframe of length 1 to reuse predictions; if the strategy needs more data for the same features, use a new `identifier` per backtest.
- `--freqai-backtest-live-models` (flag exists in `backtesting --help`, observed): backtest with predictions collected during dry/live; docs say do not pass `--timerange`, it is derived from the stored predictions. Not run here.
- Delete `user_data/models/<identifier>` to force retraining.
- `purge_old_models` (default 2): number of models kept on disk for dry/live; 0 keeps all; accepts a boolean for backward compatibility. Docs inconsistency: the live deployments text shows `"purge_old_models": true`, the parameter table says integer with a boolean accepted (the config schema accepts both, observed).
- Security (docs): loading saved models from untrusted sources can execute code (requires `weights_only=False`); only load models you trained.

## Live (dry run) deployment

```bash
freqtrade trade --strategy MyFreqaiStrategy --config config.json --freqaimodel LightGBMRegressor
```

(Docs; not run here. Docs quick start uses `FreqaiExampleStrategy` from `freqtrade/templates` with `--strategy-path freqtrade/templates`, and warns that example is for showcasing, not production.) FreqAI downloads the needed data itself, trains a model per pair (a queue keeps models equally fresh), and predicts with the newest model.
- `live_retrain_hours` (default 0: as often as possible) waits at least that long between trainings.
- `expiration_hours` (default 0: never) stops predictions from older models; `do_predict` is then 2. Docs inconsistency: the live deployment text and the `do_predict` table call it `expired_hours`. Observed in the 2026.10 image: the code reads only `expiration_hours`; `expired_hours` appears nowhere in the code base. Use `expiration_hours`.
- Model age matters: with 50 pairs at 5 minutes each the oldest model is over 4 hours old (docs example).
- Starting from a saved `identifier` still retrains if `live_retrain_hours` elapsed since the model's end.
- `wait_for_training_iteration_on_reload` (default true) waits for a training to finish on `/reload` or ctrl-c.
- `continual_learning: true` starts each model from the previous one. Docs: naive, experimental, high risk of overfitting or local minima; disables PCA.
- Keep `dry_run: true` until the validation gate is passed and the user decides otherwise.

## Controlling training

`model_training_parameters` passes parameters to the model library. `data_split_parameters` (scikit-learn `train_test_split` arguments such as `test_size`, `shuffle`) controls the in-window train/test split. `shuffle: false` keeps time order (docs: avoids biasing training with autocorrelated data). `label_period_candles` is the label offset used by the example. Defaults for other keys: parameters.md.

## Hyperopt with FreqAI (docs)

```bash
freqtrade hyperopt --hyperopt-loss SharpeHyperOptLoss --strategy MyFreqaiStrategy --freqaimodel LightGBMRegressor --config config.json --timerange 20260801-20261001
```

(Adapted from the docs command; not run here.) Restrictions: `--analyze-per-epoch` is not compatible with FreqAI; features in `feature_engineering_*()` and targets cannot be hyperopted, so model parameters cannot be optimized with hyperopt; entry/exit thresholds can, because FreqAI stores predictions as dataframes and reuses them. The docs example optimizes a `DI_values` threshold with `IntParameter(low=1, high=20, default=10, space="buy")` and `self.di_max.value / 10`. All the hyperopt overfitting cautions apply and more: predictions inside the training window are in-sample (freqtrade-hyperopt).

## lookahead-analysis and recursive-analysis on FreqAI strategies

Docs: `lookahead-analysis` "also supports freqai strategies"; its `biased_indicators` column "will falsely flag FreqAI target indicators defined in `set_freqai_targets()` as biased. These are not biased and can safely be ignored." The docs say nothing about FreqAI under `recursive-analysis`. Observed on 2026.10 with `FreqaiExample` (both commands accept `--freqaimodel`):

| Check | Observed |
|-------|----------|
| `lookahead-analysis` result row | `has_bias True`, 0 biased entry signals, 0 biased exit signals, `biased_indicators` = `&-s_close, &-s_close_mean, &-s_close_std, do_predict, exit_tag, exit_long, enter_tag, enter_long` |
| Output footer line | `Any indicators in 'biased_indicators' which are used within set_freqai_targets() can be ignored.` |
| Leaky `%` feature (`close.shift(-1)` in `feature_engineering_standard`) | identical row to the clean strategy: not detected (false negative) |
| Leaky `%%` feature | extra flagged column `%%-leak` (detected) |
| Clean `%%-rsi-period` feature | flagged as well, in the lookahead table and in recursive-analysis `found lookahead in indicator` lines (false positive) |
| `recursive-analysis` table | only `&-s_close`, `&-s_close_mean`, `&-s_close_std` rows, with variances such as -111.567% at the strategy's startup count and -59.637% at larger ones, and a 296.087% std row |

Reading it: the flagged signal columns (`enter_*`, `exit_*`, `do_predict`) are flagged because they derive from the flagged targets; real signal bias would show in `biased_entry_signals`/`biased_exit_signals`, which are 0 here. The recursive percentages most likely differ because each startup count changes the training data and hence the model, not because an indicator is recursive (inference, not tested). Neither command can validate `%` features. See freqtrade-validation for how to interpret the plain results and what else to review.

Repo harness (`tests/check_results.py`, `run_checks.sh --freqai`): lookahead passes only if no biased entry/exit signals and every flagged column is an `&` column or, only when at least one `&` column is also flagged, one of `do_predict`, `DI_values`, `enter_long/short`, `exit_long/short`, `enter_tag`, `exit_tag` (a repo rule derived from the observation above, not a Freqtrade rule). Any other flagged column fails. Recursive ignores `&` rows and prints `NOT ASSESSED` when nothing else is listed. `tests/test_freqai_fixtures.sh` proves both sides: the clean strategy passes, `FreqaiLookaheadBadReturned` (leaky `%%` feature) fails, and `FreqaiLookaheadBad` (leaky `%` feature) passes the check although it is leaky (documented limitation, not an endorsement).

## TensorBoard (docs)

`freqai.activate_tensorboard` (default true) logs for XGBoost, CatBoost, PyTorch and RL models and needs the torch image; run `tensorboard --logdir user_data/models/<identifier>` in a separate shell. Docs give port 6060 in the FreqAI running page and 6006 in the RL page (inconsistent; TensorBoard's own default is 6006). Turn it off for production, it slows training.
