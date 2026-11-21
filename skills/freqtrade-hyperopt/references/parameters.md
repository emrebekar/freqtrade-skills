Source: docs/hyperopt.md#configure-your-guards-and-triggers
Source: docs/hyperopt.md#hyperoptable-parameters
Source: docs/hyperopt.md#parameter-types
Source: docs/hyperopt.md#parameter-options
Source: docs/hyperopt.md#optimizing-an-indicator-parameter
Source: docs/hyperopt.md#optimizing-protections
Source: docs/advanced-hyperopt.md#dynamic-parameters

# Hyperoptable parameters

Define parameters at class level, then read them with `self.<name>.value` inside `populate_entry_trend()` / `populate_exit_trend()` (docs: always through the instance, never `MyStrategy.buy_rsi.value`, which returns the default).

## Types

Docs say "four parameter types" but list five.

| Type | Use | Constructor (read from the 2026.10 image, observed) |
|------|-----|------------------------------------------------------|
| `IntParameter` | whole numbers | `(low, high=None, *, default, space=None, optimize=True, load=True)` |
| `DecimalParameter` | floats with limited decimals (docs: default 3, preferred over `RealParameter`) | `(low, high=None, *, default, decimals=3, space=None, optimize=True, load=True)` |
| `RealParameter` | floats, no precision limit (docs: rarely used, near infinite space; no `.range`) | `(low, high=None, *, default, space=None, optimize=True, load=True)` |
| `CategoricalParameter` | a fixed list of choices | `(categories, *, default=None, space=None, optimize=True, load=True)` |
| `BooleanParameter` | shorthand for `CategoricalParameter([True, False])`, good for "enable" switches | `(*, default=None, space=None, optimize=True, load=True)` |

- `default` is keyword-only and required for Int/Decimal/Real. It is the value used when no hyperopt result is loaded.
- Space size matters (docs): `IntParameter(20, 40)` has 20 values, `DecimalParameter(20, 40, decimals=1)` has 200. A one-parameter space with 15 values is exhausted after 15 epochs; the log then says "The objective has been evaluated at this point before."

## Space assignment (docs)

- A parameter belongs to a space if its variable name starts with `buy_`, `sell_`, `enter_`, `exit_` or `protection_`, or if `space=` is given.
- Conflicting assignments (`buy_adx = IntParameter(4, 24, default=14, space='sell')`) use the explicit `space=`.
- A parameter with neither (for example `adx_period = IntParameter(4, 24, default=14)`) is not detected and is ignored.
- Custom space names are allowed (`space='my_custom_space'`): not `all` or `default`, and a valid Python identifier.
- Requesting a space with no parameters is an error ("no space was found"); `--ignore-missing-spaces` suppresses it.

## Options

- `optimize=False`: the parameter is not searched. It still holds `default` (or a loaded value).
- `load=False`: values from a previous run (`buy_params`/`sell_params` in the strategy, or the JSON file) are not used as the starting value; the default is used. Docs warning: backtesting then also uses the default, not the optimized value.

## Tested example

Parameter definitions (a fixed `optimize=False` one included). Names start with `buy_`/`sell_`, so `space=` is redundant but explicit.

<!-- tested: tests/strategies/HyperoptExample.py lines 22-27 -->
```python
    # Hyperoptable parameters. Names start with buy_/sell_, so the space is implied; space= is explicit anyway.
    buy_rsi = IntParameter(20, 50, default=40, space="buy")
    buy_zscore = DecimalParameter(-2.5, -0.5, decimals=1, default=-1.5, space="buy")
    buy_rsi_enabled = BooleanParameter(default=True, space="buy")
    sell_zscore = DecimalParameter(0.5, 2.5, decimals=1, default=1.5, space="sell")
    sell_rsi = IntParameter(50, 80, default=60, space="sell", optimize=False)  # fixed: not searched
```

Used in the signal methods (guards are combined with a trigger-like zscore condition). Indicators are fixed in `populate_indicators`:

<!-- tested: tests/strategies/HyperoptExample.py lines 29-35 -->
```python
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Fixed indicators only: parameter values must not be used here (hyperopt computes this once for all epochs).
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["close_mean_48"] = dataframe["close"].rolling(48).mean()
        dataframe["close_std_48"] = dataframe["close"].rolling(48).std()
        dataframe["zscore_48"] = (dataframe["close"] - dataframe["close_mean_48"]) / dataframe["close_std_48"]
        return dataframe
```

<!-- tested: tests/strategies/HyperoptExample.py lines 37-45 -->
```python
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            dataframe["zscore_48"] < self.buy_zscore.value,
            dataframe["volume"] > 0,
        ]
        if self.buy_rsi_enabled.value:
            conditions.append(dataframe["rsi"] < self.buy_rsi.value)
        dataframe.loc[reduce(lambda x, y: x & y, conditions), ["enter_long", "enter_tag"]] = (1, "zscore_rsi")
        return dataframe
```

<!-- tested: tests/strategies/HyperoptExample.py lines 47-52 -->
```python
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["zscore_48"] > self.sell_zscore.value) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "zscore_high")
        return dataframe
```

Imports needed (same file): `from functools import reduce`, `from freqtrade.strategy import BooleanParameter, DecimalParameter, IntParameter, IStrategy`.

In the test, a plain backtest of this file (no JSON present) logged "Strategy Parameter(default): ..." for each parameter, and `lookahead-analysis` and `recursive-analysis` passed (`tests/run_checks.sh HyperoptExample` in the freqtrade-skills repository, /tests).

## Parameters inside indicators (do not do this naively)

Docs warning: hyperopt computes `populate_indicators()` once for all epochs, so a parameter value used there stays at its starting value. Freqtrade logs a warning, and the epoch's result does not match the parameters shown. Two docs-described fixes:

1. `.range`: build one column per possible value, then pick by `.value` in the signal method.

```python
    buy_ema_short = IntParameter(3, 50, default=5)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        for val in self.buy_ema_short.range:
            dataframe[f'ema_short_{val}'] = ta.EMA(dataframe, timeperiod=val)
        return dataframe
```

   (Untested here; docs example.) In hyperopt `.range` holds every value in the interval (48 columns for 3..50); in backtesting and dry/live it holds only the selected value, so never reference a column by an explicit value other than `.value`. `.range` also works for `DecimalParameter` and `CategoricalParameter`, not `RealParameter`. RAM grows with the number of columns and cores.
2. `--analyze-per-epoch`: runs `populate_indicators()` once per epoch, so `.range` only yields the used value. Less RAM, more CPU.

Or move the calculation into `populate_entry_trend()`, which runs every epoch.

## Protections as a space (docs, untested here)

Define `protection_*` or `space="protection"` parameters and return the list from a `protections` property. Selecting the `protection` space turns on `--enable-protections` automatically. Docs warning: if protections are a property, entries in the config are ignored.

## Dynamic parameters (docs, untested here)

Parameters may be created in `bot_start()` (`self.buy_adx = IntParameter(20, 30, default=30, optimize=True)`). They do not show in the `list-strategies` parameter count.

## max_entry_position_adjustment (docs, untested here)

Not a separate space; expose it as a property returning a parameter value (`CategoricalParameter([-1, 0, 1, 3, 5, 10], default=1, space="buy")`; with `IntParameter` return `int(self.max_epa.value)`).
