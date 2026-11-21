Source: docs/freqai-parameter-table.md
Source: docs/freqai-feature-engineering.md#outlier-detection
Source: docs/freqai-configuration.md#important-dataframe-key-patterns

# FreqAI parameter reference

Defaults are the docs' parameter table values; "schema" marks a value read from the 2026.10 image's config schema (observed), "none" means no default is documented.

## `freqai` (general)

| Key | Default | Meaning |
|-----|---------|---------|
| `enabled` | schema: false | turn FreqAI on |
| `train_period_days` | required (schema default 0) | width of the sliding training window, days (integer) |
| `backtest_period_days` | required (schema default 7) | days predicted before the window slides and the model retrains in backtesting; float |
| `identifier` | required (schema default `example`) | unique run id; keeps saved models and predictions; change when features/model change |
| `live_retrain_hours` | 0 (as often as possible) | minimum hours between trainings in dry/live |
| `expiration_hours` | 0 (never) | no predictions from a model older than this; `do_predict` = 2. Docs prose says `expired_hours` in places, the code reads `expiration_hours` (observed) |
| `purge_old_models` | 2 | models kept on disk (dry/live); 0 keeps all; boolean accepted |
| `save_backtest_models` | false | keep models trained in a backtest (for starting live from them) |
| `fit_live_predictions_candles` | none | use the last N candles of predictions for target statistics instead of the training set |
| `continual_learning` | false | start each model from the previous one (experimental, disables PCA) |
| `write_metrics_to_disk` | false | train/inference timings and CPU usage to a json file |
| `data_kitchen_thread_count` | max threads - 2 | threads for data processing (not training) |
| `activate_tensorboard` | true | TensorBoard logging (needs torch image) |
| `wait_for_training_iteration_on_reload` | true | finish the current training before graceful shutdown |
| `extra_returns_per_train` | none | defaults for extra columns a custom model returns |
| `override_exchange_check` | false | run FreqAI on exchanges without enough history |
| `keras` | false | model uses Keras save/load |
| `conv_width` | docs: 2, schema: 1 (inconsistent) | width of a neural network input tensor, replaces `include_shifted_candles` for such models |
| `reduce_df_footprint` | false | cast numeric columns to float32/int32; set at the top level of the config, not inside `freqai` (docs) |

## `freqai.feature_parameters`

| Key | Default | Meaning |
|-----|---------|---------|
| `include_timeframes` | none | timeframes that `feature_engineering_expand_*()` run for |
| `include_corr_pairlist` | none | correlated pairs added as features for every whitelist pair |
| `label_period_candles` | none (optional) | offset into the future for labels in `set_freqai_targets()` |
| `include_shifted_candles` | schema: 0 | add features from this many previous candles |
| `indicator_periods_candles` | none | periods `expand_all` runs for |
| `weight_factor` | none | weight recent data more (typically below 1) |
| `indicator_max_period_candles` | no longer used | replaced by the strategy's `startup_candle_count` |
| `DI_threshold` | none (off) | Dissimilarity Index outlier threshold (docs: "positive float (typically < 1)", yet the docs examples use 1) |
| `use_SVM_to_remove_outliers` | none | SVM outlier removal for training and incoming data |
| `svm_params` | none | `SGDOneClassSVM` params (`shuffle` default false, `nu` 0 to 1) |
| `use_DBSCAN_to_remove_outliers` | none | DBSCAN outlier removal |
| `principal_component_analysis` | false | reduce dimensions (explained variance >= 0.999) |
| `noise_standard_deviation` | 0 | gaussian noise added to training features, relative to the normalized -1..1 space (docs list the type as Integer but use 0.05 and 0.1) |
| `outlier_protection_percentage` | 30 | if more than this % of points are outliers by SVM/DBSCAN, detection is ignored with a warning, and no predictions are made from that training |
| `reverse_train_test_order` | false | train on the latest split and test on the older one (unorthodox; understand it before use) |
| `shuffle_after_split` | false | shuffle train and test sets separately after the split |
| `buffer_train_data_candles` | 0 | trim this many candles from both ends of the training data after indicators are computed |
| `plot_feature_importances` | 0 | plot top/bottom N feature importances to `user_data/models/<identifier>/` |

