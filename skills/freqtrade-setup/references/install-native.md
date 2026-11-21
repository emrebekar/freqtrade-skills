Source: docs/installation.md#requirements
Source: docs/installation.md#script-installation
Source: docs/installation.md#manual-installation
Source: docs/installation.md#installation-with-conda

# Native installation (without Docker)

Docker is recommended. Windows users: the docs strongly recommend Docker, or WSL (then follow the Ubuntu steps); native Windows only via `setup.ps1`. On ARM64 (Apple M1, Oracle VM) use Docker: native install there is not supported.

Requirements: Python >= 3.12 (64-bit) or `uv`, pip, git, python headers (`python3-dev`), a clock synchronized by NTP. A virtualenv is recommended.

## Get the code

```bash
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade
git checkout stable
```

`stable` is the last release; `develop` has the newest features. To match the skills in this repo use the 2026.10 release (`git checkout 2026.10`). Installing from pypi (`pip install freqtrade`) needs ta-lib installed beforehand and is not the recommended route.

## Debian/Ubuntu dependencies

```bash
sudo apt-get update
sudo apt install -y python3-pip python3-venv python3-dev python3-pandas git curl
```

macOS: `brew install gettext libomp` (the setup script does this if brew exists).

## Script installation (Linux/macOS)

```bash
./setup.sh -i
source ./.venv/bin/activate
```

`-i` installs ta-lib and creates the virtualenv under `.venv/`. Other options: `./setup.sh -u` (update: git pull + refresh venv), `./setup.sh -r` (hard reset of a `stable`/`develop` checkout and venv rebuild).

Windows (PowerShell):

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass
cd freqtrade
. .\setup.ps1
. .\.venv\Scripts\Activate.ps1
```

## Manual installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

Hyperopt dependencies are separate: `python3 -m pip install -e .[hyperopt]`.

## Conda

```bash
conda create --name freqtrade python=3.12
conda activate freqtrade
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

The docs note that pip inside conda can occasionally cause problems and prefer the `conda-forge` channel.

## First steps after install

```bash
freqtrade create-userdir --userdir user_data
freqtrade new-config --config user_data/config.json
freqtrade trade --config user_data/config.json --strategy SampleStrategy
```

Only start `trade` in dry-run (`dry_run: true`) and after backtesting plus dry-run validation; the docs warn about risking real money with the sample strategy.

## Troubleshooting

- `freqtrade: command not found`: the virtualenv is not active; run `source ./.venv/bin/activate` in every new terminal.
- Compiler errors on Windows (Microsoft Visual C++ 14.0 required): install the Visual Studio C++ build tools, or use WSL2 / Docker.
- macOS build error `command 'g++' failed`: the SDK headers are missing; see docs/installation.md for the macOS-version-specific fix.
- On a server, run the bot under Docker, `screen`/`tmux`, or systemd so it survives logout.
