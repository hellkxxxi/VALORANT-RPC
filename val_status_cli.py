import base64
import contextlib
import ctypes
import io
import json
import os
import sys
import time
from pypresence import Presence
import requests
from valclient.client import Client

DISCORD_ID = "1568110058628190228"
REGION = "eu"
APP_VERSION = "v1.0.0"

RED = "\033[38;2;255;70;85m"
CYAN = "\033[38;2;0;229;255m"
GREEN = "\033[38;2;0;255;136m"
GRAY = "\033[38;2;118;128;121m"
WHITE = "\033[38;2;236;232;225m"
RESET = "\033[0m"

BANNER = f"""{RED}
 ██╗   ██╗ █████╗ ██╗      ██████╗ ██████╗  █████╗ ███╗   ██╗████████╗      ██████╗ ██████╗  ██████╗
 ██║   ██║██╔══██╗██║     ██╔═══██╗██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝      ██╔══██╗██╔══██╗██╔════╝
 ██║   ██║███████║██║     ██║   ██║██████╔╝███████║██╔██╗ ██║   ██║   █████╗██████╔╝██████╔╝██║     
 ╚██╗ ██╔╝██╔══██║██║     ██║   ██║██╔══██╗██╔══██║██║╚██╗██║   ██║   ╚════╝██╔══██╗██╔═══╝ ██║     
  ╚████╔╝ ██║  ██║███████╗╚██████╔╝██║  ██║██║  ██║██║ ╚████║   ██║         ██║  ██║██║     ╚██████╗
   ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝         ╚═╝  ╚═╝╚═╝      ╚═════╝{RESET}
                                                                            {GRAY}{APP_VERSION} | github.com/hellkxxxi{RESET}
"""

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


def setup_console():
    os.system("cls" if os.name == "nt" else "clear")
    if os.name == "nt":
        ctypes.windll.kernel32.SetConsoleTitleW(f"VALORANT RPC {APP_VERSION}")
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    print(BANNER)


def print_status(text):
    sys.stdout.write(f"\r\033[K{text}")
    sys.stdout.flush()


def load_game_data():
    maps, agents, ranks = {}, {}, {}
    try:
        r = requests.get("https://valorant-api.com/v1/maps", timeout=5).json()
        for m in r.get("data", []):
            if m.get("mapUrl"):
                maps[m["mapUrl"].lower()] = m["displayName"]

        r = requests.get("https://valorant-api.com/v1/agents", timeout=5).json()
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


def get_valorant_presence(client):
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


def get_map_name(map_path, maps_db):
    if not map_path:
        return "Unknown Map"
    if map_path.lower() in maps_db:
        return maps_db[map_path.lower()]
    return map_path.split("/")[-1]


def get_match_details(client, state, agents_db, queue_id, total_rounds):
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

                        is_def = not starts_def if swapped else starts_def
                        side = "DEF" if is_def else "ATK"
    except:
        pass
    return agent, side


def main():
    setup_console()
    print(f" {RED}loading VALORANT database...{RESET}")
    maps_db, agents_db, ranks_db = load_game_data()

    print(f" {RED}connecting to Discord...{RESET}")
    rpc = None
    while not rpc:
        try:
            rpc = Presence(DISCORD_ID)
            rpc.connect()
        except:
            print_status(f" {CYAN}waiting for Discord...{RESET}")
            time.sleep(5)

    client = Client(region=REGION)
    val_active = False
    game_start_time = None
    wait_counter = 1

    while True:
        try:
            if not val_active:
                with (
                    contextlib.redirect_stdout(io.StringIO()),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    client.activate()
                if not getattr(client, "puuid", None):
                    raise RuntimeError()
                val_active = True

            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                presence = get_valorant_presence(client)

            if not presence:
                game_start_time = None
                print_status(
                    f" {WHITE}[{wait_counter}]{RESET} {CYAN}waiting for VALORANT...{RESET}"
                )
                wait_counter += 1
                rpc.clear()
                time.sleep(5)
                continue

            wait_counter = 1
            if game_start_time is None:
                game_start_time = int(time.time())

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
                map_name = get_map_name(map_path, maps_db)
                details = f"Agent Select | {map_name}"
                state_text = f"{mode_name} (Party: {party_size})"

                agent, _ = get_match_details(
                    client, state, agents_db, queue_id, 0
                )
                if agent:
                    small_img = agent["icon"]
                    small_txt = f"Selecting {agent['name']}"

            elif state == "INGAME":
                map_name = get_map_name(map_path, maps_db)

                if flow == "ShootingRange" or map_name == "The Range":
                    details = "The Range"
                    state_text = "Warming up..."
                else:
                    my_score = presence.get("partyOwnerMatchScoreAllyTeam", 0)
                    enemy_score = presence.get(
                        "partyOwnerMatchScoreEnemyTeam", 0
                    )
                    total_rounds = my_score + enemy_score

                    agent, side = get_match_details(
                        client, state, agents_db, queue_id, total_rounds
                    )
                    side_str = f" • {side}" if side else ""

                    details = f"{mode_name} | {map_name}"
                    state_text = f"Score: {my_score} - {enemy_score}{side_str} (Party: {party_size})"

                    if agent:
                        small_img = agent["icon"]
                        small_txt = f"Playing as {agent['name']}"
                        details = f"{agent['name']} on {map_name} ({mode_name})"
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
                start=game_start_time,
            )

            print_status(
                f" {GREEN}[ACTIVE]{RESET} {WHITE}{details}{RESET} {GRAY}|{RESET} {CYAN}{state_text}{RESET}"
            )

        except Exception:
            val_active = False
            game_start_time = None
            try:
                rpc.clear()
            except:
                pass
            print_status(
                f" {WHITE}[{wait_counter}]{RESET} {CYAN}waiting for VALORANT...{RESET}"
            )
            wait_counter += 1

        time.sleep(5)


if __name__ == "__main__":
    main()