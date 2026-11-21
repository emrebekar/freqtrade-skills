Source: docs/backtesting.md#test-your-strategy-with-backtesting
Source: docs/backtesting.md#example-backtesting-commands
Source: docs/backtesting.md#backtest-result-caching
Source: docs/backtesting.md#backtest-output-file
Source: docs/backtesting.md#backtesting-multiple-strategies
Source: docs/commands/backtesting.md

# Backtesting commands and options

All commands below were run on 2026.10 with the repo's test data and strategies, except where marked "docs". Global flags such as `--no-color` go after the subcommand. In Docker, prefix with `docker compose run --rm freqtrade` (see freqtrade-setup).

```bash
freqtrade backtesting --strategy AwesomeStrategy
freqtrade backtesting --strategy AwesomeStrategy --timeframe 1m
freqtrade backtesting --strategy AwesomeStrategy --dry-run-wallet 1000
freqtrade backtesting --strategy AwesomeStrategy --datadir user_data/data/binance-20180101
freqtrade backtesting --timerange 20180401-20180410 --timeframe 5m --strategy-list Strategy001 Strategy002 --export trades
freqtrade backtesting --strategy AwesomeStrategy --export none --config config.json
freqtrade backtesting --strategy AwesomeStrategy --export trades --backtest-directory user_data/custom-backtest-results
freqtrade backtesting --fee 0.001
```

`--strategy` takes the class name, not the file name. Backtesting uses the pairs from the config and the data in `user_data/data/<exchange>`; if data is missing it asks you to download it (`freqtrade download-data`). All profit calculations include fees. The starting balance (`--dry-run-wallet` / `--starting-balance` / `dry_run_wallet`) must be higher than `stake_amount`, otherwise no trade can be simulated. `stake_amount: "unlimited"` splits the balance into `max_open_trades` pieces and compounds profits.

## Options (from `freqtrade backtesting --help`, 2026.10)

| Option | Meaning |
|--------|---------|
| `-s`, `--strategy NAME` | Strategy class. `--strategy-path PATH` adds a lookup folder; `--recursive-strategy-search` searches subfolders. |
| `-i`, `--timeframe` | Timeframe to run. |
| `--timeframe-detail` | Detail timeframe for intra-candle simulation. |
| `--timerange` | Limit dates (formats below). |
| `--max-open-trades INT`, `--stake-amount`, `--fee FLOAT` | Override config values. |
| `-p`, `--pairs` | Limit to these pairs. |
| `--eps`, `--enable-position-stacking` | Allow the same pair several times. Not reproducible live. |
| `--enable-protections` | Apply configured protections; slows down considerably. |
| `--enable-dynamic-pairlist` | Refresh dynamic pairlists per candle if the handler supports it. |
| `--dry-run-wallet`, `--starting-balance` | Starting balance. |
| `--strategy-list A B` | Several strategies; timeframe must come from config or `-i`. |
| `--export {none,trades,signals}` | Default `trades`. `signals` also exports signal candles. |
| `--backtest-directory PATH` | Directory for results. |
| `--breakdown {day,week,month,year,weekday}` | One or more breakdown tables. |
| `--cache {none,day,week,month}` | Reuse a cached result no older than this; default `day`. |
| `--notes TEXT` | Notes stored with the result. |
| `--freqai-backtest-live-models` | FreqAI: backtest with ready models. |
| `--data-format-ohlcv` | `json`, `jsongz`, `feather`, `parquet` (default `feather`). |

`--backtest-filename` / `--export-filename` is marked DEPRECATED for `backtesting` in the 2026.10 help: custom file names are no longer supported, use `--backtest-directory`. It still works for `backtesting-analysis`, `backtesting-show` and the plot commands to pick an existing result.

## Timerange

Formats (UTC; each side parsed separately and may be mixed): `20260131`, `20260131T1530`, `20260131T053045`, epoch seconds (10 digits), epoch milliseconds (13 digits). `20260131-` is open-ended at the end, `-20260131` open at the start. Backtesting loads `startup_candle_count` extra candles before the start; make sure the downloaded data reaches back that far (freqtrade-setup).

## Cache

By default a backtest reuses a cached result from within the last day when strategy and config match. Use `--cache none` to force a new run. Caching is disabled for open-ended timeranges. The cache silently ignores changes in modules the strategy imports and can reuse a result that was run before missing data was downloaded: use `--cache none` once in those cases. `lookahead-analysis` forces `--cache none` itself.

## Result files

Observed on 2026.10: a run writes `backtest-result-<timestamp>.zip` and `backtest-result-<timestamp>.meta.json` into `<userdir>/backtest_results/`. The zip held: the result JSON, `_config.json`, a copy of the strategy `.py`, `_market_change.feather`, `_<Strategy>_wallet.feather` and, with `--export signals`, `_signals.pkl`, `_rejected.pkl` and `_exited.pkl`. The docs describe the zip as containing the report JSON, market change, strategy copy, parameters copy (if any) and a sanitized config; only the strategy file and config are saved, not imported modules. Signal exports can be large; delete old results periodically.

## Multiple strategies

`--strategy-list` loads data once and prints details for each strategy, then a comparison table (the TOTAL row of each). Real output (test data, trimmed):

```text
┃          Strategy ┃ Trades ┃ Avg Profit % ┃ Tot Profit USDT ┃ Tot Profit % ┃ Avg Duration ┃  Win  Draw  Loss  Win% ┃          Drawdown ┃
│ IndicatorsExample │    200 │         0.08 │          15.811 │         1.58 │      8:23:00 │  129     0    71  64.5 │ 9.777 USDT  0.96% │
│ ValidationExample │     13 │        -0.16 │          -2.122 │        -0.21 │      4:53:00 │    6     0     7  46.2 │ 2.671 USDT  0.27% │
```

All listed strategies must be in the same directory unless `--recursive-strategy-search` is used.

## Docs inconsistencies found while building this skill

- `docs/advanced-backtesting.md` shows `freqtrade backtesting ... --backtest-filename ...` and says `_signals.pkl` and `_exited.pkl` appear in the results folder. The 2026.10 help marks `--backtest-filename` deprecated for `backtesting`, and the files are inside the result zip (observed). Prefer `--backtest-directory` and let `backtesting-analysis` read the latest result.
- `docs/plotting.md` examples use `--export-filename user_data/backtest_results/backtest-result.json`; results are zips now. Observed: the plot commands found the latest result without that option.
- `docs/backtesting.md` prose explaining the TOTAL row quotes `54.774` while the table above it shows `57.157`; the table values are the consistent ones.
- Docs say the breakdown option takes day, week, month, year; the help also lists `weekday`.
