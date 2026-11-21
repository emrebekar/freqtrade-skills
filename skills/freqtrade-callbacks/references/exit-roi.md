Source: docs/strategy-callbacks.md#custom-exit-signal
Source: docs/strategy-callbacks.md#custom-roi
Source: docs/includes/strategy-exit-comparisons.md#exit-logic-comparisons

# custom_exit and custom_roi

## custom_exit

Signature as tested (the docs signature has no return annotation):

<!-- tested: tests/strategies/CallbacksExample.py lines 92-96 -->
```python
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        # Close any trade at a loss that has been open for 2 hours or more.
        if current_profit < 0.0 and (current_time - trade.open_date_utc) >= timedelta(hours=2):
            return "unclog"
```

Rules from the docs:

- Called for open trades while they are open (live: every throttling iteration, about 5 s) and asks for a full exit.
- Returning a non-empty string or `True` is the same as setting an exit signal on that candle. The string becomes the exit tag; max 64 characters (longer is truncated). The test backtest showed the returned string as the exit reason (`unclog`, 340 exits), and as the order tag.
- Not called when an exit signal is already set, or when `use_exit_signal=False`.
- Ignores `exit_profit_only`, and is called even when there is a new enter signal.
- Use `custom_stoploss()` for stops; the docs call `custom_exit()` for stoploss "an inferior method" and note that custom stoploss can stay on the exchange.
- Not documented: what `confirm_trade_exit()` receives as `exit_reason` when `custom_exit()` returned a custom string. The docs list the order `exit_signal` / `custom_exit`, then `stop_loss`, `roi`, `trailing_stop_loss`. Log `exit_reason` in your own `confirm_trade_exit()` to find out.

Docs example (not run by the repo tests) uses the last candle for indicator checks:

```python
dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
last_candle = dataframe.iloc[-1].squeeze()
if current_profit > 0.2:
    if last_candle["rsi"] < 80:
        return "rsi_below_80"
```

Docs bug to avoid: in the same example the exit for `0.02 < current_profit < 0.1` is tagged `"ema_long_below_80"`, which does not describe its condition. Use tags that say what happened; the tags show up in backtest results.

## custom_roi

Enable with `use_custom_roi = True`. Not run by the repo tests; everything here is from the docs.

Signature (docs):

```python
def custom_roi(self, pair: str, trade: Trade, current_time: datetime, trade_duration: int,
               entry_tag: str | None, side: str, **kwargs) -> float | None:
```

- Returns a minimum ROI ratio (0.05 = 5%) or `None` to fall back to `minimal_roi`. `NaN` / `inf` are invalid and treated as `None`.
- `trade_duration` is the current trade duration in minutes; `side` is `"long"` or `"short"`.
- If both `minimal_roi` and `custom_roi` apply, the lower threshold triggers the exit. Docs: `minimal_roi = {"0": 0.10}` with `custom_roi` 0.05 exits at 5%; `custom_roi` 0.10 with `minimal_roi = {"0": 0.05}` exits at 5%.
- Docs examples: per side (`0.05` long, `0.02` short), per pair (a dict lookup with default 0.01), per entry tag (`roi_by_tag.get(entry_tag, 0.01)`), ATR ratio (`last_candle["atr"] / last_candle["close"]`).

## Which exit mechanism

Exit signal, `minimal_roi`, stoploss, `custom_exit`, `custom_stoploss` and `custom_roi` interplay; the docs summarize it in the "Exit logic comparisons" include (see freqtrade-strategy references/signals.md for the summary). Before adding a callback, check that `minimal_roi` in the class does not already exit the trade first: in the tested class `minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}` produced only 32 `roi` exits next to 340 `unclog`.
