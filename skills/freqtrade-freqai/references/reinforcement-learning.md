Source: docs/freqai-reinforcement-learning.md
Source: docs/freqai-parameter-table.md#reinforcement-learning-parameters

# Reinforcement learning (documented, UNTESTED)

Nothing on this page was run in this repo: the `2026.10_freqai` image cannot import `ReinforcementLearner` (observed: `No module named 'torch'`, status `LOAD FAILED` in `list-freqaimodels`), and the RL image (`2026.10_freqairl`; docs tag `stable_freqairl`) was not pulled. Treat every statement as the docs' claim. Verify on your setup before relying on it.

## What it is (docs)

An agent moves candle by candle through historical data and picks an action (long entry, long exit, short entry, short exit, neutral). A training environment scores the actions with `calculate_reward()` and the reward trains a neural network (stable_baselines3, `gym.Env`). State information (current profit, position, trade duration) can be fed in; it is only available in dry/live and is switched off for backtesting (`add_state_info`).

Docs warnings worth repeating to users:
- Improperly trained agents may find "cheats" to maximize reward without winning trades. RL needs more understanding than a regressor or classifier.
- The RL environment is not the Freqtrade backtester: no `custom_exit`, `custom_stoploss`, leverage controls or other callbacks. The agent learns its own stoploss/take-profit through the reward.
- The shipped `calculate_reward()` is a showcase and benchmark, "not for production". Write your own model class (in `user_data/freqaimodels`) or use one from outside the Freqtrade source.

## Running (docs)

```bash
freqtrade trade --freqaimodel ReinforcementLearner --strategy MyRLStrategy --config config.json
```

Same two flags as other FreqAI models. The strategy uses the same `feature_engineering_*()`; there are no real labels, but a neutral default is required in `set_freqai_targets()`:

```python
    def set_freqai_targets(self, dataframe, **kwargs) -> DataFrame:
        # For RL, there are no direct targets to set. This is filler (neutral)
        # until the agent sends an action.
        dataframe["&-action"] = 0
        return dataframe
```

The raw prices must be passed to the environment as features in `feature_engineering_standard()`: `%-raw_close`, `%-raw_open`, `%-raw_high`, `%-raw_low`. Docs inconsistency: the printed snippet has `return dataframe` dedented outside the function, which is a syntax error as written (docs example broken; fix the indentation).

The agent's decision is the integer in `&-action`, used in `populate_entry_trend()` / `populate_exit_trend()` together with `do_predict == 1`. With the 5-action environment: 0 neutral, 1 enter long, 2 exit long, 3 enter short, 4 exit short. The docs snippet builds `enter_long_conditions` lists with `functools.reduce`; the `if enter_long_conditions:` test is always true for a non-empty list, harmless.

## Environments (docs)

`Base3ActionRLEnv` (hold, long, short; the only one for long-only strategies with `can_short = False`; long is entry and short is exit), the 4-action environment (docs name `Base4ActionEnvironment`: enter long, enter short, neutral, exit), `Base5ActionRLEnv` (as 4, with separate exit long and exit short). Docs inconsistency: the text names them `Base3ActionRLEnvironment`/`Base4ActionEnvironment`/`Base5ActionEnvironment`, the code uses `Base5ActionRLEnv`. All use 0 as neutral. Which environment you pick changes the action numbers your strategy must use.

## `rl_config` (docs example)

```json
        "rl_config": {
            "train_cycles": 25,
            "add_state_info": true,
            "max_trade_duration_candles": 300,
            "max_training_drawdown_pct": 0.02,
            "cpu_count": 8,
            "model_type": "PPO",
            "policy_type": "MlpPolicy",
            "model_reward_parameters": {
                "rr": 1,
                "profit_aim": 0.025
            }
        }
```

`train_cycles` decides how many times the agent cycles through the candles. `model_type` is a stable_baselines3 / sb3-contrib name (`TRPO`, `ARS`, `RecurrentPPO`, `MaskablePPO`, `PPO`, `A2C`, `DQN`); put that model's hyperparameters in the general `model_training_parameters`. Other keys: `max_training_drawdown_pct` (default 0.8), `net_arch` (default `[128, 128]`), `randomize_starting_position`, `drop_ohlc_from_features`, `progress_bar` (parameters.md). `continual_learning` can also be set for RL (docs).

## Custom reward (docs)

Subclass `ReinforcementLearner`, define an inner `MyRLEnv(Base5ActionRLEnv)` with `calculate_reward(self, action: int) -> float`, and save the file in `user_data/freqaimodels`. The docs example penalizes invalid actions, rewards entering, penalizes sitting out and long holds, and scales a closing reward by PnL. Hint from the docs: use smooth, well-scaled rewards; a single large penalty on a rare event cannot be learned. `self.tensorboard_log("name")` counts events in TensorBoard.

## Pitfalls specific to RL

- A reward computed from information the live agent will not have (future prices) trains a cheating agent; keep `calculate_reward()` using past and current state only. (Repo advice, not from the docs.)
- `add_state_info` is off in backtests but on in dry/live, so backtest and live inputs differ by design (docs). Do not expect a backtest to predict live behavior.
- Re-run the validation gate; see SKILL.md. The look-ahead tools' behavior on RL strategies is unknown here.
