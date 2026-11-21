Source: docs/deprecated.md
Source: docs/strategy_migration.md#freqai-strategy

# Removed and deprecated features

From docs/deprecated.md (2026.10): "no longer supported. Please avoid their usage in your configuration." Everything below is `docs` unless marked `observed` (seen on the 2026.10 image in this repo). Check an old config or strategy against this list before running it; an old option can be an error or can be silently ignored.

## Removed command line options and config

| Old | Status in 2026.10 | Use instead |
|-----|-------------------|-------------|
| `--refresh-pairs-cached` (backtesting, hyperopt, edge) | removed in 2019.9 | `freqtrade download-data` |
| `--dynamic-whitelist` | removed 2019.6/2019.7 | pairlists (freqtrade-config) |
| `--live` (backtesting) | removed 2019.8 | `freqtrade download-data` |
| `ticker_interval` | compatibility code removed in 2022.3 | `timeframe` |
| `"pairlist"` config section | removed 2020.4 | `"pairlists"`, a list of handlers run in sequence |
| volume pairlist `bidVolume`, `askVolume` | removed 2020.9 | `quoteVolume` (only quote volume is comparable across assets) |
| `order_book_min`, `order_book_max` (stepping the order book for the exit price) | removed 2021.7 | none (docs: no benefit, more risk) |
| Separate hyperopt files (legacy hyperopt mode) | removed 2021.9 | parametrized strategies (freqtrade-hyperopt). |
| `"protections": []` in the config | removed 2024.10 | `protections` in the strategy (freqtrade-config) |
| hdf5 data storage | removed 2025.1 | feather; convert with `freqtrade convert-data` before updating |
| `--logfile systemd` / `--logfile journald` | deprecated 2025.3 | config-based log setup (docs: advanced-setup.md#advanced-logging) |
| Edge module | removed 2025.6; having edge configured "will result in an error" | none |
| `populate_any_indicators()` | removed 2023.3 | `feature_engineering_*()` and `set_freqai_targets()` (freqtrade-freqai) |
| CatBoost FreqAI models | removed 2025.12 | LightGBM or XGBoost; old CatBoost classes can be copied from git history and used as custom models (docs link the commit) |
| Webhook `webhookbuy`, `webhooksell` ... and `buy_tag` in webhooks | renamed in 2022.4; docs say compatibility "for 1-2 versions" then gone | `entry`, `exit`, ... and `enter_tag` (see v2-to-v3.md) |

## Funding rate timeframe change (2025.12, futures)

Docs: since 2025.12 the mark and funding-rate timeframes are 1h for every supported futures exchange (previously usually 8h). Effects:

- Data downloaded earlier needs re-downloading (or selective cleanup, below).
- Strategies using `@informative("8h", candle_type="funding_rate")` or `dp.get_pair_dataframe(metadata["pair"], "8h", candle_type="funding_rate")` must switch to `"1h"`. Docs: Freqtrade "will auto-adjust the timeframe and return `funding_rates` despite the wrongly given timeframe. It'll issue a warning - and may still break your strategy."
- Hyperliquid needs no action (regular candles are used).

Docs example for selective re-download (from the docs, not run here; the glob `*-mark*` deletes files, so check the directory first and keep a backup):

```bash
rm user_data/data/<exchange>/futures/*-mark*
rm user_data/data/<exchange>/futures/*-funding_rate*
freqtrade download-data -t 1h --trading-mode futures --candle-types funding_rate mark --timerange <full timerange you've got other data for>
freqtrade list-data --exchange <yourexchange> --show-timerange
```

Docs inconsistency: the docs write `freqtrade list-data --exchange <yourexchange> --show`, but 2026.10 has no `--show` option (`--show-timerange` exists), so the example above uses that. Add the config, exchange and pair options your setup needs. More on informative and funding-rate candles: freqtrade-strategy. Data download: freqtrade-setup.

## Funding rate data storage format (2026.8, futures)

Docs label (docs/deprecated.md, not run here): since 2026.8 funding rate data is stored with the columns it actually has, `date` and `funding_rate`. Before, it was stored as a regular candle with the rate in `open` and `high`, `low`, `close`, `volume` all 0. Existing data needs no active migration: old-layout files are detected and converted while reading, and rewritten in the new layout the next time they are stored (for example on the next `freqtrade download-data`).

Strategy changes (docs):

- Strategies using `dp.get_pair_dataframe(..., candle_type="funding_rate")` or `@informative("1h", candle_type="funding_rate")` should read the `funding_rate` column instead of `open`. `open` stays as a deprecated alias that "will be removed in a future version". `high`, `low`, `close`, `volume` are no longer present.
- Funding rate dataframes are not padded: one row per funding event (usually every 1h, 4h or 8h), in backtesting and in dry/live. Merge them onto the strategy dataframe by date (`merge_informative_pair` or `@informative`). A direct column assignment aligns by position and gives wrong or mostly `NaN` values.

Merge example and details: freqtrade-strategy, references/informative-pairs.md (section "Funding rate and mark candles").

## What still works in 2026.10 (observed)

Observed on the 2026.10 image, spot mode ([tests/test_migration_fixtures.sh](https://github.com/emrebekar/freqtrade-skills/tree/main/tests/test_migration_fixtures.sh)): the old method names `populate_buy_trend`, `populate_sell_trend`, `custom_sell`, `check_buy_timeout`, `check_sell_timeout`, the `sell_reason` argument of `confirm_trade_exit`, and the old `buy` / `sell` dataframe columns all still load and give the same trades as the migrated version (without a `buy_tag` column; see v2-to-v3.md). The old settings (`use_sell_signal`, `sell_profit_only`, `sell_profit_offset`, `ignore_roi_if_buy_signal`) and the old `order_types`, `order_time_in_force`, `unfilledtimeout` keys log `DEPRECATED` warnings. The docs say compatibility is kept "for now" and "we may drop support for the current interface sometime in the future" with an announced transition period.

Observed (2026.10 source, strategy resolver; docs do not state it): the loader treats non-spot trading modes strictly. With `trading_mode` other than spot, the old setting names are errors (observed: `ERROR - DEPRECATED: Using 'sell_profit_only' moved to 'exit_profit_only'.` from a futures backtest of the legacy fixture), and per the resolver source the old `populate_buy_trend`, `check_buy_timeout`, `check_sell_timeout` and `custom_sell` raise `OperationalException` ("Please migrate your implementation of ..."). The docs say migrate if you intend to use markets other than spot.

Observed source comment: interface.py says "Default to version 2" above `INTERFACE_VERSION: int = 3`. The value is 3, matching the docs ("3 ... is also the default when it's not set explicitly").

Strategy Interface v1 (populate functions without the `metadata` argument) is rejected: "Strategy Interface v1 is no longer supported" (observed in 2026.10 source). Add the `metadata: dict` argument to `populate_indicators`, `populate_entry_trend` and `populate_exit_trend`.
