# Teaching example for the freqtrade-hyperopt skill. NOT a profitable strategy.
from functools import reduce

from pandas import DataFrame

import talib.abstract as ta
from freqtrade.strategy import BooleanParameter, DecimalParameter, IntParameter, IStrategy


class HyperoptExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # EMA/RSI are recursive; 400 candles passed recursive-analysis for the sibling ValidationExample.
    startup_candle_count: int = 400

    # Hyperoptable parameters. Names start with buy_/sell_, so the space is implied; space= is explicit anyway.
    buy_rsi = IntParameter(20, 50, default=40, space="buy")
    buy_zscore = DecimalParameter(-2.5, -0.5, decimals=1, default=-1.5, space="buy")
    buy_rsi_enabled = BooleanParameter(default=True, space="buy")
    sell_zscore = DecimalParameter(0.5, 2.5, decimals=1, default=1.5, space="sell")
    sell_rsi = IntParameter(50, 80, default=60, space="sell", optimize=False)  # fixed: not searched

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Fixed indicators only: parameter values must not be used here (hyperopt computes this once for all epochs).
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["close_mean_48"] = dataframe["close"].rolling(48).mean()
        dataframe["close_std_48"] = dataframe["close"].rolling(48).std()
        dataframe["zscore_48"] = (dataframe["close"] - dataframe["close_mean_48"]) / dataframe["close_std_48"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            dataframe["zscore_48"] < self.buy_zscore.value,
            dataframe["volume"] > 0,
        ]
        if self.buy_rsi_enabled.value:
            conditions.append(dataframe["rsi"] < self.buy_rsi.value)
        dataframe.loc[reduce(lambda x, y: x & y, conditions), ["enter_long", "enter_tag"]] = (1, "zscore_rsi")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["zscore_48"] > self.sell_zscore.value) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "zscore_high")
        return dataframe
