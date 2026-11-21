Source: docs/plotting.md#installation-setup
Source: docs/plotting.md#plot-price-and-indicators
Source: docs/plotting.md#plot-profit
Source: docs/docker_quickstart.md#plotting-with-docker

# Plotting

The docs mark `plot-dataframe` and `plot-profit` as deprecated (maintenance mode, may be removed): large plots are slow, and FreqUI is the recommended way to plot.

## Dependencies (verified)

Plotly is required (`requirements-plot.txt`, plotly pinned there). Test on 2026.10:

| Image | Result |
|-------|--------|
| `freqtradeorg/freqtrade:2026.10` | `ERROR - Module plotly not found` / `ModuleNotFoundError: No module named 'plotly'` |
| `freqtradeorg/freqtrade:2026.10_freqai` | `import plotly` fails the same way |
| `freqtradeorg/freqtrade:2026.10_plot` | worked; wrote `freqtrade-plot-BTC_USDT-5m.html` and `freqtrade-profit-plot.html` to `<userdir>/plot/` |

Docs (docker quickstart): change the image to `*_plot` in `docker-compose.yml`; output goes to `user_data/plot` and opens in any browser. Native: `pip install -U -r requirements-plot.txt`.

## plot-dataframe

```bash
freqtrade plot-dataframe --strategy AwesomeStrategy -p BTC/ETH --indicators1 sma ema --indicators2 macd
freqtrade plot-dataframe --strategy AwesomeStrategy -p BTC/ETH XRP/ETH
freqtrade plot-dataframe --strategy AwesomeStrategy -p BTC/ETH --timerange=20180801-20180805
freqtrade plot-dataframe --strategy AwesomeStrategy --db-url sqlite:///tradesv3.dry_run.sqlite -p BTC/ETH --trade-source DB
```

One HTML file per pair. Needs backtest data, a strategy and a backtest result (or a trades database). Real run on 2026.10 used the latest result automatically: `freqtrade plot-dataframe --strategy IndicatorsExample -p BTC/USDT --timerange 20260801-20260805 --indicators1 ema_fast ema_slow --indicators2 rsi`.

Elements: green triangles entry signals (not every signal becomes a trade), red triangles exit signals, cyan circles trade entries, red squares losing or 0% exits, green squares profitable exits, `--indicators1` on the price plot (default `sma ema3 ema5`), volume bars, `--indicators2` in the lower plot (default `macd macdsignal`). Bollinger bands are drawn automatically when `bb_lowerband` and `bb_upperband` columns exist. With position adjustment the averaged entry price can lie outside the candle range.

## plot-profit

```bash
freqtrade plot-profit --strategy AwesomeStrategy
freqtrade plot-profit -p LTC/BTC --db-url sqlite:///tradesv3.sqlite --trade-source DB
```

Shows average close of all pairs, cumulative profit (an estimate, not real-world profit; marks max drawdown), profit per pair, trade parallelism (how often `max_open_trades` was maxed) and underwater periods. `-p` limits the pairs considered.

## plot_config

A `plot_config` property in the strategy fixes colors, adds subplots and fill areas (plotly only keys such as `plotly: {...}` are ignored by FreqUI):

```python
@property
def plot_config(self):
    return {
        "main_plot": {
            "ema_fast": {"color": "red"},
            "ema_slow": {"color": "#CCCCCC"},
        },
        "subplots": {
            "RSI": {"rsi": {"color": "red"}},
        },
    }
```

This snippet is adapted from the docs sample (shortened) and is not run by the repo tests. Other keys from the docs: `type` (`scatter` or `bar`), `fill_to`, `fill_label`, `fill_color`. Assigning `plot_config` as a class attribute still works but prevents using strategy parameters.
