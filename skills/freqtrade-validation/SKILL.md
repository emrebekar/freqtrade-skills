---
name: freqtrade-validation
description: Use when you need to check a Freqtrade strategy for lookahead bias or recursive-indicator problems, decide whether a strategy may go to dry-run, or fix a failed lookahead-analysis or recursive-analysis. Covers lookahead-analysis (--minimum-trade-amount, --targeted-trade-amount, result columns, caveats), recursive-analysis (--startup-candle, reading variance tables, startup_candle_count), a fix catalog (shift(-1), whole-dataframe statistics, iloc in populate, resample, merge, MACD signal period 1), the FreqAI exception, and the gate before backtest or hyperopt results count.
license: GPL-3.0
---

# Freqtrade validation (safety gate)

Every other freqtrade skill routes here. A strategy is not "done", and its backtest or hyperopt numbers do not count, until `lookahead-analysis` and `recursive-analysis` pass. Freqtrade version assumed: 2026.10. Users trade real money: be strict, and never overstate what a pass proves.

Rules:
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives (docs: "not biased and can safely be ignored"). That is the only blanket exception. Pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives (see the interpretation table); each must be explained to the user, never silently ignored.
- A pass is not proof. The docs: both commands are helpers that find the most common problems, and a negative result does not guarantee there are none. They only check what happened in the tested timerange. Say so in the report.
- Fix the cause, never the check: do not lower the thresholds, shorten the timerange to avoid trades, or remove a flagged signal from the check. Do not change strategy logic just to silence a flag without understanding it.
- Keep `dry_run: true`. Live trading is the user's separate, explicit decision.
- Hyperopt and backtest results from a strategy that has not passed are unreliable. Biased profits are usually the reason for "too good to be true" results (docs).

## Workflow

1. Prerequisites: the strategy loads (`freqtrade list-strategies`), data is downloaded for the whole timerange plus startup candles (freqtrade-setup), and a plain backtest runs with trades (freqtrade-backtesting).
2. Run `lookahead-analysis` (below). Use a timerange long enough to produce many trades.
3. Read the table (below). If `has_bias` is `Yes`, go to step 5 (fix). If the command reports too few trades there is no verdict: widen the timerange and re-run.
4. Run `recursive-analysis` (below) and read the variance table.
5. Fix with references/fix-catalog.md: entries first, then exits, then indicators. Re-run both checks after every change, because a fix can move signals.
6. Repeat until both pass on the same strategy file and timerange you will backtest.
7. Only then: trust backtest results, run hyperopt, and suggest a dry run. Re-run both checks after any later change to indicators, signals or `startup_candle_count`.

## lookahead-analysis

```bash
freqtrade lookahead-analysis --strategy MyStrategy --timerange 20260801-20261001
freqtrade lookahead-analysis --strategy MyStrategy --timerange 20260801-20261001 --minimum-trade-amount 10 --targeted-trade-amount 20 --lookahead-analysis-exportfilename lookahead.csv
```

It runs a baseline backtest of all pairs, then re-runs a slice per entry and per exit signal on a one-pair pairlist and compares indicator values and moved entries/exits against the baseline. It does not read your code. It accepts the usual backtesting options but forces: `--cache none`, `--max-open-trades` at least the number of pairs, a 1 billion wallet, a static stake of 10000, protections off and market orders (so `custom_entry_price()` and `custom_exit_price()` are not called) unless `--allow-limit-orders` is given (the docs prose spells it `--lookahead-allow-limit-orders`; the 2026.10 help says `--allow-limit-orders`, which is what the CLI check accepts; limit orders can cause false positives).

