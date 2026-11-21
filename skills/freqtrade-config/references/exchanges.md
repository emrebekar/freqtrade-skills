Source: docs/exchanges.md#exchange-configuration
Source: docs/exchanges.md#binance
Source: docs/exchanges.md#kraken
Source: docs/exchanges.md#okx
Source: docs/exchanges.md#bybit
Source: docs/exchanges.md#hyperliquid
Source: docs/exchanges.md#all-exchanges

# Exchange notes

Only what the docs state. Freqtrade is built on ccxt; the dev team tested only some exchanges. Credentials go in `exchange.api_key`, `exchange.secret`, and `exchange.password` where required, preferably supplied via environment variables or a private config (see SKILL.md). Never commit them.

## General

- Leave `rateLimit` to ccxt. If you see DDOS/rate-limit errors, raise `exchange.ccxt_async_config.rateLimit` (it is milliseconds between requests; increase, never decrease). Example from the docs for Kraken: `"ccxt_config": {"enableRateLimit": true}, "ccxt_async_config": {"enableRateLimit": true, "rateLimit": 3100}`.
- Constant `InvalidNonce` errors: regenerate the API keys.
- Most exchanges return the incomplete current candle; freqtrade drops the last candle for you and does not let strategies use it.
- `_ft_has_params` under `exchange` overrides exchange behaviour (e.g. `ohlcv_candle_limit`). Unsupported if it breaks things; avoid.
- Stoploss on exchange (`order_types.stoploss_on_exchange: true`) is supported and recommended by the docs on Binance, Bingx, Kraken, Kucoin, HTX, OKX, Gate.io, Bybit (futures only), Bitget, Hyperliquid, Kraken Futures. On several exchanges `order_types.stoploss` can be `"limit"` or `"market"`.

## Binance

- Site: `binance` for binance.com; `binanceus` for binance.us. Wrong id means API keys are not recognized. API access is geo-restricted (Canada, Malaysia, Netherlands, United States are listed as blocked; check the Binance terms).
- Add `"BNB/<STAKE>"` (e.g. `BNB/USDT`) to `pair_blacklist` unless you keep enough BNB for fees; a BNB trade can become unsellable when fees consume it. Freqtrade never buys BNB for fees.
- Supports `time_in_force`.
- RSA keys: set via environment variable `export FREQTRADE__EXCHANGE__SECRET="$(cat ./rsa_binance.private)"`; in a JSON file replace newlines by `\n`.
- Futures: obey Binance's Futures Trading Quantitative Rules (too-low stakes across many orders can restrict the account). Use the order book for pricing (see pricing.md). Account must be in "One-way Mode" Position Mode and "Single-Asset Mode"; freqtrade checks on startup and does not change them.
- BNFCR futures (Europe): `"trading_mode": "futures"`, `"margin_mode": "cross"`, `"proxy_coin": "BNFCR"`, `"stake_currency": "USDT"` (or `"USDC"`); exchange must be in Multi-asset Mode and One-way Mode.

## Bybit

- Stoploss on exchange: futures only. Supports `time_in_force` GTC, FOK, IOC, PO.
- Dedicate the account to the bot; use one subaccount per bot (important for unified accounts). Manual trades or several bots on one account are unsupported.
- Futures: isolated mode only. On startup freqtrade sets the whole (sub)account to One-way Mode; manual changes cause errors. No funding rate history (dry-run calculation is used for live too). Live futures API key permissions: Read-write, Contract - Orders, Contract - Positions. Restrict keys to your IP.
- Demo trading: `exchange.demo_trading: true` with separate demo API keys; incompatible with dry-run.

## OKX

- Needs `password` (the API key passphrase) besides key and secret.
- Registered on my.okx.com (OKX EAA)? Use exchange name `myokx`; otherwise "OKX Error 50119: API key doesn't exist".
- Only 100 candles per API call, so backtesting data is limited. Futures: position mode Buy/Sell recommended, never change mode mid-trading; MARK candles only for about 3 months, so older futures backtests have inexact funding fees.

## Kraken

- Supports `time_in_force` GTC, IOC, PO.
- API serves only 720 historic candles: `download-data --dl-trades` is mandatory for backtest data (see setup skill data-download reference). Needs much RAM/time.
- Rate limit errors: increase `rateLimit` (see General).
- Kraken Futures: exchange id `krakenfutures`, isolated mode, USD-settled:

```jsonc
"exchange": {
    "name": "krakenfutures",
    "api_key": "your_exchange_api_key",
    "secret": "your_exchange_secret"
},
"trading_mode": "futures",
"margin_mode": "isolated",
"stake_currency": "USD"
```

  Select the stoploss trigger price with `order_types.stoploss_price_type` (`mark`, `last`, `index`).

## Hyperliquid

- Decentralized exchange: no API key; private calls are signed with a wallet key. Use an API wallet, not your main wallet's key (it cannot withdraw):

```json
"exchange": {
    "name": "hyperliquid",
    "walletAddress": "your_eth_wallet_address",
    "privateKey": "your_api_private_key"
}
```

  `walletAddress` is `0x` + 40 hex chars (your main wallet, not the API wallet). `privateKey` is `0x` + 64 hex chars (shown when creating the API wallet). Keep both out of committed files.
- Quote/collateral is USDC (deposits via Arbitrum One).
- No market orders (ccxt simulates them with limit orders, max 5% slippage).
- No historic data download possible; only the last 5000 candles are served.
- Subaccount: add `"ccxt_config": {"options": {"subAccountAddress": "..."}}` with the master `walletAddress`. Vault: `walletAddress` = vault address and `"ccxt_config": {"options": {"vaultAddress": "..."}}`. Only one of vault or subaccount.
- Unified accounts are supported; prefer subaccounts and no manual trading while the bot runs.
- HIP-3 DEXes: `"hip3_dexes": ["dex_name"]` under `exchange`; each one costs extra API calls and rate limit. Use `list-pairs` for the right pair names.

## Others (short)

- Kucoin, Bitget: need `password`. Kucoin: blacklist `KCS/<STAKE>` for the same reason as BNB. Bitget futures isolated mode only, One-way Mode set on startup.
- Gate.io: fees paid in POINT break fee detection; set `exchange.unknown_fee_rate`. API key needs "Spot Trade" or "Perpetual Futures" (read/write), "Wallet" (read), "Account" (read).
- Bitvavo: if an operatorId is required, `"ccxt_config": {"options": {"operatorId": "123567"}}` (integer).
