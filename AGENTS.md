# Freqtrade Skills

Cross-harness Agent Skills (SKILL.md format) for developing Freqtrade strategies.

| Skill | Path |
|-------|------|
| freqtrade-setup | skills/freqtrade-setup/SKILL.md - install Freqtrade (Docker/native), create user dir and config, generate strategy, download and list data |
| freqtrade-config | skills/freqtrade-config/SKILL.md - config keys, secrets, pairlists, protections, pricing, exchange notes |
| freqtrade-strategy | skills/freqtrade-strategy/SKILL.md - write IStrategy classes: indicators, signals, ROI/stoploss, informative pairs, DataProvider, shorting/leverage, Trade object, common mistakes |
| freqtrade-callbacks | skills/freqtrade-callbacks/SKILL.md - strategy callbacks: custom_stoploss, custom_exit, custom_roi, custom_stake_amount, adjust_trade_position (DCA/partial exit), confirm_trade_entry/exit, order price/timeout callbacks, order_filled, leverage, bot_start/bot_loop_start |
| freqtrade-backtesting | skills/freqtrade-backtesting/SKILL.md - run and read backtests (--timerange, --timeframe-detail, --breakdown, --export, --strategy-list), summary metrics, backtest assumptions, backtesting-analysis, backtesting-show, plot-dataframe, plot-profit |
| freqtrade-validation | skills/freqtrade-validation/SKILL.md - safety gate: lookahead-analysis, recursive-analysis, interpreting results, fix catalog (shift(-1), whole-column stats, iloc, resample, merge, startup candles), FreqAI exception, rules before dry-run |
| freqtrade-hyperopt | skills/freqtrade-hyperopt/SKILL.md - tune parameters with hyperopt: IntParameter/DecimalParameter/BooleanParameter, spaces, loss functions, hyperopt-list/show, params JSON precedence, custom loss, overfitting and out-of-sample checks |
