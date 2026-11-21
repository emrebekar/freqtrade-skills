# Test fixture for the freqtrade-migration skill: a deliberately OLD (interface v2) strategy.
# Do not copy it as a starting point; tests/strategies/MigratedV3.py is the migrated version.
from datetime import datetime
from typing import Optional

from pandas import DataFrame

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from technical import qtpylib


class LegacyV2(IStrategy):
    # No INTERFACE_VERSION on purpose: the old default.
    timeframe = "5m"

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10
    startup_candle_count: int = 200

    # Old setting names (renamed in interface v3).
    use_sell_signal = True
    sell_profit_only = False
    sell_profit_offset = 0.0
    ignore_roi_if_buy_signal = False

    order_types = {
        "buy": "limit",
        "sell": "limit",
        "emergencysell": "market",
        "forcesell": "market",
        "forcebuy": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
        "stoploss_on_exchange_interval": 60,
    }
    order_time_in_force = {"buy": "gtc", "sell": "gtc"}
    unfilledtimeout = {"buy": 10, "sell": 10, "unit": "minutes"}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["volume_mean_12"] = dataframe["volume"].rolling(12).mean()
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)
                & (dataframe["close"] < dataframe["bb_lowerband"])
                & (dataframe["volume"] > dataframe["volume_mean_12"])
                & (dataframe["volume"] > 0)
            ),
            "buy",
        ] = 1
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
                & (dataframe["rsi"] < 60)
                & (dataframe["close"] > dataframe["close"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            "buy",
        ] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] > 70)
                & (dataframe["volume"] > 0)
            ),
            ["sell", "exit_tag"],
        ] = (1, "rsi_high")
        return dataframe

    def custom_sell(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        if current_profit > 0.015:
            return "profit_1_5pct"
        return None

    def check_buy_timeout(self, pair: str, trade: Trade, order: dict,
                          current_time: datetime, **kwargs) -> bool:
        return False

    def check_sell_timeout(self, pair: str, trade: Trade, order: dict,
                           current_time: datetime, **kwargs) -> bool:
        return False

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            entry_tag: Optional[str], **kwargs) -> float:
        return proposed_stake

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, sell_reason: str,
                           current_time: datetime, **kwargs) -> bool:
        return True
