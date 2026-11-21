# flake8: noqa: F401
from pandas import DataFrame

import talib.abstract as ta
from freqtrade.strategy import IStrategy


class LookaheadBad(IStrategy):
    """Known-bad fixture: RSI shifted -1 peeks at the next candle (lookahead bias)."""

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 0.02}
    stoploss = -0.10
    # Wilder RSI is recursive; 400 candles keep variance well under the 0.5% gate.
    startup_candle_count: int = 400

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14).shift(-1)  # BIAS: future candle
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] < 35) & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] > 65) & (dataframe["volume"] > 0), "exit_long"] = 1
        return dataframe
