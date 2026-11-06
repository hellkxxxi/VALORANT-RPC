import asyncio
import base64
import ctypes
import json
import os
import sys
import time
from pypresence import Presence
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
import requests
from valclient.client import Client

DISCORD_ID = "1568110058628190228"
REGION = "eu"
APP_VERSION = "v1.0.0"

QUEUES = {
    "competitive": "Competitive",
    "unrated": "Unrated",
    "spikerush": "Spike Rush",
    "deathmatch": "Deathmatch",
    "swiftplay": "Swiftplay",
    "hurm": "Team Deathmatch",
    "ggteam": "Escalation",
    "onefa": "Replication",
    "premier": "Premier",
    "snowball": "Snowball Fight",
    "custom": "Custom Game",
}

NO_SIDE_MODES = ["deathmatch", "hurm", "ggteam", "snowball"]


def load_app_icon():
    search_dirs = []
    if hasattr(sys, "_MEIPASS"):
        search_dirs.append(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        search_dirs.append(os.path.dirname(sys.executable))
    search_dirs.append(os.path.dirname(os.path.abspath(__file__)))

    for folder in search_dirs:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.lower().endswith((".ico", ".png")):
                    return QIcon(os.path.join(folder, file))

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#000000"))
    painter.setPen(QColor("#ff4655"))
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
    painter.setFont(QFont("Segoe UI", 32, QFont.Weight.Black))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "V")
    painter.end()
    return QIcon(pixmap)


