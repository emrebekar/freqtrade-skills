---
name: freqtrade-config
description: Use when you need to write or edit a Freqtrade config.json, set stake amount, max_open_trades, dry-run vs live, pairlists (StaticPairList, VolumePairList, filters), pair whitelist/blacklist, order pricing, protections, exchange-specific settings, or keep API keys out of the config. Covers key table, environment variables, multiple config files, show-config, test-pairlist, Binance, Bybit, OKX, Kraken and Hyperliquid notes.
license: GPL-3.0
---

# Freqtrade configuration

How to configure the bot (`config.json`) correctly and safely. Pinned Freqtrade release: 2026.10. All keys here come from the Freqtrade configuration docs; look keys up in references/config-keys.md rather than guessing names.

Rules:
- Keep `dry_run: true` until the strategy passed backtesting and dry-run observation. Never set `dry_run: false` unless the user explicitly asks.
- Do not call a strategy finished, and do not suggest dry-run or live trading, until `lookahead-analysis` and `recursive-analysis` pass. Exception: FreqAI columns set in `set_freqai_targets()` can be reported as look-ahead false positives.
- Secrets never go into a config that is committed or shared. See "Secrets".
- Futures need `trading_mode` and `margin_mode` in the config; spot is the default.

## Format

JSON, but `// line` and `/* block */` comments and trailing commas are accepted. Add `"$schema": "https://schema.freqtrade.io/schema.json"` as first key for editor validation. Pass `-c/--config PATH` (repeatable); default is `user_data/config.json` or `config.json`.

Precedence: CLI arguments > environment variables > config files (last wins) > strategy attributes. Config values override strategy values for keys marked "Strat" in the key table (e.g. `minimal_roi`, `stoploss`, `timeframe`, `max_open_trades`).

## Minimal spot dry-run config

```json
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 100,
    "dry_run": true,
    "dry_run_wallet": 1000,
    "trading_mode": "spot",
    "unfilledtimeout": {"entry": 10, "exit": 10, "unit": "minutes"},
    "entry_pricing": {"price_side": "same", "use_order_book": true, "order_book_top": 1, "price_last_balance": 0.0},
    "exit_pricing": {"price_side": "same", "use_order_book": true, "order_book_top": 1, "price_last_balance": 0.0},
    "exchange": {
        "name": "binance",
        "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
        "pair_blacklist": ["BNB/USDT"]
    },
    "pairlists": [{"method": "StaticPairList"}]
}
```

Futures (spot differs only here; pairs are written `BTC/USDT:USDT`):

```json
{
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "exchange": {
        "name": "binance",
        "pair_whitelist": ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    }
}
```

Binance futures need order book pricing (`use_order_book: true`); see references/pricing.md. Other exchanges: references/exchanges.md.

## Stake and capital

- `stake_amount`: fixed number (max capital in use = `stake_amount * max_open_trades`) or `"unlimited"` (balance divided across open-trade slots; set a realistic `dry_run_wallet`, backtests simulate from it).
- `tradable_balance_ratio` (default 0.99) leaves part of the wallet untouched. For several bots on one account use `available_capital` per bot instead (it replaces `tradable_balance_ratio`).
- `amend_last_stake_amount: true` lets the last slot use a reduced stake (minimum `last_stake_amount_min_ratio`, default 0.5).
- The exchange minimum stake plus `amount_reserve_percent` (default 0.05) and stoploss applies; a stake far below it is raised, one far above the wanted stake is rejected.

## Secrets

Never write API keys, secrets, passwords, Telegram tokens or API server passwords into a committed config. Dry-run needs no keys. Two safe options:

1. A private config merged on top, kept out of git (add it to `.gitignore`):

```bash
freqtrade trade --config user_data/config.json --config user_data/config-private.json --strategy MyStrategy
```

   `config-private.json` only contains `{"exchange": {"api_key": "...", "secret": "..."}}` (plus `password`, `telegram` etc. as needed). The last file wins on conflicts. Alternatively list it in `add_config_files` of the main config (paths relative to the first config; the parent config wins on collisions).
2. Environment variables, format `FREQTRADE__{section}__{key}`, `__` as level separator:

```bash
export FREQTRADE__EXCHANGE__API_KEY=<yourExchangeKey>
export FREQTRADE__EXCHANGE__SECRET=<yourExchangeSecret>
export FREQTRADE__TELEGRAM__TOKEN=<telegramToken>
export FREQTRADE__TELEGRAM__CHAT_ID=<telegramChatId>
export FREQTRADE__EXCHANGE__PAIR_WHITELIST='["BTC/USDT", "ETH/USDT"]'
```

   Env vars override config values; JSON lists are parsed as JSON. The docs' own example uses `FREQTRADE__EXCHANGE__KEY`; the code accepts both `api_key` and the older `key`, but `api_key` wins when both are present, so use `FREQTRADE__EXCHANGE__API_KEY` (verified with `show-config` on the pinned release). The config file path cannot come from an env var. Loaded env vars are logged at startup.

Check the merged result; secrets are redacted unless `--show-sensitive` is given (do not paste that output anywhere):

```bash
freqtrade show-config --config user_data/config.json --config user_data/config-private.json
```

Before sharing a config or a log, check it for keys, tokens, wallet addresses and private keys (Hyperliquid uses `walletAddress` and `privateKey`).

## Pairlists

Dynamic `VolumePairList`, filters, blacklist regex, backtesting limits and every handler's settings: references/pairlists.md. Test a pairlist (needs network access to the exchange):

```bash
freqtrade test-pairlist --config user_data/config.json --quote USDT
```

`VolumePairList` ignores `pair_whitelist` in first position and does not work in backtesting; backtest with a `StaticPairList`.

## Protections

Stop trading after stoploss streaks, drawdowns or low-profit pairs: `StoplossGuard`, `MaxDrawdown`, `LowProfitPairs`, `CooldownPeriod`. Defined in the strategy (`protections` property); backtesting needs `--enable-protections`. See references/protections.md.

## Pricing

`entry_pricing` / `exit_pricing` (`price_side` same/other/ask/bid, order book vs ticker). Prefer `same` or `other`. Market orders need `price_side: other`. See references/pricing.md.

## Exchange notes

Binance (BNB blacklist, binance vs binanceus, futures modes), Bybit, OKX (`password`, `myokx`), Kraken (720 candles, `--dl-trades`), Hyperliquid (wallet keys, no data download, no market orders), Kucoin, Gate.io, Bitget: references/exchanges.md.

## Workflow

1. Read the existing config before editing; change only what was asked.
2. Look up every key name in references/config-keys.md; do not invent keys. `show-config` rejects wrong value types but accepts unknown keys (verified on the pinned release), so a misspelled key is silently ignored.
3. Run `freqtrade show-config --config <file>` to validate the file (value-type errors are reported) and see the merged result.
4. For a pairlist change run `freqtrade test-pairlist`; for pricing/protection changes backtest with `--enable-protections` where relevant.
5. Switching to live is a separate, explicit decision by the user: `dry_run: false`, a fresh `db_url`, keys via private config or env vars, small stake.

## Related skills

freqtrade-setup (install, user directory, `new-config`, data download), freqtrade-strategy (writing and validating strategies).

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
