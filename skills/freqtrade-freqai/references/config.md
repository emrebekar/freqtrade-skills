Source: docs/freqai-configuration.md#setting-up-the-configuration-file
Source: docs/freqai-parameter-table.md#general-configuration-parameters
Source: docs/freqai-parameter-table.md#feature-parameters
Source: docs/freqai.md#common-pitfalls

# FreqAI configuration

FreqAI is configured in the normal Freqtrade config (see freqtrade-config) plus a `freqai` object. `"enabled": true` switches it on. A strategy that defines FreqAI methods and runs without the `freqai` block (or the reverse) does not work.

## Required keys (docs)

The docs mark `freqai`, `train_period_days`, `backtest_period_days` and `identifier` as **Required**, and the minimal example in the configuration page also sets `purge_old_models`, `feature_parameters` (`include_timeframes`, `include_corr_pairlist`, `label_period_candles`, `include_shifted_candles`, `indicator_periods_candles`) and `data_split_parameters.test_size`. Observed in the 2026.10 image's config schema (config_schema.py): `train_period_days` defaults to 0, `backtest_period_days` to 7 and `identifier` to `"example"`, so a missing key may not fail at load time; set all four explicitly.

`identifier` is a unique name for one run. Keeping it the same keeps saved models and predictions (crash resilience, fast re-backtests). Docs: change it, or delete `user_data/models/<identifier>`, as soon as you try new features or a new model.

## Tested config (repo)

This block is the `freqai` object of [tests/config.freqai.json](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/config.freqai.json), used with `LightGBMRegressor` on `BTC/USDT` (pair whitelist of one) with `ETH/USDT` as a correlated pair, 5m plus 1h. It is deliberately small so CI stays fast, not a recommendation.

<!-- tested: tests/config.freqai.json lines 21-38 -->
```json
  "freqai": {
    "enabled": true,
    "identifier": "skill-test",
    "train_period_days": 15,
    "backtest_period_days": 7,
    "purge_old_models": 2,
    "fit_live_predictions_candles": 50,
    "activate_tensorboard": false,
    "feature_parameters": {
      "include_timeframes": ["5m", "1h"],
      "include_corr_pairlist": ["ETH/USDT"],
      "label_period_candles": 12,
      "include_shifted_candles": 1,
      "indicator_periods_candles": [10]
    },
    "data_split_parameters": {"test_size": 0.25, "shuffle": false},
    "model_training_parameters": {"n_estimators": 50, "n_jobs": 2, "verbose": -1}
  }
```

Notes on what was observed with it (backtest `--timerange 20260801-20261001`, data from 2026-07-01):
- FreqAI raised the data it loads: `Increasing startup_candle_count for freqai on 5m to 4360` (15 days of 5m candles = 4320, plus the strategy's 40) and `... on 1h to 400`. The existing test data was enough; no data was changed for FreqAI.
- First training window `2026-07-17` to `2026-08-01`, i.e. before the backtest range, as the docs describe.
- `activate_tensorboard: false` because TensorBoard needs the torch image (docs, default true).
- `model_training_parameters` is passed to the model library (here LightGBM); `verbose: -1` silences its output.
- Observed 2026.10: `data_split_parameters.shuffle: false` keeps time order; the docs call shuffling a way to reduce bias from autocorrelated data, but unshuffled is the usual time-series choice (docs table: default `False`).

## Pairlist rule (docs)

FreqAI cannot be combined with dynamic `VolumePairList` or any pairlist filter that adds or removes pairs, because it downloads all training data at start and cannot get data for pairs that arrive later. `ShufflePairlist`, or a `VolumePairList` that keeps the pair set constant, works. `include_corr_pairlist` adds correlated pairs as features for every whitelist pair; they must have data too.

## Where things are written

Models and predictions go to `<userdir>/models/<identifier>/`. Observed after a backtest: `run_params.json`, `backtesting_predictions/cb_<pair>_<timestamp>_prediction.feather`, and `sub-train-<PAIR>_<timestamp>/cb_<pair>_<timestamp>_metadata.json` (no model file unless `save_backtest_models: true`). Plots from `plot_feature_importances` land in the same folder (docs).

## Exchange check

`override_exchange_check` (default false, docs) forces FreqAI to run on exchanges that may not have enough history. Leave it false unless you know the strategy needs no history.
