# Teaching example for the freqtrade-strategy skill. NOT a profitable strategy.
# Futures only: needs "trading_mode": "futures" and "margin_mode" in the config.
from datetime import datetime

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy
from technical import qtpylib


class ShortExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = True

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    startup_candle_count: int = 200

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        # Fixed low leverage; values above max_leverage are capped by the bot anyway.
        return min(2.0, max_leverage)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_upperband"] = bollinger["upper"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)
                & (dataframe["close"] < dataframe["bb_lowerband"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_low")
        dataframe.loc[
            (
                (dataframe["rsi"] > 65)
                & (dataframe["close"] > dataframe["bb_upperband"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_short", "enter_tag"],
        ] = (1, "rsi_high")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when RSI returns to 50. Not above 65/below 35: that would collide with
        # the entry signals of the opposite side (enter_short vs exit_long).
        dataframe.loc[
            (qtpylib.crossed_above(dataframe["rsi"], 50) & (dataframe["volume"] > 0)),
            ["exit_long", "exit_tag"],
        ] = (1, "rsi_mid")
        dataframe.loc[
            (qtpylib.crossed_below(dataframe["rsi"], 50) & (dataframe["volume"] > 0)),
            ["exit_short", "exit_tag"],
        ] = (1, "rsi_mid")
        return dataframe
