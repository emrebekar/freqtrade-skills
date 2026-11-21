Source: docs/strategy-callbacks.md#stake-size-management
Source: docs/strategy-callbacks.md#adjust-trade-position
Source: docs/strategy-callbacks.md#position-adjust-calculations
Source: docs/strategy-callbacks.md#leverage-callback

# Stake size, position adjustment, leverage

## custom_stake_amount

Called before entering a trade (live and backtesting; in bot-basics order it comes after `leverage()` and before `confirm_trade_entry()`).

<!-- tested: tests/strategies/CallbacksExample.py lines 74-81 -->
```python
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            leverage: float, entry_tag: str | None, side: str,
                            **kwargs) -> float:
        # Half stake for the crossover entries, default stake for the rest.
        if entry_tag == "ema_cross":
            return proposed_stake / 2
        return proposed_stake
```

Docs:

- The returned value is clamped to the supported range and the clamp is logged; you do not have to ensure `min_stake <= value <= max_stake`.
- Returning `0` or `None` prevents the trade.
- If your code raises, freqtrade falls back to `proposed_stake` and logs the exception.
- Using `stake_amount: "unlimited"` with DCA requires implementing this callback so all funds do not go into the first order.

Test result: `ema_cross` trades had stake about 50 USDT, `rsi_bb_low` about 100 USDT (config `stake_amount` 100).

## adjust_trade_position

Enable with `position_adjustment_enable = True` (off by default for performance; freqtrade warns at startup when on). `max_entry_position_adjustment` limits additional entries per trade on top of the first entry order; default -1 means no limit.

Class attributes as tested:

<!-- tested: tests/strategies/PositionAdjustExample.py lines 21-26 -->
```python
    position_adjustment_enable = True
    # One extra entry per trade, on top of the first entry order.
    max_entry_position_adjustment = 1

    # EMA is recursive: 200 candles is chosen via recursive-analysis for EMA50.
    startup_candle_count: int = 200
```

The callback as tested (signature copied from the docs):

<!-- tested: tests/strategies/PositionAdjustExample.py lines 55-75 -->
```python
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: float | None, max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs
                              ) -> float | None | tuple[float | None, str | None]:
        if trade.has_open_orders:
            # Only act if no orders are open
            return None

        if current_profit > 0.005 and trade.nr_of_successful_exits == 0:
            # Take half of the position off at +0.5% (negative stake = partial exit)
            return -(trade.stake_amount / 2), "half_profit"

        if current_profit < -0.01 and trade.nr_of_successful_entries == 1:
            # One DCA add, same size as the first entry
            filled_entries = trade.select_filled_orders(trade.entry_side)
            return filled_entries[0].stake_amount_filled, "dca_1"

        return None
```

Return convention (docs):

- Positive number: extra entry, stake amount in stake currency, before leverage, between `min_stake` and `max_stake` (long trade: buy; short trade: sell). Above `max_stake` (not enough funds) the signal is ignored. Additional entries beyond `max_entry_position_adjustment` are ignored, but the callback is still called for partial exits.
- Negative number: partial exit. `-trade.stake_amount` closes the full position; a larger magnitude is ignored. Amount sold = `negative_stake_amount * trade.amount / trade.stake_amount`; it ignores current profit/loss.
- `None`: no action.
- A 2-tuple `(stake, "tag")` attaches an order tag (for example `return 250, "increase_favorable_conditions"`).
- The callback is also called while an order is open and will cancel that order to place a new one if amount, price or direction differ; partially filled orders are cancelled and replaced. Guard with `trade.has_open_orders` as the example does.
- `trade.stake_amount` is updated on every extra entry and partial exit. Leverage cannot be changed.
- Additional orders cost extra fees and do not count towards `max_open_trades`.

Docs warnings:

- Loose logic repeats every `throttle_process_secs` (5 s) live until funds run out, the limit is hit or the condition ends. Check the last filled order or open orders.
- Backtesting calls it once per candle (or detail candle), live can adjust several times per candle, so results can deviate.
- Stoploss: the docs say it is still calculated from the initial opening price, not the averaged price, and cannot move down; `custom_stoploss(after_fill=True)` can widen it (see references/stoploss.md for the docs conflict). `/stopentry` does not stop position adjustment on existing trades.
- Many adjustments per trade increase memory use.
- Entry rates are weighted averages; exits do not change the average entry rate; final exit profit is relative to total invested capital (docs "Calculation example").

Test evidence: 24 of 95 trades had two entry orders (order tag `dca_1`), 20 trades had a partial exit (`half_profit`). Checked by reading the exported trades (`trades[].orders[]`, counting orders with `ft_is_entry` true).

Doc example (not run by the repo tests): `DigDeeperStrategy` scales the first stake with `custom_stake_amount` (`proposed_stake / self.max_dca_multiplier`) to leave room for DCA, takes half the position at +5% (`return -(trade.stake_amount / 2), "half_profit_5%"`), and buys increasingly larger amounts when profit is below -5% and the last candle is not falling. Its `max_dca_multiplier = 5.5` is tied to `max_entry_position_adjustment = 3` (1 + 1.25 + 1.5 + 1.75); change them together.

## leverage

Futures/margin only; ignored for markets without leverage. Values above `max_leverage` are lowered to `max_leverage`. Signature (docs):

```python
def leverage(self, pair: str, current_time: datetime, current_rate: float,
             proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
             **kwargs) -> float:
```

Docs: "This method is only called in futures mode"; default is 1 (no leverage). Profit, stoploss and ROI all include leverage: a 10% stoploss at 10x triggers on a 1% move. A working `leverage()` example that runs in the futures config is in freqtrade-strategy references/leverage-shorting.md ([tests/strategies/ShortExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/ShortExample.py)).
