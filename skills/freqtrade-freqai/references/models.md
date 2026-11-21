Source: docs/freqai-configuration.md#using-different-prediction-models
Source: docs/freqai-configuration.md#setting-model-targets
Source: docs/freqai-configuration.md#pytorch-module
Source: docs/commands/list-freqaimodels.md
Source: docs/freqai.md#install-prerequisites

# Prediction models

Select a model with `--freqaimodel NAME`. Names come from `freqtrade list-freqaimodels`, which also searches `user_data/freqaimodels` and `--freqaimodel-path PATH`. `-1` / `--one-column` prints names only.

## Models in the `2026.10_freqai` image (observed)

```bash
freqtrade list-freqaimodels --one-column
```

```text
LightGBMClassifier
LightGBMClassifierMultiTarget
LightGBMRegressor
LightGBMRegressorMultiTarget
SKLearnRandomForestClassifier
XGBoostClassifier
XGBoostRFClassifier
XGBoostRFRegressor
XGBoostRegressor
XGBoostRegressorMultiTarget
```

Without `-1` the command prints a table with `Strategy name`, `Location` and `Status`. In this image five more built-in files show `LOAD FAILED` because torch / stable-baselines are not installed (observed): `PyTorchTransformerRegressor`, `PyTorchMLPRegressor`, `PyTorchMLPClassifier`, `ReinforcementLearner`, `ReinforcementLearner_multiproc`. They need the torch or RL image (docs: `stable_freqaitorch`, `stable_freqairl` tags, or the matching install answer in `setup.sh`).

Docs inconsistencies: the introduction says "Eight examples are currently available"; the image lists ten usable plus five that need extra packages. Docs list CatBoost among the libraries but note it is "no longer actively supported since 2025.12"; no CatBoost model appears in the 2026.10 list. Verify with `list-freqaimodels` rather than the docs.

## Regressor or classifier

- Regressor (`...Regressor`): target is a number, for example the relative future price in the tested strategy. Tested: `LightGBMRegressor` (backtest, lookahead, recursive; see running.md).
- Classifier (`...Classifier`): target is a string class. Docs example:

```python
df['&s-up_or_down'] = np.where( df["close"].shift(-100) > df["close"], 'up', 'down')
```

  (Docs; not run here.) Multiple classes go in the same column, e.g. a `'same'` class assigned with a second `np.where`. For the PyTorch classifiers also set `self.freqai.class_names = ["down", "up"]` inside `set_freqai_targets()`.
- `...MultiTarget` models are documented only by name in `list-freqaimodels`; the docs say regressors can predict several targets by defining several `&` columns. Not tested.
- The strategy's entry/exit logic must match the target: a classifier gives class labels (and, in `do_predict`-gated logic, you compare against the class string), a regressor gives a number to compare to a threshold.

All the built-in models are gradient boosted tree libraries (LightGBM, XGBoost) except `SKLearnRandomForestClassifier` (docs describe the gradient boosting family; the random forest is inferred from its name). Docs: reported accuracy differs by application; pick on your own out-of-sample results, not on blog comparisons.

## Model parameters

`model_training_parameters` accepts any parameter of the library, e.g. LightGBM's `n_estimators`, `learning_rate`, `n_jobs` (docs). Tested values: `{"n_estimators": 50, "n_jobs": 2, "verbose": -1}`. More trees and more features mean slower training and slower backtests, and a larger risk of overfitting a short window.

## Custom models (docs)

Subclass `IFreqaiModel` (or a base such as `BaseRegressionModel`), override `fit()`, `train()`, `predict()` as needed, save the file in `user_data/freqaimodels/`; the class name must equal the `--freqaimodel` value and be unique (do not shadow a built-in). The pipeline can be customized with `define_data_pipeline()` and `define_label_pipeline()` (feature-engineering.md). Not run here.

## PyTorch (docs, untested here)

Quick start from the docs: `freqtrade trade --config config_examples/config_freqai.example.json --strategy FreqaiExampleStrategy --freqaimodel PyTorchMLPRegressor --strategy-path freqtrade/templates`. Needs the torch install/image. Structure: your `nn.Module` plus a `BasePyTorch*` subclass implementing `fit()` with `PyTorchModelTrainer`; trainer options come from `model_training_parameters.trainer_kwargs` (`n_epochs`, `n_steps`, `batch_size`, `early_stopping_patience`, see parameters.md). `torch.compile()` can speed up specific GPUs but removes eager error traces. Docs security notice: loading saved PyTorch models needs `weights_only=False`; only load your own.
