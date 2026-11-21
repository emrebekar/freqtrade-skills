Source: docs/configuration.md#parameters-table
Source: docs/configuration.md#parameters-in-the-strategy
Source: docs/configuration.md#configuration-option-prevalence

# Configuration keys

Only keys listed in the docs' parameters table. "Req" = marked Required (must be set in config, strategy or CLI). "Strat" = can also be set in the strategy; the config value wins. Defaults are the ones the docs state; "-" means no default stated.

Precedence: CLI arguments > environment variables (`FREQTRADE__...`) > config files (last file wins) > strategy attributes.

## Trading and stake

| Key | Default | Meaning |
|-----|---------|---------|
| `max_open_trades` (Req, Strat) | - | Number of simultaneous open trades; `-1` = no limit (pairlist length still limits). One open trade per pair. |
| `stake_currency` (Req) | - | Currency used for trading, e.g. `USDT`. |
| `stake_amount` (Req) | - | Amount per trade, positive float or `"unlimited"` (all available balance split across slots). |
| `tradable_balance_ratio` | `0.99` | Share of total balance the bot may use (0.1 to 1.0). Do not use with multiple bots on one account. |
| `available_capital` | - | Starting capital for this bot when several bots share an account. Replaces `tradable_balance_ratio`. |
| `amend_last_stake_amount` | `false` | Reduce the last stake to the remaining balance (static stake amount only). |
| `last_stake_amount_min_ratio` | `0.5` | Minimum share of `stake_amount` that an amended last stake must keep. |
| `amount_reserve_percent` | `0.05` | Reserve added to the exchange minimum stake (plus stoploss) to avoid refused orders. |
| `timeframe` (Strat) | - | Candle timeframe, usually set in the strategy. |
| `fiat_display_currency` | - | Fiat currency for profit display; removing it skips coingecko. |
| `fee` | exchange default | Fee ratio for backtesting/dry-run (0.001 = 0.1%), applied on each side. Normally leave unset. |
| `trading_mode` | `"spot"` | `spot`, `margin` or `futures` (see leverage docs). |
| `margin_mode` | - | `isolated` or `cross` when using leverage. |
| `liquidation_buffer` | `0.05` | Safety margin ratio between liquidation price and stoploss. |
| `liquidation_warn_ratio` | `0.2` | Notify when liquidation stop distance falls below this fraction of the margin-consuming move; `0` disables. |
| `futures_funding_rate` | `None` | Funding rate used only when exchange history is missing; keep 0 unless you know why. |

## Dry-run

| Key | Default | Meaning |
|-----|---------|---------|
| `dry_run` (Req) | `true` | Simulated trades instead of real orders. |
| `dry_run_wallet` | `1000` | Simulated starting balance (float, or dict per currency such as `{"BTC": 0.01, "USDT": 1000}`). CLI `--dry-run-wallet` overrides the float only. |
| `cancel_open_orders_on_exit` | `false` | Cancel open orders on stop / Ctrl+C / crash. Does not close positions. |
| `db_url` | `sqlite:///tradesv3.dryrun.sqlite` (dry-run) / `sqlite:///tradesv3.sqlite` (live) | SQLAlchemy database URL. Use a fresh database when switching to live. |

## Exit logic and orders

| Key | Default | Meaning |
|-----|---------|---------|
| `minimal_roi` (Req, Strat) | strategy or `{"0": 10}` | Dict of minutes to minimum profit ratio. `"<N>": -1` force-exits after N minutes. |
| `stoploss` (Req, Strat) | - | Stoploss ratio, e.g. `-0.10`. |
| `trailing_stop` (Strat) | - | Enable trailing stoploss. |
| `trailing_stop_positive` (Strat) | - | Trailing distance once profit is reached. |
| `trailing_stop_positive_offset` (Strat) | `0.0` | Profit offset before `trailing_stop_positive` applies. |
| `trailing_only_offset_is_reached` (Strat) | `false` | Trail only after the offset is reached. |
| `use_exit_signal` (Strat) | `true` | Use strategy exit signals in addition to ROI. `false` disables `exit_long`/`exit_short`. |
| `exit_profit_only` (Strat) | `false` | Wait for `exit_profit_offset` before acting on exit signals. |
| `exit_profit_offset` (Strat) | `0.0` | Exit signals only active above this profit ratio (with `exit_profit_only`). |
| `ignore_roi_if_entry_signal` (Strat) | `false` | Do not exit while the entry signal is still active; beats `minimal_roi` and `use_exit_signal`. |
| `ignore_buying_expired_candle_after` (Strat) | - | Seconds after which an entry signal on a candle expires. |
| `process_only_new_candles` (Strat) | `true` | Run indicators only on new candles. |
| `order_types` (Strat) | - | Dict mapping `entry`, `exit`, `stoploss`, `stoploss_on_exchange` (all four required if set in config) plus `emergency_exit`, `force_exit`, `force_entry`, `stoploss_on_exchange_interval`, `stoploss_on_exchange_limit_ratio`. Config replaces the whole strategy dict. |
| `order_time_in_force` (Strat) | `GTC` | Dict `{"entry": ..., "exit": ...}`; values `GTC`, `FOK`, `IOC` (check exchange support). |
| `unfilledtimeout.entry` (Req, Strat) | - | Wait before cancelling an unfilled entry order. |
| `unfilledtimeout.exit` (Req, Strat) | - | Wait before cancelling and re-placing an unfilled exit order. |
| `unfilledtimeout.unit` (Strat) | `"minutes"` | `minutes` or `seconds` (seconds needs `internals.process_throttle_secs` <= timeout). |
| `unfilledtimeout.exit_timeout_count` (Strat) | `0` | Exit order timeouts before an emergency exit; `0` = unlimited. |
| `position_adjustment_enable` (Strat) | `false` | Allow additional buys/sells on open trades. |
| `max_entry_position_adjustment` (Strat) | `-1` | Maximum additional entry orders per trade; `-1` unlimited. |
| `custom_price_max_distance_ratio` | `0.02` | Maximum distance between current and custom entry/exit price. |
| `force_entry_enable` | - | Enable force-entry RPC commands (off by default for safety). |

