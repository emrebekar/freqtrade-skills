# Teaching example for the freqtrade-validation skill. NOT a profitable strategy.
from pandas import DataFrame

import talib.abstract as ta
from freqtrade.strategy import IStrategy


class ValidationExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # EMA/RSI/MACD are recursive: recursive-analysis showed 400 candles is enough (see freqtrade-validation).
    startup_candle_count: int = 400

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)  # docs: signalperiod 1 introduces bias
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        # Windowed statistics only: each row sees its own past, never the whole column.
        dataframe["close_mean_48"] = dataframe["close"].rolling(48).mean()
        dataframe["close_std_48"] = dataframe["close"].rolling(48).std()
        dataframe["zscore_48"] = (dataframe["close"] - dataframe["close_mean_48"]) / dataframe["close_std_48"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["zscore_48"] < -1.5)
                & (dataframe["macd"] > dataframe["macdsignal"])
                & (dataframe["rsi"] < 50)
                & (dataframe["close"] > dataframe["close"].shift(1))  # previous candle only
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "zscore_macd")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            ((dataframe["zscore_48"] > 1.5) & (dataframe["volume"] > 0)),
            ["exit_long", "exit_tag"],
        ] = (1, "zscore_high")
        return dataframe
