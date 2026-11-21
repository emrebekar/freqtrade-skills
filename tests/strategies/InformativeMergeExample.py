# Teaching example for the freqtrade-strategy skill. NOT a profitable strategy.
# Pattern 2: DataProvider + merge_informative_pair (see InformativeExample.py for the decorator).
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair


class InformativeMergeExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    # RSI is recursive; 200 main candles cover the 1h RSI as well (recursive-analysis checked).
    startup_candle_count: int = 200

    inf_tf = "1h"

    def informative_pairs(self):
        # Download and cache the informative timeframe for every whitelisted pair.
        return [(pair, self.inf_tf) for pair in self.dp.current_whitelist()]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.inf_tf)
        informative["rsi"] = ta.RSI(informative, timeperiod=14)
        # Renames the columns to rsi_1h etc. and merges without lookahead bias.
        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.inf_tf, ffill=True
        )
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
