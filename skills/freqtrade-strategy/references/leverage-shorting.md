Source: docs/leverage.md#shorting
Source: docs/leverage.md#understand-trading_mode
Source: docs/leverage.md#margin-mode
Source: docs/leverage.md#set-leverage-to-use
Source: docs/leverage.md#understand-liquidation_buffer
Source: docs/exchanges.md#binance-futures
Source: docs/strategy-customization.md#can-short
Source: docs/strategy-callbacks.md#leverage-callback

# Shorting and leverage

Real money warning: leverage multiplies losses and can liquidate a position to 0. The docs advise not to use leverage above 1 with a strategy that has not shown positive results on spot, and not to run two bots on one account with leverage.

## Config required

Shorting is impossible on `spot`. The config needs futures mode and a margin mode (`margin` mode is currently unavailable):

```json
"trading_mode": "futures",
"margin_mode": "isolated"
```

- `margin_mode`: `isolated` (collateral per pair) or `cross` (shared collateral; higher risk of full-account liquidation, and cross-position influence may not be fully simulated in dry-run or backtesting).
- Futures pairs are written `base/quote:settle`, e.g. `ETH/USDT:USDT`.
- Binance futures need `use_order_book: true` in `entry_pricing`/`exit_pricing` (see freqtrade-config). The repo's [`tests/config.futures.json`](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/config.futures.json) is a working example.
- Futures backtesting needs futures candles plus mark and funding-rate data. If funding rates are unavailable for the timerange you can set `futures_funding_rate` (recommended `0`), which makes backtests less accurate.
- Download futures data with the setup skill's data commands (`--trading-mode futures`).

## Strategy requirements

- `can_short = True` as a class attribute. Default `False`: `enter_short` signals are then ignored, even on futures. Strategies with `can_short = True` fail to load on spot.
- `enter_short` / `exit_short` columns alongside `enter_long`. `enter_long` must exist even for short-only strategies.
- Optional `leverage()` callback. Without it, leverage is 1x. Values above `max_leverage` are capped to `max_leverage`. Only called in futures mode.

## Tested example: ShortExample

Source file: ShortExample. Passes backtesting, `lookahead-analysis` and `recursive-analysis` with [`tests/config.futures.json`](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/config.futures.json). A backtest of it opened both long and short trades, all at leverage 2.0. It is a teaching strategy and loses money on the test data.

<!-- tested: tests/strategies/ShortExample.py lines 15-27 -->
```python
    timeframe = "5m"
    can_short = True

    minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}
    stoploss = -0.10

    startup_candle_count: int = 200

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        # Fixed low leverage; values above max_leverage are capped by the bot anyway.
        return min(2.0, max_leverage)
```

The signals of this strategy are in signals.md (section "Short signals").

## Leverage and risk

- All profit calculations, stoploss and ROI include leverage: stake 100 at 3x is a 300 position, and a 10% stoploss at 10x triggers on a 1% move.
- Choose a stoploss that triggers well before liquidation. Do not reason it out by hand: compare `trade.liquidation_price` with the stop price (`trade.stop_loss`) on a real or dry-run trade.
- Docs conflict: leverage.md (danger box) says "With a leverage of 2, a stoploss of 0.5 (50%) would be too low, and these trades would be liquidated before reaching that stoploss", while strategy-callbacks.md and stoploss.md describe a leverage-adjusted stoploss (at 10x, -0.1 triggers on a 1% move). Do not reason it out. After a backtest or dry run, compare `trade.liquidation_price` with the stop price and keep the stop well inside liquidation.
- `liquidation_buffer` (default `0.05`) puts a safety margin between the liquidation price and the stoploss: `freqtrade_liquidation_price = liquidation_price +/- (abs(open_rate - liquidation_price) * liquidation_buffer)` (+ for long, - for short). Setting it to 0 or very low likely causes liquidations and liquidation fees, which freqtrade does not track; use `stoploss_on_exchange` then if supported.
- `liquidation_warn_ratio` (default `0.2`, `0` disables) sends a best-effort notification near the liquidation stop. It does not replace a stoploss.
- Isolated margin: adding funds to the account does not move an isolated position's liquidation stop.
- A callback must not depend on the pairlist length (for example `len(self.dp.current_whitelist())` in `leverage()`): `lookahead-analysis` backtests one pair at a time and would report a false positive.

## Leverage callback signature (docs)

```python
def leverage(self, pair: str, current_time: datetime, current_rate: float,
             proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
             **kwargs) -> float:
```

`side` is `"long"` or `"short"`. Return a value between 1.0 and `max_leverage`. Per-pair or per-tag leverage is allowed; the tested example returns a fixed `min(2.0, max_leverage)`.
