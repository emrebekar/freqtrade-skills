# Freqtrade Skills

Cross-harness Agent Skills (SKILL.md format) for developing Freqtrade strategies.

If your harness has no native skill support: when a task matches a row below, read the listed `skills/<name>/SKILL.md` in full and follow it, opening files in that skill's `references/` folder when the skill points to them. Do not call a strategy finished, or suggest dry-run or live trading, until the freqtrade-validation gate (lookahead-analysis and recursive-analysis) has passed.

| Skill | Path |
|-------|------|
| freqtrade-setup | skills/freqtrade-setup/SKILL.md - install Freqtrade (Docker/native), create user dir and config, generate strategy, download and list data |
| freqtrade-config | skills/freqtrade-config/SKILL.md - config keys, secrets, pairlists, protections, pricing, exchange notes |
| freqtrade-strategy | skills/freqtrade-strategy/SKILL.md - write IStrategy classes: indicators, signals, ROI/stoploss, informative pairs, DataProvider, shorting/leverage, Trade object, common mistakes |
| freqtrade-callbacks | skills/freqtrade-callbacks/SKILL.md - strategy callbacks: custom_stoploss, custom_exit, custom_roi, custom_stake_amount, adjust_trade_position (DCA/partial exit), confirm_trade_entry/exit, order price/timeout callbacks, order_filled, leverage, bot_start/bot_loop_start |
| freqtrade-backtesting | skills/freqtrade-backtesting/SKILL.md - run and read backtests (--timerange, --timeframe-detail, --breakdown, --export, --strategy-list), summary metrics, backtest assumptions, backtesting-analysis, backtesting-show, plot-dataframe, plot-profit |
| freqtrade-validation | skills/freqtrade-validation/SKILL.md - safety gate: lookahead-analysis, recursive-analysis, interpreting results, fix catalog (shift(-1), whole-column stats, iloc, resample, merge, startup candles), FreqAI exception, rules before dry-run |
| freqtrade-hyperopt | skills/freqtrade-hyperopt/SKILL.md - tune parameters with hyperopt: IntParameter/DecimalParameter/BooleanParameter, spaces, loss functions, hyperopt-list/show, params JSON precedence, custom loss, overfitting and out-of-sample checks |
| freqtrade-freqai | skills/freqtrade-freqai/SKILL.md - FreqAI machine learning strategies: freqai config block, feature_engineering_* and set_freqai_targets, % and & prefixes, retraining windows, --freqaimodel, list-freqaimodels, model/prediction reuse by identifier, outlier options, reinforcement learning (untested), FreqAI leakage and validation caveats |
| freqtrade-migration | skills/freqtrade-migration/SKILL.md - migrate old (interface v2) strategies and configs to v3: populate_buy_trend/sell_trend to entry/exit, buy/sell/buy_tag columns, custom_sell, sell_* settings, order_types/unfilledtimeout keys, bid/ask_strategy, `freqtrade strategy-updater` (what it converts and misses), removed features (populate_any_indicators, edge, hdf5, ticker_interval), before/after trade equivalence check |
- Manual/slow suites (not in run_all.sh): tests/test_freqai_fixtures.sh (about 5 min), tests/test_lookahead_fixtures.sh and tests/test_migration_fixtures.sh.
