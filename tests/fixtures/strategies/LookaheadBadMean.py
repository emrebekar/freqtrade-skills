# flake8: noqa: F401
# Known-bad fixture for the freqtrade-validation skill: whole-column .mean() (expected: lookahead-analysis flags it).
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy

class LookaheadBadMean(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 0.02}
    stoploss = -0.10
    startup_candle_count: int = 400

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["vol_mean"] = dataframe["volume"].mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] < 35) & (dataframe["volume"] > dataframe["vol_mean"]) & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] > 65) & (dataframe["volume"] > 0), "exit_long"] = 1
        return dataframe
