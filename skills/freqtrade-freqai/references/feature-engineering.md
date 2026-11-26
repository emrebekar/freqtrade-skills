Source: docs/freqai-configuration.md#building-a-freqai-strategy
Source: docs/freqai-configuration.md#important-dataframe-key-patterns
Source: docs/freqai-configuration.md#setting-the-startup_candle_count
Source: docs/freqai-configuration.md#creating-a-dynamic-target-threshold
Source: docs/freqai-feature-engineering.md#defining-the-features
Source: docs/freqai-feature-engineering.md#gain-finer-control-over-feature_engineering_-functions-with-metadata
Source: docs/freqai-feature-engineering.md#returning-additional-info-from-training
Source: docs/freqai-feature-engineering.md#weighting-features-for-temporal-importance
Source: docs/freqai-feature-engineering.md#building-the-data-pipeline

# Feature engineering and targets

## The four functions (docs)

| Function | Called | Purpose |
|----------|--------|---------|
| `feature_engineering_expand_all(dataframe, period, metadata, **kwargs)` | per `indicator_periods_candles` value, per `include_timeframes`, per `include_corr_pairlist` pair, per shift | indicators that depend on a period |
| `feature_engineering_expand_basic(dataframe, metadata, **kwargs)` | per timeframe, pair, shift (not per period) | period-free features (returns, raw volume) |
| `feature_engineering_standard(dataframe, metadata, **kwargs)` | once, on the base timeframe, last | features that must not expand (hour of day) |
| `set_freqai_targets(dataframe, metadata, **kwargs)` | required | labels, `&`-prefixed |

