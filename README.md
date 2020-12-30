# RadBot
Radix Telegram Bot

### Prerequisites
1. Install [Python 3.x](https://www.python.org/downloads/) and make sure it's in PATH.
1. Register an [Infura](https://infura.io/) API account and create a new Ethereum Project.
1. Set up a [Telegram Bot](https://core.telegram.org/bots) and obtain the bot API token.

### Setup
1. Install project dependencies `python -m pip install -r requirements.txt`.
1. Create a file called `infura.json` with your Infura Project ID (see `infura.example.json`).
1. Create `RadBotToken.json` with your Telegram Bot token (see `RadBotToken.example.json`).
1. Run `python rewards.py` - this will prefetch the historical data into file `stake.h5`.
1. Run the Bot! `python RadBot.py`.

### Other
* HDF5 does not cleanup deleted data from the file automatically (see [here](https://pandas.pydata.org/pandas-docs/stable/user_guide/io.html#delete-from-a-table)).
  You need to compact it manually
  ```bash
  ptrepack --chunkshape=auto --propindexes --complevel=0 --complib=blosc stake.h5 stake_new.h5
  ```
  and then
  ```bash
  mv -f stake_new.h5 stake.h5
  ```
