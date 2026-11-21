# Teaching example for the freqtrade-strategy skill. NOT a profitable strategy.
from pandas import DataFrame

import talib.abstract as ta
from freqtrade.strategy import IStrategy
from technical import qtpylib


class IndicatorsExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["volume_mean_12"] = dataframe["volume"].rolling(12).mean()  # rolling, not .mean()
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)  # Signal: oversold
                & (dataframe["close"] < dataframe["bb_lowerband"])  # Guard: below lower band
                & (dataframe["volume"] > dataframe["volume_mean_12"])
                & (dataframe["volume"] > 0)  # Make sure Volume is not 0
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_bb_low")
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])  # Signal
                & (dataframe["rsi"] < 60)  # Guard: keeps it away from the exit signal below
                & (dataframe["close"] > dataframe["close"].shift(1))  # previous candle: shift(1), never shift(-1)
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