All four are optional except `set_freqai_targets()`. Docs conflict on signatures: the strategy page (freqai-configuration.md#building-a-freqai-strategy) shows `feature_engineering_expand_all(self, dataframe, period, **kwargs)` and the others without `metadata`, while the feature engineering page shows `metadata` in each. Both work because of `**kwargs` (the tested code below uses the `metadata` form). Docs: `metadata` has `pair`, `tf` (timeframe), `period`; use it to build a feature only for some timeframes, for example `if metadata["tf"] == "1h":`.

Number of features (docs): written features x `len(include_timeframes)` x `len(include_corr_pairlist)` x (1 + `include_shifted_candles`) x `len(indicator_periods_candles)` for `expand_all`; without the period factor for `expand_basic`; `standard` is not expanded. The docs formula counts shifted candles as a factor of `include_shifted_candles`; observed in the tested config (shift 1) the count is `1 + shift`, because the unshifted feature stays: 5 expand_all features x 1 period x 2 timeframes x 2 pairs x 2 = 40, plus 2 expand_basic x 2 x 2 x 2 = 16, plus 2 standard = 58, matching the log line `Training model on 58 features`.

Naming: a `-period` suffix in a feature name is replaced by `-period_<n>`; FreqAI then appends `_shift-<k>`, the pair and the timeframe, for example `%-rsi-period_10_shift-1_BTC/USDT_5m` (observed; the docs show `%%-rsi-period_10_ETH/USDT:USDT_1h` for a futures pair).

## Tested strategy code

The whole strategy is [tests/strategies/FreqaiExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/FreqaiExample.py). Feature functions:

<!-- tested: tests/strategies/FreqaiExample.py lines 20-40 -->
```python
    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period, metadata, **kwargs
    ) -> DataFrame:
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata, **kwargs) -> DataFrame:
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata, **kwargs) -> DataFrame:
        dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        dataframe["%-hour_of_day"] = (dataframe["date"].dt.hour + 1) / 25
        return dataframe
```

Target (the label looks into the future on purpose; this is the documented example, the `&` column is the only thing allowed to do that):

<!-- tested: tests/strategies/FreqaiExample.py lines 42-50 -->
```python
    def set_freqai_targets(self, dataframe: DataFrame, metadata, **kwargs) -> DataFrame:
        # Intentionally looks into the future: this is the label the model learns to predict.
        label_period = self.freqai_info["feature_parameters"]["label_period_candles"]
        dataframe["&-s_close"] = (
            dataframe["close"].shift(-label_period).rolling(label_period).mean()
            / dataframe["close"]
            - 1
        )
        return dataframe
```

Entry and exit from the prediction, gated on `do_predict`:

<!-- tested: tests/strategies/FreqaiExample.py lines 52-72 -->
```python
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["do_predict"] == 1)
                & (dataframe["&-s_close"] > 0.0005)
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "pred_up")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            ((dataframe["do_predict"] == 1) & (dataframe["&-s_close"] < 0) & (dataframe["volume"] > 0)),
            ["exit_long", "exit_tag"],
        ] = (1, "pred_down")
        return dataframe
```

Class attributes (lines 8-18): `INTERFACE_VERSION = 3`, `timeframe = "5m"`, `can_short = False`, `minimal_roi = {"0": 0.05}`, `stoploss = -0.10`, `startup_candle_count: int = 40`. The `0.0005` entry threshold is a teaching number. It produced 570 trades in the test range with a loss of -86.6 USDT: it demonstrates plumbing, not an edge.

## Prefixes

- `%name`: a training feature. Removed from the dataframe FreqAI returns (tens of thousands can be created).
- `%%name`: also a training feature, but returned to the strategy for FreqUI and `plot-dataframe` (docs). Observed on the pinned release: `lookahead-analysis` and `recursive-analysis` then list these columns as biased even for a clean RSI, so a `%%` column cannot serve as proof either way. Use `%%` only for plotting.
- `&name`: a target. FreqAI returns the prediction under the same name (`&-s_close`) plus `&-s_close_mean` and `&-s_close_std`, the training statistics (or live statistics with `fit_live_predictions_candles`). Docs naming convention `&-s*`.
- Hyphen naming is convention. The classifier docs use `&s-up_or_down`; both start with `&`.

## Targets

- Regressor: continuous target, for example `df["&-s_close"] = df["close"].shift(-100)`-style or the tested relative form.
- Classifier: string classes, for example `np.where(df["close"].shift(-100) > df["close"], "up", "down")`. In docs with PyTorch classifiers also set `self.freqai.class_names` in `set_freqai_targets()`.
- Several targets: define several `&` columns (regressors); for classifiers keep all classes in one column (docs).
- `label_period_candles` (config) is the offset used in the example; it is not required, you can build labels any way.
- `buffer_train_data_candles` (default 0): cut candles from both ends of the training data after indicators are populated, for labels like `argrelextrema` that cannot be known at the range edges (docs).
- Rows whose target is NaN (the last `label_period_candles` candles of the training window) are dropped automatically (docs, for shifted targets).

## `startup_candle_count`

Set it as in any strategy: the largest period passed to an indicator in the `feature_engineering_*` functions. Docs: TA-Lib sometimes needs more than the period to avoid NaNs; doubling it is "typically safest". Check the log line `dropped N training points due to NaNs in populated dataset M` (observed: `dropped 12 training points due to NaNs in populated dataset 4320` with `startup_candle_count = 40` and a period of 10).

## Dynamic targets from training statistics (docs)

The `&*_mean` and `&*_std` columns describe the label distribution of the last training, so a prediction can be compared to what was normal:

```python
dataframe["target_roi"] = dataframe["&-s_close_mean"] + dataframe["&-s_close_std"] * 1.25
dataframe["sell_roi"] = dataframe["&-s_close_mean"] - dataframe["&-s_close_std"] * 1.25
```

(Docs snippet, not run here.) With `fit_live_predictions_candles` set, FreqAI starts with training statistics and gradually switches to real predictions, saved and reloaded for the same `identifier`.

## Returning extra values from training (docs)

A custom model can write `dk.data['extra_returns_per_train']['my_new_value'] = XYZ`; it appears as `dataframe['my_new_value']`. Declare defaults in the config so the dataframe shape is right: `"extra_returns_per_train": {"total_profit": 4}`. Not run here.

## Temporal weights and the data pipeline (docs)

`weight_factor` weights recent points more via `W_i = exp(-i / (alpha * n))` (typically below 1). The default pipeline is a `MinMaxScaler(-1, 1)` and a `VarianceThreshold` (drops constant columns); config switches add `SVMOutlierExtractor`, PCA, `DissimilarityIndex`, noise, DBSCAN. A custom pipeline is built by overriding `define_data_pipeline()` / `define_label_pipeline()` in a custom model (DataSieve, sklearn-like). A custom model that relied on the old `data_cleaning_train/predict()` must migrate (docs link strategy_migration). Not run here.

## Look-ahead rules for features

Docs: backtesting calls `set_freqai_targets()` once per backtest window, which simulates dry/live without look-ahead, but defines features once over the whole training range, so features must not look ahead. Concretely avoid in `feature_engineering_*()`: `shift(-n)`, `.iloc` positions, statistics over the whole column (`mean()`, `std()` of the full column), resampling or merging informative data without the usual forward-fill shift (freqtrade-validation fix catalog). Observed: a fixture with `%-leak = close.shift(-1) / close` ([tests/fixtures/strategies/FreqaiLookaheadBad.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/fixtures/strategies/FreqaiLookaheadBad.py)) was not flagged by `lookahead-analysis` at all.
