Source: docs/data-download.md#getting-data-for-backtesting-and-hyperopt
Source: docs/data-download.md#download-additional-data-before-the-current-timerange
Source: docs/data-download.md#data-format
Source: docs/data-download.md#pairs-file
Source: docs/data-download.md#trades-tick-data
Source: docs/commands/download-data.md
Source: docs/commands/list-data.md
Source: docs/exchanges.md#historic-kraken-data

# Downloading and inspecting data

`download-data` fetches candles (OHLCV). Without options: timeframes `1m` and `5m`, last 30 days. Exchange and pairs come from the config when `-c/--config` is given; without a config `--exchange` is mandatory. Existing data is topped up from the latest candle to now; neither `--days` nor `--timerange` is required then.

## Options that matter

| Option | Meaning |
|--------|---------|
| `-p, --pairs P [P ...]` | Pairs (regex allowed, e.g. `".*/USDT"`). |
| `--pairs-file FILE` | JSON list of pairs; takes precedence over `--pairs` and config. |
| `-t, --timeframes T [T ...]` | Timeframes to download. Default `1m 5m`. |
| `--days N` | Last N days (relative; use this for incremental updates). |
| `--timerange R` | `yyyymmdd` or `yyyymmddThhmm`, e.g. `20240101-20240201T1200`, `20200101-`. Start points are ignored if data already exists. |
| `--new-pairs-days N` | Days to fetch for pairs that have no data yet; old pairs only get the missing part. |
| `--prepend` | Allow prepending older data. Appending is disabled in this mode. |
| `--include-inactive-pairs` | Also download delisted pairs. |
| `--trading-mode {spot,margin,futures}` | Futures also fetches `mark` and `funding_rate` candles unless `--candle-types` says otherwise. |
| `--candle-types ...` | `spot, futures, mark, index, premiumIndex, funding_rate, open_interest`. |
| `--erase` | Delete existing data of the selected exchange/pairs/timeframes first. |
| `--data-format-ohlcv {json,jsongz,feather,parquet}` | Storage format; default `feather` (recommended). |
| `-d, --datadir PATH` | Data directory (default is exchange specific under `user_data/data`). |
| `--dl-trades`, `--convert` | Download trades instead of candles; `--convert` resamples them to candles. |
| `--no-parallel-download` | Only if the parallel startup download causes problems. |

## Examples

```bash
freqtrade download-data --exchange binance
freqtrade download-data --exchange binance --pairs ETH/USDT XRP/USDT BTC/USDT
freqtrade download-data --exchange binance --pairs ".*/USDT" --timeframes 5m 1h --timerange 20250101-
freqtrade download-data --exchange binance --pairs BTC/USDT:USDT --timeframes 1h --trading-mode futures --timerange 20250101-
freqtrade download-data --exchange binance --pairs ETH/USDT XRP/USDT BTC/USDT --prepend --timerange 20210101-20220101
freqtrade download-data -c user_data/config.json --days 10 --new-pairs-days 30
```

With `--prepend`, an end date is ignored when data exists: it is moved to the start of the existing data.

## Startup period

`download-data` does not know a strategy's `startup_candle_count`. If a backtest should start at a given date, download that many extra candles before it.

## Futures extras

Open interest is not downloaded by default:

```bash
freqtrade download-data --exchange binance --pairs BTC/USDT:USDT --timeframes 1h --trading-mode futures --candle-types open_interest
```

Exchanges often keep little open-interest history (Binance serves about the last 30 days). Bybit reports only `open_interest_amount` on linear markets. Funding rate data is stored with `date` and `funding_rate` columns.

## Data formats

`feather` (default, fast, small), `json`, `jsongz`, `parquet` (OHLCV only). If you change the format, set `dataformat_ohlcv` and `dataformat_trades` in the config to match. Convert later with `convert-data` and `convert-trade-data`.

## Pairs file

`user_data/data/<exchange>/pairs.json` is a JSON list; mixed stake currencies are allowed because it is only used for downloading. It is only read when no config is loaded or when `--pairs-file` is given. Prefer `exchange.pair_whitelist` in the config.

## list-data

```bash
freqtrade list-data --userdir user_data
freqtrade list-data --userdir user_data --show-timerange
freqtrade list-data --userdir user_data --trading-mode futures
freqtrade list-data --userdir user_data --trades
freqtrade list-data --userdir user_data -p BTC/USDT
```

Options: `--exchange`, `--data-format-ohlcv`, `--data-format-trades`, `--trades`, `-p/--pairs`, `--trading-mode`, `--show-timerange` (may take a while; reads the data). The table lists pair, timeframes and candle type per pair.

## Exchange limits

- Kraken: the API gives only 720 historic candles. `--dl-trades` is mandatory for backtest data:

```bash
freqtrade download-data --exchange kraken --pairs XRP/EUR ETH/EUR --days 20 --dl-trades
```

  It needs a lot of RAM and time (every trade is downloaded and resampled). Kraken Futures uses normal OHLCV downloads without `--dl-trades`. Kraken trade CSV archives can be imported (see docs/exchanges.md#historic-kraken-data). Add timeframes later with `freqtrade trades-to-ohlcv --exchange kraken -t 5m 1h 1d --pairs BTC/EUR`.
- Hyperliquid: no historic data download is possible; the API only serves the last 5000 candles, so backtests are limited to those (or data you collect over time).
- OKX: 100 candles per API call, so backtests have little data; futures MARK candles only for about 3 months.
- Do not use `--dl-trades` on other exchanges: the docs say candle download is much faster.
