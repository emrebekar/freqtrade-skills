---
name: freqtrade-setup
description: Use when you need to install Freqtrade, set up a user_data directory, create a first config.json, generate a strategy file, or download and inspect historical candle data for backtesting. Covers Docker (recommended) and native install, create-userdir, new-config, new-strategy templates, download-data (--timerange, --timeframes, --trading-mode futures, --prepend), list-data and Kraken/Hyperliquid data limits.
license: GPL-3.0
---

# Freqtrade setup

Get from nothing to a working user directory, a dry-run config, a strategy file and downloaded data. Pinned Freqtrade release: 2026.10.

Rules for every step below:
- Start with `dry_run: true`. Never put exchange API keys in a config you commit or share (see the freqtrade-config skill).
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass on it. The only blanket exception is FreqAI `set_freqai_targets()` columns (targets are expected to look ahead). Pairlist-dependent logic and limit orders with `custom_entry_price()`/`custom_exit_price()` can also give documented false positives; explain each to the user, never silently ignore.
- Docker: pin the image to the release tag `freqtradeorg/freqtrade:2026.10` (or its `_plot`/`_freqai`/`_freqaitorch`/`_freqairl` flavour). Never use `latest` (it is the unreleased `develop` build), `develop*`, `stable*` or an image without a tag. Details: references/install-docker.md.
- Backtests need data: download it first (below) and include the strategy's `startup_candle_count` extra candles before the timerange start.

## 1. Install

Docker is the recommended path (and strongly recommended on Windows). Details: references/install-docker.md. Native install (script, manual, conda): references/install-native.md.

Docker quick start:

```bash
mkdir ft_userdata
cd ft_userdata/
curl https://raw.githubusercontent.com/freqtrade/freqtrade/stable/docker-compose.yml -o docker-compose.yml
sed -i 's#freqtrade:stable#freqtrade:2026.10#' docker-compose.yml
docker compose pull
docker compose run --rm freqtrade --version
```

The downloaded compose file uses the floating `stable` tag; the `sed` line pins it (macOS: `sed -i ''`). `--version` must report `freqtrade 2026.10`.

Every freqtrade command then runs as `docker compose run --rm freqtrade <command>`. In native installs, activate the venv first (`source ./.venv/bin/activate`) and run `freqtrade <command>` directly. Examples below use the short `freqtrade` form; prefix with `docker compose run --rm` in Docker.

## 2. Create the user directory

```bash
freqtrade create-userdir --userdir user_data
```

Creates `user_data/` with `strategies/`, `data/` and other subfolders plus sample files. `--reset` restores the sample files to their original state.

If `user_data` was created by Docker and you get "Permission denied" when copying files into it on Linux: `sudo chown -R $UID:$GID user_data`.

## 3. Create a config

```bash
freqtrade new-config --config user_data/config.json
```

`new-config` asks interactive questions, so run it in a terminal you control (an agent cannot answer them; ask the user to run it, or write the file by hand from the example below). Questions, in order:

| Question | What to answer |
|----------|----------------|
| Enable Dry-run (simulated trades)? | Yes. Keep yes until the strategy is validated. |
| Stake currency | e.g. `USDT`. Must match the quote currency of your pairs. |
| Stake amount | A number, or `unlimited` (all available balance split across `max_open_trades`). |
| max_open_trades | Integer, or `-1` for unlimited. |
| Timeframe | "Have the strategy define timeframe" (usual) or override in config. |
| Fiat display currency | e.g. `USD`; empty disables fiat conversion. |
| Exchange | binance, binanceus, bingx, gate, htx, kraken, kucoin, okx, or "other" (any ccxt exchange). |
| Perpetual futures? | Asked for binance, gate, okx, bybit. Yes sets `trading_mode: futures` and `margin_mode: isolated`. |
| API key / secret (/ password) | Only asked when dry-run is off. Skip by staying in dry-run. |
| Telegram, Rest API (FreqUI) | Optional. Answer no unless needed. |

Resulting config for binance spot, dry-run, unlimited stake (trimmed; the generated file also contains telegram, api_server and other sections, and by default uses `VolumePairList` with 20 assets):

```json
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "dry_run_wallet": 1000,
    "trading_mode": "spot",
    "margin_mode": "",
    "unfilledtimeout": {"entry": 10, "exit": 10, "unit": "minutes"},
    "exchange": {
        "name": "binance",
        "api_key": "",
        "secret": "",
        "pair_whitelist": [],
        "pair_blacklist": ["BNB/.*"]
    },
    "pairlists": [
        {"method": "VolumePairList", "number_assets": 20, "sort_key": "quoteVolume", "refresh_period": 1800}
    ]
}
```

Configuration keys, pairlists, pricing, protections and exchange notes: freqtrade-config skill.

## 4. Create a strategy file

```bash
freqtrade new-strategy --strategy MyStrategy --userdir user_data --template full
```

Templates: `minimal` (bare skeleton), `full` (default; sample indicators), `advanced` (extra callbacks). The file is written to `user_data/strategies/MyStrategy.py`. The class name must equal `--strategy`. Use `--strategy-path` to look in another directory.

Pitfall: a generated template's default `startup_candle_count` can be too low for its indicators (the `full` template ships 30 and fails `recursive-analysis`). Run `freqtrade recursive-analysis` and raise it before trusting backtests.

## 5. Download data

```bash
freqtrade download-data --exchange binance --pairs BTC/USDT ETH/USDT --timeframes 5m 1h --timerange 20250101- --userdir user_data
```

- Use `-c user_data/config.json` to take exchange, pairs and (with `--timeframes`) timeframes from your config instead.
- Default without options: timeframes `1m 5m`, last 30 days. `--days N` = last N days; `--timerange 20250101-20250601` = absolute range. Re-running tops up existing data to now.
- Regex pairs: `--pairs ".*/USDT"` (all active USDT pairs; add `--include-inactive-pairs` for delisted ones).
- Futures: add `--trading-mode futures` (pairs look like `BTC/USDT:USDT`); mark and funding-rate candles are fetched automatically.
- Earlier history for existing data: `--prepend --timerange 20240101-20250101`.
- Download the timeframe your strategy uses plus every `informative_pairs`/informative timeframe, and extra history for the startup period.
- Kraken has no historic candles: needs `--dl-trades`. Hyperliquid has no downloadable history. Details: references/data-download.md.

Inspect what you have:

```bash
freqtrade list-data --userdir user_data --show-timerange
freqtrade list-data --userdir user_data --trading-mode futures
```

## Verify the install end to end

```bash
freqtrade list-exchanges
freqtrade backtesting --config user_data/config.json --strategy MyStrategy --timerange 20250101-20250301 --userdir user_data
```

## Next

Develop and test the strategy with the freqtrade-strategy skill; tune the config, pairlists and protections with the freqtrade-config skill.

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
