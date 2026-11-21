Source: docs/backtesting.md#understand-the-backtesting-result
Source: docs/backtesting.md#backtesting-report-table
Source: docs/backtesting.md#summary-metrics
Source: docs/backtesting.md#daily-weekly-monthly-yearly-breakdown

# Reading the backtest result

Definitions below are the docs' (2026.10). Comments marked "note" are this skill's guidance, not Freqtrade rules.

## Tables, in order

| Table | What it shows |
|-------|---------------|
| Backtesting report | Per-pair trades, avg profit %, total profit (stake currency and % of starting balance), avg duration, wins/draws/losses. Last row `TOTAL` is the overall result. Includes left-open trades. |
| Left open trades | Trades force-exited at the end of the timerange (`force_exit`), also counted in the first table. |
| Enter tag stats | Same columns grouped by entry tag (`enter_tag`). |
| Exit reason stats | Grouped by exit reason (`exit_signal`, `roi`, `stop_loss`, `trailing_stop_loss`, `force_exit`, custom tags). Shows which exit needs work, for example many losing `exit_signal` trades. |
| Mixed tag stats | Entry tag by exit reason. |
| Breakdown (`--breakdown`) | Realized profit per day, week, month, year or weekday with trades, profit factor and win/draw/loss; counted on the day trades closed. |
| Summary metrics | See below. |
| Strategy summary | One row per strategy, with drawdown. |

`Tot Profit %` is relative to the starting balance: (absolute profit / starting balance) * 100. `minimal_roi` and `stoploss` strongly shape the result: a ROI of `{"0": 0.01}` caps every trade near 1%, a very high ROI is almost never reached.

## Summary metrics

- `Backtesting from` / `to`: range, usually from `--timerange`.
- `Trading Mode`: Spot or futures. `Max open trades`: `max_open_trades` or number of pairs, whichever is lower.
- `Total/Daily Avg Trades`: total trades / trades per day.
- `Starting balance`, `Final balance`, `Absolute profit`, `Total profit %`, `CAGR %`.
- `Sharpe`, `Sortino`, `Calmar (closed trades)`: annualized, closed trades only.
- `SQN`: System Quality Number (Van Tharp).
- `Mean profit p-value`: two-sided p-value of a one-sample t-test against zero mean per-trade return; its t-statistic is identical to SQN. Docs: below `0.05` is the usual bar; the test assumes independent identically distributed trades, which real strategies rarely are, so the figure is an optimistic lower bound; because backtesting and hyperopt evaluate many strategies, some score low by chance, so a small value is not proof of an edge.
- `Profit factor`: sum of winning profits / sum of losses.
- `Expectancy (Ratio)`: average profit or loss per trade and its ratio; negative means not profitable.
- `Avg. daily profit`, `Avg. stake amount`.
- `Market change`: average change of all pairs from first to last candle (close).
- `Total trade volume`: exchange volume generated.
- `Long / Short trades`, `Long / Short profit %`, `Long / Short profit USDT`: only shown when short trades were made.
- `Best/Worst Pair`, `Best/Worst trade`, `Best/Worst day`, `Days win/draw/lose`.
- `Min/Max/Avg. Duration Winners` and `Losers`, `Max Consecutive Wins / Loss`.
- `Rejected Entry signals`: signals ignored because `max_open_trades` was reached.
- `Entry/Exit Timeouts`: orders that did not fill (only with custom pricing).
- `Min/Max balance`, `Max % of account underwater`, `Absolute drawdown`, `Drawdown duration`, `Profit at drawdown start/end`, `Drawdown start/end`: for the largest drawdown, based on closed trades.
- Wallet based metrics: the same family including unrealized profit of open trades (`Min/Max balance (wallet balance)`, `Absolute drawdown (wallet balance)`, `Sharpe/Sortino/Calmar (daily wallet balance)`). Docs: more complete because they include capital tied in open trades.

## Honest reading (notes)

- Compare `Total profit %` with `Market change` and with the drawdown. A strategy that makes less than holding in a rising market and still has drawdowns has not shown an edge.
- Look at `Exit Reason Stats` first: which exit loses? Which tag earns? Use `backtesting-analysis` to dig in.
- The docs' FAQ: 12 trades are not enough to say anything; the docs give no threshold. Prefer more trades, several timeranges and market regimes.
- `Rejected Entry signals` counts `max_open_trades` rejections only; in the callbacks tests a `confirm_trade_entry` rejection did not show up there.
- Exit reason does not say if the trade won: with negative ROI values an `roi` exit can be a loss.