Pricing keys (`entry_pricing.*`, `exit_pricing.*`): see pricing.md.

## Exchange

| Key | Default | Meaning |
|-----|---------|---------|
| `exchange.name` (Req) | - | ccxt exchange id, e.g. `binance`, `okx`. |
| `exchange.api_key` | - | API key (live only). Secret: never commit. |
| `exchange.secret` | - | API secret (live only). Secret. |
| `exchange.password` | - | API passphrase for exchanges that need one. Secret. |
| `exchange.uid` | - | API uid for exchanges that need one. Secret. |
| `exchange.pair_whitelist` | - | Pairs to trade/backtest; regex like `.*/USDT` allowed. Ignored by a leading `VolumePairList`. |
| `exchange.pair_blacklist` | - | Pairs never traded; regex allowed. |
| `exchange.ccxt_config` | - | Extra ccxt parameters for both ccxt instances. No secrets here (they can appear in logs). |
| `exchange.ccxt_sync_config` / `exchange.ccxt_async_config` | - | Extra ccxt parameters for only the sync / async instance. |
| `exchange.enable_ws` | `true` | Websockets (bool, or per-stream dict such as `{"ohlcv": true, "orderbook": false}`). Currently OHLCV streams only. |
| `exchange.markets_refresh_interval` | `60` | Minutes between market reloads. |
| `exchange.skip_open_order_update` | `false` | Skip open order update on startup (live only). |
| `exchange.unknown_fee_rate` | `None` | Fallback fee conversion for fees paid in non-tradable currencies. |
| `exchange.log_responses` | `false` | Log exchange responses (debug only). |
| `exchange.only_from_ccxt` | `false` | Do not use data.binance.vision for downloads. |
| `experimental.block_bad_exchanges` | `true` | Block exchanges known not to work. Leave on. |

## Plugins, notifications, API

| Key | Default | Meaning |
|-----|---------|---------|
| `pairlists` | `StaticPairList` | List of pairlist handler dicts (see pairlists.md). |
| `telegram.enabled`, `telegram.token`, `telegram.chat_id` | - | Telegram bot. Token and chat id are secrets. |
| `telegram.balance_dust_level` | - | `/balance` hides currencies below this stake-currency value. |
| `telegram.reload` | `true` | Reload buttons on messages. |
| `telegram.allow_custom_messages` | - | Allow strategies to send messages via `dataprovider.send_msg()`. |
| `webhook.enabled`, `webhook.url`, `webhook.entry`, `webhook.entry_cancel`, `webhook.entry_fill`, `webhook.exit`, `webhook.exit_cancel`, `webhook.exit_fill`, `webhook.status` | - | Webhook notifications and payload templates (see docs/webhook-config.md). |
| `api_server.enabled` | - | Enable the Rest API (FreqUI). |
| `api_server.listen_ip_address`, `api_server.listen_port` | - | Bind address; port 1024 to 65535. |
| `api_server.verbosity` | `info` | `info` logs all RPC calls, `error` only errors. |
| `api_server.username`, `api_server.password`, `api_server.ws_token` | - | Credentials. Secrets. |
| `bot_name` | `freqtrade` | Name shown to API clients. |
| `external_message_consumer` | - | Producer/Consumer mode dict (docs/producer-consumer.md). |
| `fiat_display_currency` / `coingecko.api_key`, `coingecko.is_demo` | - | Only for fiat conversion; the key is optional. |

## Other

| Key | Default | Meaning |
|-----|---------|---------|
| `initial_state` | `stopped` | `running`, `paused` or `stopped`. A stopped bot must be started via the RPC `/start`. |
| `disable_dataframe_checks` (Strat) | `false` | Skip checks of the dataframe returned by strategy methods. |
| `internals.process_throttle_secs` | `5` | Minimum seconds per bot loop. |
| `internals.heartbeat_interval` | `60` | Heartbeat log every N seconds; `0` disables. |
| `internals.sd_notify` | - | systemd notify protocol. |
| `strategy` (Req) | - | Strategy class; prefer `--strategy NAME`. |
| `strategy_path` | - | Extra strategy lookup directory. |
| `recursive_strategy_search` | - | Search sub-directories of `user_data/strategies`. |
| `user_data_dir` | `./user_data/` | User data directory. |
| `logfile` | - | Log file name (rotates over 10 files of 1 MB). |
| `add_config_files` | `[]` | Extra config files merged below the parent config; paths relative to the first config. |
| `dataformat_ohlcv`, `dataformat_trades` | `feather` | Storage format of downloaded data; must match what was downloaded. |
| `reduce_df_footprint` | `False` | Cast numeric columns to float32/int32 to save RAM/disk. |
| `log_config` | `FtRichHandler` | Python logging dict (docs/advanced-setup.md#advanced-logging). |
