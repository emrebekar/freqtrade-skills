Source: docs/docker_quickstart.md#docker-quick-start
Source: docs/docker_quickstart.md#editing-the-docker-compose-file
Source: docs/docker_quickstart.md#troubleshooting

# Install and run with Docker

## Prerequisites

Install Docker Desktop (Mac, Windows) or Docker Engine (Linux) plus the `docker compose` plugin. The docs assume `docker compose`; with the standalone `docker-compose` binary replace `docker compose` by `docker-compose`. After installing Docker on Windows, reboot, otherwise containers can have unexplained network problems.

The docs do not recommend Docker on Windows for production bots, only for experimentation, data download and backtesting. Use a Linux VPS for running live.

## Quick start

```bash
mkdir ft_userdata
cd ft_userdata/
curl https://raw.githubusercontent.com/freqtrade/freqtrade/stable/docker-compose.yml -o docker-compose.yml
docker compose pull
docker compose run --rm freqtrade create-userdir --userdir user_data
docker compose run --rm freqtrade new-config --config user_data/config.json
```

All commands are run from the directory containing `docker-compose.yml`. The configuration is `user_data/config.json`. Strategies go into `user_data/strategies/`. The compose file's `command` section chooses the strategy and arguments of the running bot (SampleStrategy by default); edit it to use your strategy class name.

## Pin the image to a release tag

Always use the release these skills were tested on: `freqtradeorg/freqtrade:2026.10`, or a flavour of it (`2026.10_plot`, `2026.10_freqai`, `2026.10_freqaitorch`, `2026.10_freqairl`, `2026.10_pi`). Release tags match the GitHub releases (`gh release list -R freqtrade/freqtrade`).

Never use these tags:
- `latest`: on Docker Hub it is the same image as `develop`, an unreleased build (observed 2026-11-25: identical digests). An image name without a tag pulls `latest`.
- `develop`, `develop_*`: unreleased builds.
- `stable`, `stable_*`: move to each new release without notice, so results stop being reproducible and stop matching these skills.

The official `docker-compose.yml` uses the floating `stable` tag (the `develop` lines are commented out). After downloading it, change that line to the pinned tag:

```bash
sed -i 's#freqtrade:stable#freqtrade:2026.10#' docker-compose.yml
docker compose run --rm freqtrade --version
```

On macOS use `sed -i ''`. The version check must print `Freqtrade Version:	freqtrade 2026.10` (observed). To run a newer release, pin that exact `YYYY.M` tag instead and tell the user that commands and sample outputs in these skills were checked on the pinned release.

## Running commands

All freqtrade arguments work as `docker compose run --rm freqtrade <command> <arguments>`. `--rm` removes the container after completion and is recommended for everything except trading mode.

Trade commands (`freqtrade trade ...`) should not be run via `docker compose run`; use `docker compose up -d` instead. That starts the container properly (port forwarding) and restarts it after a reboot.

```bash
docker compose up -d
docker compose ps
docker compose pull
```

Commands that need no authentication, such as `list-pairs`, can also run without compose:

```bash
docker run --rm freqtradeorg/freqtrade:2026.10 list-pairs --exchange binance --quote BTC --print-json
```

Logs go to `user_data/logs/freqtrade.log`; the database is `user_data/tradesv3.sqlite`. Follow live logs with `docker compose logs -f` (text, not a freqtrade command).

## Examples

Download 5 days of ETH/BTC 1h data from Binance into `user_data/data/`:

```bash
docker compose run --rm freqtrade download-data --pairs ETH/BTC --exchange binance --days 5 -t 1h
```

Backtest on the 5m timeframe:

```bash
docker compose run --rm freqtrade backtesting --config user_data/config.json --strategy SampleStrategy --timerange 20190801-20191001 -i 5m
```

## Update

```bash
docker compose pull
docker compose up -d
```

Check the changelog for breaking changes before updating.

## FreqUI

If you enabled the Rest API in `new-config`, FreqUI is available on `localhost:8080`. On a remote server do not expose it directly (no https out of the box); use an ssh tunnel or a VPN. See the Rest API docs section "Configuration with docker" (docs/rest-api.md) for the listen address required inside a container.

## Extra Python dependencies

If the strategy needs packages not in the image, build a custom image: create a Dockerfile (see `docker/Dockerfile.custom` in the freqtrade repo), uncomment the `build` step in `docker-compose.yml` and rename the image to avoid a name collision, then run `docker compose build --pull`.

## Plotting

`plot-dataframe` and `plot-profit` need the `_plot` image flavour; change the image in `docker-compose.yml` to `freqtradeorg/freqtrade:2026.10_plot`. Output goes to `user_data/plot`.

## Troubleshooting (Windows)

- `Timestamp for this request is outside of the recvWindow.`: the container clock drifts in WSL. Temporary fix: `wsl --shutdown` and restart Docker Desktop. Permanent fix: run on a Linux host.
- Cannot connect to the API: reboot after installing Docker, and check the API settings.
- "Permission denied" for files created by Docker in `user_data` (Linux host): `sudo chown -R $UID:$GID user_data`.
