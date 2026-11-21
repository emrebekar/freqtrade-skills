Source: docs/backtesting.md#assumptions-made-by-backtesting
Source: docs/backtesting.md#trading-limits-in-backtesting
Source: docs/backtesting.md#improved-backtest-accuracy
Source: docs/strategy-customization.md#common-mistakes-when-developing-strategies

# What backtesting assumes

Backtesting cannot see how prices moved inside a candle (was high before low?). These are the docs' assumptions (2026.10); every result is only as good as they are.

## Fills and prices

- Exchange trading limits are respected (limits and precision come from current exchange data, not history; a limit inflated by a historic price can push minimum stakes above 50 USD).
- Entries happen at the candle open unless a custom price is used.
- All orders fill at the requested price, no slippage, as long as the price is inside the candle's high/low range.
- Exit-signal exits happen at the open of the next candle. Exits free their trade slot for a new trade on a different pair.
- Position reversals (futures) happen when an opposite entry signal fires on the candle where the trade closes.

## Order of events in one candle

Evaluation sequence when several things happen on the same candle: exit signal, stoploss, ROI, trailing stoploss. So an exit signal wins over stoploss (signals are assumed to trigger at the open), and stoploss is evaluated before ROI: expect more `stop_loss` exits than in dry-run or live.

- Low is assumed to happen before high for stoploss, protecting capital first.
- Stoploss exits happen exactly at the stoploss price even if low was lower, but the loss is `2 * fees` higher than the stoploss price.
- ROI: compared against high, but the ROI value is used (ROI 2%, high 5% exits at 2%). Exits are never "below the candle", so ROI 2% can exit at 2.4% if low was already 2.4% profit. A ROI step that takes effect on the triggering candle uses the candle open as exit rate. Force-exits from `<N>=-1` ROI entries use low unless N falls on the candle open.
- Trailing stoploss: only adjusted if below the candle's low; high happens first (adjusts the stop), low uses the adjusted stop; on entry candles that trigger it, `stop_positive_offset` is assumed instead of high (not for custom stoploss); ROI applies before trailing stop, so profits are capped at ROI.
- The exit reason does not say whether a trade won or lost (odd with negative ROI values).

## Improved accuracy: `--timeframe-detail`

```bash
freqtrade backtesting --strategy AwesomeStrategy --timeframe 1h --timeframe-detail 5m
```

The strategy runs on the main timeframe. Candles where activity can happen (an active signal, the pair is in a trade) are evaluated on the detail timeframe. Entries still happen at the main candle's open, but trade slots can free earlier, and with several pairs competing for slots results can differ a lot (docs example). All callbacks (`custom_exit()`, `custom_stoploss()` and so on) run on every detail candle once the trade is open (12 times for 1h with 5m detail). The detail timeframe must be smaller than the main one, data for it must be downloaded, and memory and runtime grow. The docs suggest using it as the last part of development to check the strategy is not exploiting the assumptions above. Strategies that perform similarly with it have a good chance of doing so in dry/live (only dry-run confirms).

Verified on 2026.10 (test data, IndicatorsExample, `-i 1h --timeframe-detail 5m`): the run succeeded; no profit conclusions are drawn from it here.

## Other limits

- Backtesting never replaces dry-run; past results do not guarantee future success.
- Dynamic pairlists use today's market, so results are not reproducible; generate a static list with `freqtrade test-pairlist` (docs).
- Not all pairlist handlers work in backtesting.
- Look at the common mistakes (lookahead): backtests use data that would not exist live. See freqtrade-validation.