class RPCWorker(QThread):
    update_ui = pyqtSignal(str, str, str, str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.game_start_time = None

    def load_game_data(self):
        maps, agents, ranks = {}, {}, {}
        try:
            r = requests.get(
                "https://valorant-api.com/v1/maps", timeout=5
            ).json()
            for m in r.get("data", []):
                if m.get("mapUrl"):
                    maps[m["mapUrl"].lower()] = m["displayName"]

            r = requests.get(
                "https://valorant-api.com/v1/agents", timeout=5
            ).json()
            for a in r.get("data", []):
                agents[a["uuid"].lower()] = {
                    "name": a["displayName"],
                    "icon": a["displayIcon"],
                }

            r = requests.get(
                "https://valorant-api.com/v1/competitivetiers", timeout=5
            ).json()
            tiers = r.get("data", [])[-1].get("tiers", [])
            for t in tiers:
                ranks[t["tier"]] = {
                    "name": t["tierName"].title(),
                    "icon": t.get("smallIcon"),
                }
        except:
            pass
        return maps, agents, ranks

    def get_valorant_presence(self, client):
        presences = client.fetch_all_friend_presences()
        for p in presences.get("presences", []):
            if p.get("puuid") == client.puuid and p.get("product") == "valorant":
                private_b64 = p.get("private")
                if not private_b64:
                    continue
                raw_json = base64.b64decode(private_b64 + "===").decode("utf-8")
                data = json.loads(raw_json)

                flat = dict(data)
                for folder in [
                    "matchPresenceData",
                    "partyPresenceData",
                    "playerPresenceData",
                    "premierPresenceData",
                ]:
                    if isinstance(data.get(folder), dict):
                        flat.update(data[folder])

                party_data = data.get("partyPresenceData", {})
                if isinstance(party_data, dict) and isinstance(
                    party_data.get("matchmakingData"), dict
                ):
                    if not flat.get("queueId"):
                        flat["queueId"] = party_data["matchmakingData"].get(
                            "queueId", ""
                        )
                return flat
        return None

    def get_map_name(self, map_path, maps_db):
        if not map_path:
            return "Unknown Map"
        if map_path.lower() in maps_db:
            return maps_db[map_path.lower()]
        return map_path.split("/")[-1]

    def get_match_details(
        self, client, state, agents_db, queue_id, total_rounds
    ):
        agent = None
        side = None
        try:
            if state == "PREGAME":
                match_id = client.pregame_fetch_player()["MatchID"]
                match = client.pregame_fetch_match(match_id)
                for p in match["AllyTeam"]["Players"]:
                    if p["Subject"] == client.puuid and p.get("CharacterID"):
                        agent = agents_db.get(p["CharacterID"].lower())
            elif state == "INGAME":
                match_id = client.coregame_fetch_player()["MatchID"]
                match = client.coregame_fetch_match(match_id)
                for p in match["Players"]:
                    if p["Subject"] == client.puuid:
                        if p.get("CharacterID"):
                            agent = agents_db.get(p["CharacterID"].lower())

                        team = p.get("TeamID")
                        if (
                            team in ["Blue", "Red"]
                            and queue_id not in NO_SIDE_MODES
                        ):
                            starts_def = team == "Blue"
                            if queue_id == "swiftplay":
                                swapped = total_rounds >= 4
                            elif queue_id == "spikerush":
                                swapped = total_rounds >= 3
                            else:
                                if total_rounds < 12:
                                    swapped = False
                                elif total_rounds < 24:
                                    swapped = True
                                else:
                                    swapped = (total_rounds - 24) % 2 == 1

                            is_def = (
                                not starts_def if swapped else starts_def
                            )
                            side = "DEF" if is_def else "ATK"
        except:
            pass
        return agent, side

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.update_ui.emit("Loading database...", "Please wait", "...", "")
        maps_db, agents_db, ranks_db = self.load_game_data()

        rpc = None
        while self.running and not rpc:
            try:
                rpc = Presence(DISCORD_ID)
                rpc.connect()
            except:
                self.update_ui.emit(
                    "Waiting for Discord...",
                    "Discord not detected",
                    "Make sure Discord is open",
                    "",
                )
                time.sleep(5)

        client = Client(region=REGION)
        val_active = False
        wait_counter = 1

        while self.running:
            try:
                if not val_active:
                    client.activate()
                    val_active = True

                presence = self.get_valorant_presence(client)

                if not presence:
                    self.game_start_time = None
                    self.update_ui.emit(
                        f"[{wait_counter}] waiting for VALORANT...",
                        "Not in game",
                        "Launch VALORANT to start RPC",
                        "",
                    )
                    wait_counter += 1
                    rpc.clear()
                    time.sleep(5)
                    continue

                wait_counter = 1
                if self.game_start_time is None:
                    self.game_start_time = int(time.time())

                state = presence.get("sessionLoopState", "MENUS")
                flow = presence.get("provisioningFlow", "")
                queue_id = presence.get("queueId", "")
                map_path = presence.get("matchMap", "")

                party_size = presence.get("partySize", 1)
                max_party = presence.get("maxPartySize", 5)
                party_state = presence.get("partyState", "")

                if (
                    flow == "CustomGame"
                    or queue_id == "custom"
                    or "CUSTOM" in party_state.upper()
                ):
                    mode_name = "Custom Game"
                else:
                    mode_name = QUEUES.get(
                        queue_id, queue_id.capitalize() if queue_id else "Unrated"
                    )

                rank_tier = presence.get("competitiveTier", 0)
                rank_info = ranks_db.get(rank_tier)

                small_img = None
                small_txt = ""

                if rank_info and rank_tier > 0:
                    small_img = rank_info["icon"]
                    small_txt = f"Rank: {rank_info['name']}"

                if state == "MENUS":
                    if party_state == "MATCHMAKING":
                        details = f"In Queue ({mode_name})"
                    elif "CUSTOM" in party_state.upper():
                        details = "In Custom Game Lobby"
                    else:
                        details = f"In Lobby ({mode_name})"
                    state_text = f"Party: {party_size} of {max_party}"

                elif state == "PREGAME":
                    map_name = self.get_map_name(map_path, maps_db)
                    details = f"Agent Select | {map_name}"
                    state_text = f"{mode_name} (Party: {party_size})"

                    agent, _ = self.get_match_details(
                        client, state, agents_db, queue_id, 0
                    )
                    if agent:
                        small_img = agent["icon"]
                        small_txt = f"Selecting {agent['name']}"

                elif state == "INGAME":
                    map_name = self.get_map_name(map_path, maps_db)

                    if flow == "ShootingRange" or map_name == "The Range":
                        details = "The Range"
                        state_text = "Warming up..."
                    else:
                        my_score = presence.get(
                            "partyOwnerMatchScoreAllyTeam", 0
                        )
                        enemy_score = presence.get(
                            "partyOwnerMatchScoreEnemyTeam", 0
                        )
                        total_rounds = my_score + enemy_score

                        agent, side = self.get_match_details(
                            client, state, agents_db, queue_id, total_rounds
                        )
                        side_str = f" • {side}" if side else ""

                        details = f"{mode_name} | {map_name}"
                        state_text = f"Score: {my_score} - {enemy_score}{side_str} (Party: {party_size})"

                        if agent:
                            small_img = agent["icon"]
                            small_txt = f"Playing as {agent['name']}"
                            details = (
                                f"{agent['name']} on {map_name} ({mode_name})"
                            )
                else:
                    details = "In Menu"
                    state_text = f"Party: {party_size} of {max_party}"

                rpc.update(
                    details=details,
                    state=state_text,
                    large_image="logo",
                    large_text="VALORANT",
                    small_image=small_img,
                    small_text=small_txt if small_txt else None,
                    start=self.game_start_time,
                )

                self.update_ui.emit("ACTIVE", details, state_text, small_txt)

            except Exception:
                val_active = False
                self.game_start_time = None
                try:
                    rpc.clear()
                except:
                    pass
                self.update_ui.emit(
                    f"[{wait_counter}] waiting for VALORANT...",
                    "Not in game",
                    "Launch VALORANT to start RPC",
                    "",
                )
                wait_counter += 1

            time.sleep(5)


class MainWindow(QMainWindow):

    def __init__(self, icon):
        super().__init__()
        self.app_icon = icon
        self.setWindowTitle(f"VALORANT RPC {APP_VERSION}")
        self.setWindowIcon(self.app_icon)
        self.setFixedSize(390, 280)

        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(self.winId()), 20, ctypes.byref(ctypes.c_int(1)), 4
            )
        except:
            pass

        self.setStyleSheet("""
            QMainWindow { background-color: #000000; }
            QLabel#Header {
                color: #ff4655;
                font-family: 'Segoe UI', sans-serif;
                font-size: 21px;
                font-weight: 900;
                letter-spacing: 2px;
            }
            QLabel#Version {
                color: #555555;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QLabel#ConnStatus {
                color: #00e5ff;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                font-weight: bold;
            }
            QFrame#Card {
                background-color: #0a0a0c;
                border: 1px solid #1c1c21;
                border-left: 4px solid #ff4655;
                border-radius: 6px;
            }
            QLabel#CardTitle {
                color: #555555;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLabel#Details {
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#State {
                color: #b5bac1;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLabel#Extra {
                color: #ff4655;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QLabel#Timer {
                color: #23a55a;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0d0d10;
                color: #ece8e1;
                border: 1px solid #222228;
                border-radius: 4px;
                padding: 7px;
                font-weight: bold;
                font-size: 12px;
                outline: none;
            }
            QPushButton:hover {
                background-color: #ff4655;
                border-color: #ff4655;
                color: #ffffff;
            }
            QLabel#GithubLink {
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 14, 20, 12)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        self.header_lbl = QLabel("VALORANT-RPC")
        self.header_lbl.setObjectName("Header")
        self.ver_lbl = QLabel(APP_VERSION)
        self.ver_lbl.setObjectName("Version")
        header_layout.addWidget(self.header_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.ver_lbl)
        layout.addLayout(header_layout)

        self.conn_lbl = QLabel("[1] waiting for VALORANT...")
        self.conn_lbl.setObjectName("ConnStatus")
        layout.addWidget(self.conn_lbl)

        self.card = QFrame()
        self.card.setObjectName("Card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(3)

        self.card_title = QLabel("DISCORD RICH PRESENCE PREVIEW")
        self.card_title.setObjectName("CardTitle")
        self.details_lbl = QLabel("Initializing...")
        self.details_lbl.setObjectName("Details")
        self.state_lbl = QLabel("...")
        self.state_lbl.setObjectName("State")

        bottom_card_layout = QHBoxLayout()
        self.extra_lbl = QLabel("")
        self.extra_lbl.setObjectName("Extra")
        self.timer_lbl = QLabel("")
        self.timer_lbl.setObjectName("Timer")
        bottom_card_layout.addWidget(self.extra_lbl)
        bottom_card_layout.addStretch()
        bottom_card_layout.addWidget(self.timer_lbl)

        card_layout.addWidget(self.card_title)
        card_layout.addWidget(self.details_lbl)
        card_layout.addWidget(self.state_lbl)
        card_layout.addLayout(bottom_card_layout)
        layout.addWidget(self.card)

        btn_layout = QHBoxLayout()
        self.tray_btn = QPushButton("HIDE TO TRAY")
        self.tray_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tray_btn.clicked.connect(self.hide)

        self.quit_btn = QPushButton("QUIT")
        self.quit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.quit_btn.clicked.connect(self.quit_app)

        btn_layout.addWidget(self.tray_btn)
        btn_layout.addWidget(self.quit_btn)
        layout.addLayout(btn_layout)

        self.github_lbl = QLabel(
            '<a href="https://github.com/hellkxxxi" style="color: #666666; text-decoration: none;">github.com/hellkxxxi</a>'
        )
        self.github_lbl.setObjectName("GithubLink")
        self.github_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.github_lbl.setOpenExternalLinks(True)
        layout.addWidget(self.github_lbl)

        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip(f"VALORANT RPC {APP_VERSION}")

        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_click)
        self.tray_icon.show()

        self.worker = RPCWorker()
        self.worker.update_ui.connect(self.on_status_update)
        self.worker.start()

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self.update_elapsed_time)
        self.ui_timer.start(1000)

    def update_elapsed_time(self):
        if self.worker.game_start_time:
            elapsed = int(time.time()) - self.worker.game_start_time
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            if hours > 0:
                self.timer_lbl.setText(f"{hours}:{mins:02d}:{secs:02d}")
            else:
                self.timer_lbl.setText(f"{mins:02d}:{secs:02d}")
        else:
            self.timer_lbl.setText("")

    def on_status_update(self, conn_status, details, state, extra):
        self.conn_lbl.setText(conn_status)
        if conn_status == "ACTIVE":
            self.conn_lbl.setStyleSheet(
                "color: #00ff88; font-family: 'Consolas', monospace; font-size: 13px; font-weight: bold;"
            )
        else:
            self.conn_lbl.setStyleSheet(
                "color: #00e5ff; font-family: 'Consolas', monospace; font-size: 13px; font-weight: bold;"
            )

        self.details_lbl.setText(details)
        self.state_lbl.setText(state)
        self.extra_lbl.setText(extra)
        self.update_elapsed_time()

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def quit_app(self):
        self.worker.running = False
        self.tray_icon.hide()
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    icon = load_app_icon()
    window = MainWindow(icon)
    window.show()
    sys.exit(app.exec())