# Real CLI fixture

```bash
freqtrade backtesting --strategy X --timerange 20260101-
pip install freqtrade
freqtrade backtesting \
  --config user_data/config.json \
  --strategy=X -c other.json \
  --timeframe 5m --cache "none --not-checked"
docker compose run --rm freqtrade download-data --pairs BTC/USDT --timeframes 5m
docker run --rm -v "$PWD/user_data:/freqtrade/user_data" freqtradeorg/freqtrade:2026.10 list-strategies --userdir user_data
```

```console
$ freqtrade lookahead-analysis --strategy X # --bogus in comment
```

```text
freqtrade backtesting --ignored-non-shell-block
```
