Source: docs/includes/protections.md#protections
Source: docs/includes/protections.md#available-protections
Source: docs/includes/protections.md#full-example-of-protections

# Protections

Temporarily stop trading one pair or all pairs after unexpected events. Lock end times are rounded up to the next candle. The docs show them defined in the strategy as a `protections` property. Backtesting and hyperopt only apply them with the `--enable-protections` flag. Each protection can appear several times with different parameters; they are evaluated in the order defined. Not every protection fits every strategy; tune the parameters.

## Common settings

| Parameter | Meaning |
|-----------|---------|
| `method` | `StoplossGuard`, `MaxDrawdown`, `LowProfitPairs`, `CooldownPeriod`. |
| `stop_duration_candles` | Lock length in candles. |
| `stop_duration` | Lock length in minutes (float). Not together with `stop_duration_candles`. |
| `lookback_period_candles` | Only trades closed within the last N candles count (may be ignored by some protections). |
| `lookback_period` | Same, in minutes. Not together with `lookback_period_candles`. |
| `trade_limit` | Minimum number of trades required (not used by all). |
| `unlock_at` | `"HH:MM"` (24h) time when trading unlocks regularly (not used by all). |

## StoplossGuard

If `trade_limit` or more trades hit a stoploss (`stop_loss`, `stoploss_on_exchange`, `trailing_stop_loss` with negative profit) within the lookback, stop trading for the duration. All pairs unless `only_per_pair` is true. `only_per_side` (futures) locks only the affected side. `required_profit` (default 0.0) sets the profit below which stoplosses count.

```python
@property
def protections(self):
    return [
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 24,
            "trade_limit": 4,
            "stop_duration_candles": 4,
            "required_profit": 0.0,
            "only_per_pair": False,
            "only_per_side": False
        }
    ]
```

## MaxDrawdown

Evaluates trades closed in the lookback; if drawdown exceeds `max_allowed_drawdown`, stop for the duration after the last trade. `calculation_mode`: `"ratios"` (default, legacy approximation from cumulative profit ratios) or `"equity"` (peak-to-trough on the equity curve; recommended for new setups).

```python
@property
def protections(self):
    return  [
        {
            "method": "MaxDrawdown",
            "calculation_mode": "equity",
            "lookback_period_candles": 48,
            "trade_limit": 20,
            "stop_duration_candles": 12,
            "max_allowed_drawdown": 0.2
        },
    ]
```

## LowProfitPairs

Locks a pair if its profit ratio over the lookback is below `required_profit`. `only_per_side` for futures.

```python
@property
def protections(self):
    return [
        {
            "method": "LowProfitPairs",
            "lookback_period_candles": 6,
            "trade_limit": 2,
            "stop_duration": 60,
            "required_profit": 0.02,
            "only_per_pair": False,
        }
    ]
```

## CooldownPeriod

Locks a pair for the duration after a trade closes. Pair-level only; ignores `lookback_period` (looks at the latest trade).

```python
@property
def protections(self):
    return  [
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 2
        }
    ]
```

## Combined (1h timeframe)

```python
from freqtrade.strategy import IStrategy

class AwesomeStrategy(IStrategy):
    timeframe = '1h'
    
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 5
            },
            {
                "method": "MaxDrawdown",
                "calculation_mode": "equity",
                "lookback_period_candles": 48,
                "trade_limit": 20,
                "stop_duration_candles": 4,
                "max_allowed_drawdown": 0.2
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 4,
                "stop_duration_candles": 2,
                "only_per_pair": False
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 6,
                "trade_limit": 2,
                "stop_duration_candles": 60,
                "required_profit": 0.02
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 24,
                "trade_limit": 4,
                "stop_duration_candles": 2,
                "required_profit": 0.01
            }
        ]
    # ...
```
