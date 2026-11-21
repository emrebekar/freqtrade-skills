# Teaching example for the freqtrade-callbacks skill. NOT a profitable strategy.
import logging
from datetime import datetime, timedelta

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, stoploss_from_open
from technical import qtpylib

logger = logging.getLogger(__name__)


class CallbacksExample(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10
    use_custom_stoploss = True

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["rsi"] < 35)
                & (dataframe["close"] < dataframe["bb_lowerband"])
                & (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "rsi_bb_low")
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
                & (dataframe["rsi"] < 60)
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

    def bot_start(self, **kwargs) -> None:
        logger.info("CALLBACK bot_start")

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        # Fires once per candle in backtesting: log only the first one.
        if not getattr(self, "_loop_logged", False):
            self._loop_logged = True
            logger.info("CALLBACK bot_loop_start first call at %s", current_time)

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            leverage: float, entry_tag: str | None, side: str,
                            **kwargs) -> float:
        # Half stake for the crossover entries, default stake for the rest.
        if entry_tag == "ema_cross":
            return proposed_stake / 2
        return proposed_stake

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        # Refuse entries during the first hour (UTC) of the day. Arbitrary rule, for demonstration.
        if current_time.hour == 0:
            logger.info("CALLBACK confirm_trade_entry rejected %s at %s", pair, current_time)
            return False
        return True

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        # Close any trade at a loss that has been open for 2 hours or more.
        if current_profit < 0.0 and (current_time - trade.open_date_utc) >= timedelta(hours=2):
            return "unclog"

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float | None:
        # Once 1% in profit, lock the stop at 0.5% above the open price (never moves down).
        if current_profit > 0.01:
            return stoploss_from_open(0.005, current_profit, is_short=trade.is_short, leverage=trade.leverage)
        # Otherwise trail 4% behind the current price.
        return -0.04 * trade.leverage
