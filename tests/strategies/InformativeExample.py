# Teaching example for the freqtrade-strategy skill. NOT a profitable strategy.
# Pattern 1: the @informative decorator (see InformativeMergeExample.py for merge_informative_pair).
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, informative


class InformativeExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # RSI is recursive; 200 main candles cover the 1h RSI as well (recursive-analysis checked).
    startup_candle_count: int = 200

    # Available in populate_indicators and later as "rsi_1h".
    # Method names must be unique across all @informative methods.
    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)
                & (dataframe["rsi_1h"] < 50)  # Guard: higher timeframe not overbought
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_5m_and_1h")
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
