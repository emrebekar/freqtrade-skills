---
name: x
description: Bump fixture.
license: GPL-3.0
---

# X

Pinned Freqtrade release: 2026.10. Run `docker run --rm freqtradeorg/freqtrade:2026.10_freqai --version`; it prints `freqtrade 2026.10`. Native: `git checkout 2026.10`. Pin compose: `sed -i 's#freqtrade:stable#freqtrade:2026.10#' docker-compose.yml`. Plot image `2026.10_plot`. The `ticker_interval` key was removed in 2019.9; timerange 20261001-20261101.

Built from Freqtrade docs 2026.10 (4cf0351e08d26e96a6429ef48103b726bb230cf8). Source: https://github.com/freqtrade/freqtrade/tree/2026.10/docs