Trade counts: `--targeted-trade-amount` is how many signals are verified (the docs' column `total_signals` defaults to 20), `--minimum-trade-amount` is the least acceptable (the help text gives no default; in a test the message read "too few trades caught (0/10)", so it appears to be 10). With fewer trades than the minimum the analysis is cancelled for that strategy: use a wider or busier timerange, or lower the minimum knowingly.

Columns: `has_bias` (`No` is good, `Yes` is bad), `total_signals`, `biased_entry_signals`, `biased_exit_signals`, `biased_indicators` (columns from `populate_indicators`, observed to include `enter_long` / `exit_long` when signals are biased). Fix entries first; biased exits may be a consequence of biased entries (docs). A bias can show only in `biased_indicators` with 0 biased signals.

Real output on a known-bad fixture, trimmed ([tests/fixtures/strategies/LookaheadBad.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/fixtures/strategies/LookaheadBad.py): `ta.RSI(...).shift(-1)`, test data, 2026-08-01 to 2026-10-01):

```text
┃        filename ┃     strategy ┃ has_bias ┃ total_signals ┃ biased_entry_signals ┃ biased_exit_signals ┃          biased_indicators ┃
│ LookaheadBad.py │ LookaheadBad │      Yes │            20 │                    0 │                   0 │ rsi, enter_long, exit_long │
```

The log line behind it: `found look ahead bias in column rsi. 29.66475411745386 != nan`. A clean strategy ([tests/strategies/ValidationExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/ValidationExample.py)) printed `has_bias No`, `total_signals 13`, nothing in the other columns.

What the checks catch and miss (repo tests, test data; run [`tests/test_lookahead_fixtures.sh`](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/test_lookahead_fixtures.sh)):

| Pattern (fixture) | `lookahead-analysis` result |
|-------------------|-----------------------------|
| `shift(-1)` on RSI (`LookaheadBad`) | flagged |
| whole-column `.mean()` (`LookaheadBadMean`) | flagged |
| whole-column mean/std z-score (`LookaheadBadZscore`) | flagged |
| `.iloc[-1]` in `populate_indicators` (`LookaheadBadIloc`) | flagged |
| `resample()` mapped back with the left bucket edge (`LookaheadBadResample`) | flagged |
| plain `pd.merge` of a 1h frame onto 5m (`LookaheadBadMerge`) | NOT flagged (false negative) |
| `ta.MACD(df, 12, 26, 1)` (`LookaheadBadMacd1`) | NOT flagged in this test (docs list it as biased) |

So a clean result never replaces reading the code against references/fix-catalog.md. More on caveats: references/lookahead.md.

## recursive-analysis

```bash
freqtrade recursive-analysis --strategy MyStrategy --timerange 20260801-20261001 -p BTC/USDT
freqtrade recursive-analysis --strategy MyStrategy --timerange 20260801-20261001 -p BTC/USDT --startup-candle 30 100 200 499
```

It calculates indicators (not trades) on data of different lengths and compares the last row's values with a benchmark from the full range. Recursive indicators (EMA, RSI, ATR, anything that uses previous values) depend on how many candles you feed them, so live (limited by the exchange) can differ from backtesting. Use one pair with a high price and moderate volatility (BTC or ETH) and a long timerange (docs: at least 5000 candles; 18 days on 5m). It also runs a simple lookahead check on indicator values. It only calculates `populate_indicators` and `@informative` methods: an indicator computed in `populate_entry_trend` or `populate_exit_trend` is not checked.

Real output, trimmed ([tests/strategies/IndicatorsExample.py](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/strategies/IndicatorsExample.py), `startup_candle_count = 200`, test data):

```text
┃     Indicators ┃      30 ┃     100 ┃ 200 (from strategy) ┃     499 ┃
│            rsi │  1.504% │ -0.013% │             -0.000% │       - │
│       ema_fast │ -0.000% │  0.000% │              0.000% │       - │
│       ema_slow │    nan% │  0.013% │             -0.000% │  0.000% │
│ volume_mean_12 │ -0.000% │       - │                   - │       - │
```

Reading it: columns are `startup_candle_count` values (the strategy's own is marked `(from strategy)`; without `--startup-candle` the run used 199, 399, the strategy's value, 499, 999 and 1999 in our test). Cells are the variance of the indicator versus the benchmark. `-` is zero variance, `nan%` means too few candles to calculate (here `ema_slow` with 30 candles). Judge each indicator at your strategy's column: the variance must be small enough that it cannot change entries or exits. The docs give no numeric limit and say zero is not always the best option (some indicators would need a very long startup). This repo's checks fail above 0.5% at the strategy's own column: that is a repo choice, not a Freqtrade rule. If the strategy's column is too high, raise `startup_candle_count` and re-run (not the tolerance). The docs say the default values are odd numbers on purpose and that on Binance the largest usable `startup_candle_count` is 4999 (5 calls of 1000 candles); more candles also mean more startup time and API calls (we saw a warning at 1999).

Observed: on `LookaheadBad` the command printed no result table at all ([tests/run_checks.sh](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/run_checks.sh) reports "no result table found"). Fix lookahead bias first, then re-run recursive-analysis. Details: references/recursive.md.

## Interpreting and deciding

| Observation | Meaning | Action |
|-------------|---------|--------|
| `has_bias` Yes, biased entry signals | Entry reads future data | Fix catalog, entries first |
| `has_bias` Yes, only `biased_indicators` | An indicator column differs on slices | Find that column in `populate_indicators` |
| biased exits only | Often follows biased entries | Fix entries, re-run |
| "too few trades caught" | Not enough trades, no verdict | Widen timerange, add pairs, loosen conditions for the test |
| Flag on `&` columns with FreqAI | Docs: false positive in `set_freqai_targets()`. Repo-observed: FreqAI outputs `do_predict`, `DI_values`, `enter_long`, `enter_short`, `exit_long`, `exit_short`, `enter_tag`, `exit_tag` are flagged too (only `do_predict`, `enter_long`, `exit_long`, `enter_tag`, `exit_tag` observed); a leaky `%` feature is not flagged at all (see freqtrade-freqai) | Ignore `&` targets, and those outputs only when an `&` column is also flagged and biased entry/exit signals are 0; any other column (even one computed from predictions) is a finding; review feature, entry/exit code by hand (repo gloss) |
| Flag only with `len(self.dp.current_whitelist())` or pair ranking | Verification runs one pair alone: false positive per docs | Do not depend on the pairlist in strategy methods, or explain it |
| Flag with limit orders and `custom_entry_price()` | Docs: can cause late entries and false positives | Check with the default market orders |
| Recursive variance above your limit at the strategy's column | Too few startup candles | Raise `startup_candle_count` |
| Everything clean | No problem found in tested signals; not a proof | Read the code against the catalog, then dry-run |

## Validation gate

Before reporting the strategy as done, show the user the actual outputs of:

1. `lookahead-analysis`: `has_bias` No, no biased signals or indicators (the only blanket docs exception is FreqAI `set_freqai_targets()` columns; for FreqAI the repo also accepts FreqAI's own outputs, exact list in freqtrade-freqai, only when an `&` column is flagged and biased entry/exit signals are 0; pairlist-dependent logic and limit orders with `custom_*_price` can also give documented false positives, each explained, never silently ignored), enough trades verified.
2. `recursive-analysis`: low variance for every indicator at the declared `startup_candle_count`. For FreqAI strategies recursive-analysis lists only model outputs and does not assess `%` features (the repo harness prints `NOT ASSESSED`); that is not a pass, see the freqtrade-freqai gate.
3. A re-run of both after the last code change.
4. The honest limits: only signals that fired were checked; helpers do not prove a strategy is clean.

Only then suggest a dry run. Live trading is the user's separate, explicit decision.

## References

- references/lookahead.md - options, forced settings, columns, caveats, fixtures
- references/recursive.md - options, startup candle logic, caveats
- references/fix-catalog.md - each bias pattern with WRONG and RIGHT code

## Related skills

freqtrade-strategy (indicators, signals, startup candles), freqtrade-callbacks (callbacks read the dataframe, so they inherit its bias), freqtrade-backtesting (running and reading backtests), freqtrade-config (pairlists, order types), freqtrade-setup (download data).

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
