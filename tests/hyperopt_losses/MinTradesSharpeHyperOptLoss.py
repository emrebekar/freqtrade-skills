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
