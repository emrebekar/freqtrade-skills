Source: docs/advanced-hyperopt.md#creating-and-using-a-custom-loss-function
Source: docs/hyperopt.md#loss-functions
Source: docs/utils.md#list-hyperopt-loss-functions
Source: docs/commands/list-hyperoptloss.md

# Custom loss function

A custom loss is a class that subclasses `IHyperOptLoss` and defines the static method `hyperopt_loss_function`. Select it with `--hyperopt-loss ClassName` (or `"hyperopt_loss"` in the config). Docs: the class lives in its own file in `user_data/hyperopts/` (or in a directory given with `--hyperopt-path PATH`). It is called once per epoch, so keep it fast. It must return a `float`; smaller is better.

## Signature (verbatim from the docs, 2026.10)

```python
from datetime import datetime
from typing import Any, Dict

from pandas import DataFrame

from freqtrade.constants import Config
from freqtrade.optimize.hyperopt import IHyperOptLoss

TARGET_TRADES = 600
EXPECTED_MAX_PROFIT = 3.0
MAX_ACCEPTED_TRADE_DURATION = 300

class SuperDuperHyperOptLoss(IHyperOptLoss):
    """
    Defines the default loss function for hyperopt
    """

    @staticmethod
    def hyperopt_loss_function(
        *,
        results: DataFrame,
        trade_count: int,
        min_date: datetime,
        max_date: datetime,
        config: Config,
        processed: dict[str, DataFrame],
        backtest_stats: dict[str, Any],
        starting_balance: float,
        **kwargs,
    ) -> float:
        """
        Objective function, returns smaller number for better results
        This is the legacy algorithm (used until now in freqtrade).
        Weights are distributed as follows:
        * 0.4 to trade duration
        * 0.25: Avoiding trade loss
        * 1.0 to total profit, compared to the expected value (`EXPECTED_MAX_PROFIT`) defined above
        """
        total_profit = results['profit_ratio'].sum()
        trade_duration = results['trade_duration'].mean()

        trade_loss = 1 - 0.25 * exp(-(trade_count - TARGET_TRADES) ** 2 / 10 ** 5.8)
        profit_loss = max(0, 1 - total_profit / EXPECTED_MAX_PROFIT)
        duration_loss = 0.4 * min(trade_duration / MAX_ACCEPTED_TRADE_DURATION, 1)
        result = trade_loss + profit_loss + duration_loss
        return result
```

Docs example problems (observed by reading, the class itself was not run): it calls `exp()` but imports no `exp` (add `from math import exp`), it imports `Dict` but uses `dict[...]`, and it calls itself "identical to the Default Hyperopt loss implementation" while the 2026.10 loader lists `DefaultHyperOptLoss` and `ShortTradeDurHyperOptLoss` as separate names from the same file. Copy the signature, not the body.

## Arguments (docs)

- `results`: DataFrame of trades. Columns: `pair, profit_ratio, profit_abs, open_date, open_rate, fee_open, close_date, close_rate, fee_close, amount, trade_duration, is_open, exit_reason, stake_amount, min_rate, max_rate, stop_loss_ratio, stop_loss_abs`.
- `trade_count`: number of trades (`len(results)`).
- `min_date`, `max_date`: start and end of the timerange used. (The docs list `min_date` twice; the second entry describes the end date.)
- `config`: config object. Not all strategy parameters in a hyperopt space are updated in it.
- `processed`: dict of DataFrames (pair to data) used for backtesting.
- `backtest_stats`: statistics in the format of the backtest file's "strategy" substructure; fields in `generate_strategy_stats()` in `optimize_reports.py`.
- `starting_balance`: starting balance used.

Keep `*` (keyword-only) and `**kwargs` in the signature: docs say they allow the interface to be extended.

## Tested example

A small custom loss (repo example, not a recommendation): epochs with fewer than `MIN_TRADES` trades get a large loss, otherwise the negated per-trade Sharpe-like ratio.

<!-- tested: tests/hyperopt_losses/MinTradesSharpeHyperOptLoss.py lines 1-33 -->
```python
# Teaching example for the freqtrade-hyperopt skill (custom loss). NOT a recommended objective.
from datetime import datetime
from typing import Any

from pandas import DataFrame

from freqtrade.constants import Config
from freqtrade.optimize.hyperopt import IHyperOptLoss

MIN_TRADES = 20
TOO_FEW_TRADES_LOSS = 1000.0


class MinTradesSharpeHyperOptLoss(IHyperOptLoss):
    """Per-trade Sharpe-like ratio; epochs with fewer than MIN_TRADES trades get a large loss."""

    @staticmethod
    def hyperopt_loss_function(
        *,
        results: DataFrame,
        trade_count: int,
        min_date: datetime,
        max_date: datetime,
        config: Config,
        processed: dict[str, DataFrame],
        backtest_stats: dict[str, Any],
        starting_balance: float,
        **kwargs,
    ) -> float:
        if trade_count < MIN_TRADES:
            return TOO_FEW_TRADES_LOSS
        returns = results["profit_ratio"]
        return -returns.mean() / (returns.std() + 1e-9)  # smaller is better, so negate
```

Run (the docs import `from freqtrade.optimize.hyperopt import IHyperOptLoss` worked in 2026.10):

```bash
freqtrade hyperopt --strategy HyperoptExample --hyperopt-path tests/hyperopt_losses --hyperopt-loss MinTradesSharpeHyperOptLoss --spaces buy sell -e 5 -j 1 --random-state 42
```

Observed with 5 epochs on test data: objectives 0.22, 0.058, 0.099, 0.22, 0.13 and the lowest (0.058, epoch 2) still had total profit -0.79%. "Best objective" never means "profitable". A loss that ignores drawdown or trade count can reward a lucky few trades; one that rewards trade count can reward many small losing trades. Check the epoch's full line in `hyperopt-list`, not only the objective.

`list-hyperoptloss` shows load problems (docs: LOAD FAILED in red, DUPLICATE NAME in yellow). Observed: `list-hyperoptloss --hyperopt-path tests/hyperopt_losses` did NOT list the class that `hyperopt --hyperopt-path tests/hyperopt_losses` loaded and ran fine; so a missing entry in that list does not prove the class will not load. Put the file in `<userdir>/hyperopts/` (docs location) to see it listed (untested here).
