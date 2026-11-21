# flake8: noqa: F401
# Known-bad fixture for the freqtrade-validation skill: ta.MACD signalperiod 1 (docs say it introduces bias; NOT flagged here: known false negative).
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy

class LookaheadBadMacd1(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 0.02}
    stoploss = -0.10
    startup_candle_count: int = 400

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["macd"] = ta.MACD(dataframe, 12, 26, 1)["macd"]
        dataframe["macdhist"] = ta.MACD(dataframe, 12, 26, 1)["macdhist"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] < 35) & (dataframe["macd"] < 0) & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] > 65) & (dataframe["volume"] > 0), "exit_long"] = 1
        return dataframe
