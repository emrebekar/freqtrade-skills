Source: docs/lookahead-analysis.md#lookahead-analysis-command-reference
Source: docs/lookahead-analysis.md#how-does-the-command-work
Source: docs/lookahead-analysis.md#how-to-find-and-remove-bias-how-can-i-salvage-a-biased-strategy
Source: docs/lookahead-analysis.md#what-do-the-columns-in-the-results-table-mean
Source: docs/lookahead-analysis.md#caveats
Source: docs/commands/lookahead-analysis.md

# lookahead-analysis

Lookahead bias: indicators or signals use data from candles that would not exist yet in dry/live. Backtesting computes the whole dataframe at once, so the bug is invisible there and makes backtests look great. The command chains backtests and pokes at the strategy: it does not read the code, it compares changed indicator values and moved entries/exits against a full backtest.

## How it works

1. A baseline backtest of all pairs creates reference indicators and entries/exits.
2. If the number of trades is below `minimum-trade-amount`, the analysis is cancelled for that strategy. Use a wider timerange or one with more trades.
3. For each entry and each exit (up to the targeted amount) an additional backtest runs on a one-pair pairlist and the dataframes are compared column by column.
4. A result table is printed (and saved with `--lookahead-analysis-exportfilename FILE.csv`).

Forced settings (docs): `--cache none`; `--max-open-trades` at least the number of pairs; dry-run wallet 1 billion; stake amount 10000; protections off; `order_types` forced to market unless `--allow-limit-orders`. The log line `Forced max_open_trades to -1 (same amount as there are pairs)` confirms the first one (observed).

## Options added on top of backtesting (2026.10 help)

| Option | Meaning |
|--------|---------|
| `--minimum-trade-amount INT` | Minimum trade amount for the analysis. |
| `--targeted-trade-amount INT` | Targeted trade amount (how many signals get verified; docs: `total_signals` default 20). |
| `--lookahead-analysis-exportfilename FILE` | Write the result CSV. |
| `--allow-limit-orders` | Do not force market orders. The help warns of false positives. |

Observed log with 248 trades: `Found 248 trades, calculating 20 trades.` A strategy with 13 trades verified 13. In a test with 0 trades the table showed `too few trades caught (0/10).Test failed.` in the `has_bias` cell, so the minimum appears to default to 10 (observed, not documented). `check_results.py` in the repo treats a missing or empty result as failure.

## Result columns

`filename`, `strategy`, `has_bias` (`No` good, `Yes` bad), `total_signals` (checked signals, default 20), `biased_entry_signals`, `biased_exit_signals`, `biased_indicators` (indicator columns from `populate_indicators`; observed to list `enter_long` / `exit_long` too when signals are affected). Biased exits can be false positives that come from biased entries: address entries first, then exits.

Real output, trimmed (fixture `LookaheadBad`: `rsi = ta.RSI(...).shift(-1)`):

```text
┃        filename ┃     strategy ┃ has_bias ┃ total_signals ┃ biased_entry_signals ┃ biased_exit_signals ┃          biased_indicators ┃
│ LookaheadBad.py │ LookaheadBad │      Yes │            20 │                    0 │                   0 │ rsi, enter_long, exit_long │
```

Note: `has_bias` was `Yes` although both signal counts were 0; the indicators column carried the finding. Repo rule (`tests/check_results.py`): biased if either signal count is above 0 or `has_bias` is `True` in the CSV.

## Salvaging a biased strategy

Docs: if you found a biased strategy online and want the same results without bias, you will mostly be out of luck. The bias is usually the driving factor behind "too good to be true" profits, and removing the biased conditions usually makes the strategy much worse. You may salvage it partially if the biased parts are not the core or other signals are unbiased.

## Caveats (docs)

- It can only verify or falsify trades it calculated. Signals that never fired in the tested range are not verified, so a strategy with several signal types can be reported unbiased (false negative). Choose timerange and parameters so each signal fires at least once.
- It uses backtesting options: do not enable position stacking (distorts the number of checked signals). If you do, make sure `max_open_trades` slots and wallet never run out.
- It assumes one-pair backtests behave like the full pairlist. Strategies that depend on the pairlist are reported as biased (false positive): for example `leverage()` or `custom_stake_amount()` using `len(self.dp.current_whitelist())`, or `populate_*` ranking against other pairs; this applies to every strategy method.
- Limit orders with `custom_entry_price()` / `custom_exit_price()` can cause late or delayed entries and false positives. Market orders are forced, so those callbacks are not called. `--allow-limit-orders` skips the override and has "shown to eventually produce false positives".
- FreqAI: supported, but the `biased_indicators` column falsely flags target indicators defined in `set_freqai_targets()`. These are not biased and can be ignored. Ignore only those target columns; treating `&`-prefixed columns as the targets is this repo's gloss, the docs only say "target indicators defined in `set_freqai_targets()`".
- Can also run from freqUI in webserver mode as a background task; only one analysis (lookahead or recursive) runs at a time.

## Repo evidence (tests/test_lookahead_fixtures.sh)

Fixtures in tests/fixtures/strategies/ and the expected results: see the table in SKILL.md. The two false negatives (plain merge, MACD signal period 1) are documented as such: the check is a helper, not a proof. `LookaheadBad` must keep failing in `tests/run_checks.sh`.

## Docs inconsistency

`docs/lookahead-analysis.md` prose names the flag `--lookahead-allow-limit-orders`; the 2026.10 CLI help has `--allow-limit-orders`. The repo CLI checker accepts only the help spelling.
