# VALORANT-RPC

Lightweight Discord Rich Presence client for **VALORANT** featuring a clean AMOLED interface and system tray integration.

<img width="392" height="312" alt="VALORANT-RPC_VDKaNwMBKr" src="https://github.com/user-attachments/assets/71dc808e-624d-455e-9a8d-49b4b8e0c3bb" />
<img width="247" height="109" alt="vesktop_ibzqaEmaSc" src="https://github.com/user-attachments/assets/6dc1745b-053f-47a6-a5c7-ab7eeeb8db8e" />

## ✨ Features
- **Live Match Status:** Displays current game mode, map, live score, and party size.
- **Side Detection:** Automatically shows whether you are on **ATK** or **DEF**.
- **Agent & Rank Icons:** Shows your competitive rank in lobby and your selected agent in-game.
- **Smart Timers:** Separate elapsed timers for lobby, queue, agent select, and match duration.
- **Auto-Updated Database:** Automatically fetches new maps, agents, and ranks via `valorant-api.com`.
- **AMOLED UI & System Tray:** Minimalist dark window (`PyQt6`) that minimizes cleanly to the Windows tray.
- **100% Safe:** Uses the official local Riot Client lockfile API (does not read game memory or interact with Vanguard).

## 🚀 Download & Usage
No Python installation required!
1. Go to the [**Releases**](../../releases) page and download the latest `VALORANT-RPC.exe`.
2. Make sure **Discord** is running.
3. Run `VALORANT-RPC.exe` (before or after launching VALORANT).

## 🛠️ Running from Source
If you want to run or build the script yourself:

```
pip install valclient pypresence PyQt6 requests
python val_status.py
```
```
pip install pyinstaller
pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." --name "VALORANT-RPC" val_status.py
```

Сreated by **hellkai \\ hellkxxxi**
