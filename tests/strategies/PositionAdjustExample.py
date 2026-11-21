# Teaching example for the freqtrade-callbacks skill. NOT a profitable strategy.
from pandas import DataFrame

import talib.abstract as ta
from datetime import datetime

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from technical import qtpylib


class PositionAdjustExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    position_adjustment_enable = True
    # One extra entry per trade, on top of the first entry order.
    max_entry_position_adjustment = 1

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
                & (dataframe["rsi"] < 60)
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "ema_cross")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] > 70)
                & (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "rsi_high")
        return dataframe

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: float | None, max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> float | None | tuple[float | None, str | None]:
        if trade.has_open_orders:
            # Only act if no orders are open
            return None

        if current_profit > 0.005 and trade.nr_of_successful_exits == 0:
            # Take half of the position off at +0.5% (negative stake = partial exit)
            return -(trade.stake_amount / 2), "half_profit"

        if current_profit < -0.01 and trade.nr_of_successful_entries == 1:
            # One DCA add, same size as the first entry
            filled_entries = trade.select_filled_orders(trade.entry_side)
            return filled_entries[0].stake_amount_filled, "dca_1"

        return None
