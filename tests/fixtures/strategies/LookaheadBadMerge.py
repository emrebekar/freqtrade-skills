# flake8: noqa: F401
# Known-bad fixture for the freqtrade-validation skill: plain pd.merge of a 1h frame onto 5m (biased by the docs, but NOT flagged by lookahead-analysis: known false negative).
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy

class LookaheadBadMerge(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 0.02}
    stoploss = -0.10
    startup_candle_count: int = 400

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        inf = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe="1h")
        inf["rsi_1h"] = ta.RSI(inf, timeperiod=14)
        dataframe = pd.merge(dataframe, inf[["date", "rsi_1h"]], on="date", how="left").ffill()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] < 35) & (dataframe["rsi_1h"] < 60) & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] > 65) & (dataframe["volume"] > 0), "exit_long"] = 1
        return dataframe
