<h1 align="center">hellkai's VALORANT RPC</h1>

<p align="center">
Lightweight Discord Rich Presence client for **VALORANT** featuring a clean AMOLED interface and system tray integration.
</p>

<p align="center">
<img width="392" height="312" alt="VALORANT-RPC_VDKaNwMBKr" src="https://github.com/user-attachments/assets/71dc808e-624d-455e-9a8d-49b4b8e0c3bb" />
<p align="center">
GUI version
</p>

<p align="center">
<img width="868" height="512" alt="VALORANT-RPC-CLI_zKbSqZTk4C" src="https://github.com/user-attachments/assets/cd670fc0-cb52-4ddb-a742-88d3f5a923a6" />
<p align="center">
CLI version
</p>

<p align="center">
<img width="247" height="109" alt="vesktop_ibzqaEmaSc" src="https://github.com/user-attachments/assets/6dc1745b-053f-47a6-a5c7-ab7eeeb8db8e" />
<p align="center">
Discord RPC 
</p>

  <p align="center">
  <img src="https://img.shields.io/github/v/release/hellkxxxi/valorant-rpc?color=990000&label=version&style=flat-square">
  <img src="https://img.shields.io/github/license/hellkxxxi/valorant-rpc?color=990000&style=flat-square">
  <img src="https://img.shields.io/github/downloads/hellkxxxi/valorant-rpc/total?color=990000&style=flat-square">
</p>

## ☆ Features
- **Live Match Status:** Displays current game mode, map, live score, and party size.
- **Side Detection:** Automatically shows whether you are on **ATK** or **DEF**.
- **Agent & Rank Icons:** Shows your competitive rank in lobby and your selected agent in-game.
- **Smart Timers:** Separate elapsed timers for lobby, queue, agent select, and match duration.
- **Auto-Updated Database:** Automatically fetches new maps, agents, and ranks via `valorant-api.com`.
- - **Two Editions:**
  - **GUI Edition (`VALORANT-RPC.exe`):** Minimalist AMOLED window (`PyQt6`) that minimizes cleanly to the Windows system tray.
  - **CLI Edition (`VALORANT-RPC-CLI.exe`):** Ultra-lightweight console version with minimal resource usage.
- **100% Safe:** Uses the official local Riot Client lockfile API (does not read game memory or interact with Vanguard).

## ⌯⌲ Download & Usage
No Python installation required!
1. Go to the [**Releases**](../../releases) page and download the version you prefer:
   - `VALORANT-RPC.exe` — **AMOLED GUI + System Tray**
   - `VALORANT-RPC-CLI.exe` — **Lightweight Console**
2. Make sure **Discord** is running.
3. Run `VALORANT-RPC.exe` (before or after launching VALORANT).

## ⇣ Running from Source
If you want to run or build the script yourself:

```
pip install valclient pypresence PyQt6 requests
python val_status.py
python val_status_cli.py
```
```
pip install pyinstaller
pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." --name "VALORANT-RPC" val_status.py
pyinstaller --onefile --icon=icon.ico --exclude-module PyQt6 --name "VALORANT-RPC-CLI" val_status_cli.py
```

Сreated by **hellkai \\ hellkxxxi**