## `freqai.data_split_parameters`

Any argument of scikit-learn `train_test_split()`. `test_size` (float below 1, the test fraction); `shuffle` (default false; keep false for time series).

## `freqai.model_training_parameters`

Library-specific. Common: `n_estimators`, `learning_rate`, `n_jobs` / `thread_count` / `task_type` (threads or `gpu`/`cpu`, name depends on the library). PyTorch (general): `learning_rate` (3e-4), `model_kwargs` ({}), `trainer_kwargs` ({}); `trainer_kwargs` keys: `n_epochs` (10, overrides `n_steps`), `n_steps` (none), `batch_size` (64), `early_stopping_patience` (0 = off, needs `test_size > 0`).

## `freqai.rl_config` (untested, see reinforcement-learning.md)

`train_cycles`, `max_trade_duration_candles`, `model_type`, `policy_type`, `max_training_drawdown_pct` (0.8), `cpu_count` (physical cores - 1), `model_reward_parameters`, `add_state_info` (false; dry/live only), `net_arch` ([128, 128]), `randomize_starting_position` (false), `drop_ohlc_from_features` (false), `progress_bar` (false).

## Outlier methods

All of these remove or flag points unlike the training data. They change what the model trains on and when `do_predict` is 1. Use a new `identifier` after enabling or tuning them, and do not judge a model on predictions it was allowed to discard silently: report how many candles were skipped.

- Dissimilarity Index (DI): measures the distance of a new feature vector to the training points relative to the average training distance. `DI_threshold` higher means more lenient (docs). A prediction above the threshold subtracts 1 from `do_predict`. `DI_values` is returned to the strategy; docs example: `dataframe['outlier'] = np.where(dataframe['DI_values'] > self.di_max.value/10, 1, 0)`. In the repo test, a config with `DI_threshold: 0` logged `datasieve.pipeline - WARNING - Could not find step di in pipeline, returning None` on every training; the key was removed from the tested config (observed).
- SVM: `use_SVM_to_remove_outliers`; also subtracts 1 from `do_predict` when it flags a point.
- DBSCAN: `min_samples` is a quarter of the candles in the feature set and `eps` comes from the elbow of the k-distance graph (docs); also subtracts 1.
- `do_predict` therefore ranges from -2 to 2 (docs): 1 trust, 0 one detector fired, -1 two fired, -2 three fired (DI, SVM, DBSCAN), 2 expired model.
- PCA: faster training at the cost of interpretable features; disabled automatically with `continual_learning`.

## Docs inconsistencies collected

- `expired_hours` (freqai-configuration.md:166 dataframe key table, freqai-running.md:15) vs `expiration_hours` (parameter table, code). The table also types it "positive integer" while the running page example uses 0.5.
- `feature_engineering_*` signatures with and without `metadata` (freqai-configuration.md vs freqai-feature-engineering.md).
- `purge_old_models: true` (running) vs an integer default 2 (table).
- Feature count formula uses `include_shifted_candles` as a factor (observed `1 + include_shifted_candles`) and counts only the corr pairs listed, while the base pair is also a feature source (observed 2 pairs for 1 listed: undercount).
- TensorBoard port 6060 (running) vs 6006 (RL page).
- "Eight examples" of models vs ten usable in the image; CatBoost mentioned, not present.
- `conv_width` default 2 (docs) vs 1 (schema).
- `noise_standard_deviation` documented as Integer, examples use fractions.
- RL: environment class names and a dedented `return dataframe` in the strategy snippet.
- `backtest_period_days` described as usable for sub-daily retraining in live (running page); the table ties it to backtesting.
