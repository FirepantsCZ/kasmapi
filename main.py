import requests
import getpass
from dotenv import load_dotenv
from os import getenv
from dataclasses import dataclass
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Europe/Prague")
ALL_USERS_GROUP_ID = "68d557ac4cac42cca9f31c7c853de0f3"
DEFAULT_HOURS = 6

load_dotenv()

BASE_URL = "https://kasm.krabice.online"  # e.g. https://kasm.example.com
USERNAME = getenv("USERNAME")
ADMIN_TOKEN = getenv("ADMIN_TOKEN")
API_KEY = getenv("API_KEY")
API_KEY_SECRET = getenv("API_KEY_SECRET")

def set_keepalive(group_id, group_setting_id, value):
    update_resp = requests.post(
        f"{BASE_URL}/api/admin/update_settings_group",
        json=get_json({
            "target_group": {
                "group_id": group_id,
            },
            "target_setting": {
                "group_setting_id": group_setting_id,
                "value": value,
            }
        }),
        verify=True
    )
    update_resp.raise_for_status()

def get_json(request_json = None, admin = False):
    if admin:
        result = {
            "username": USERNAME,
            "token": ADMIN_TOKEN,
        }
    else:
        result = {
            "api_key": API_KEY,
            "api_key_secret": API_KEY_SECRET,
        }
    if request_json:
        result.update(request_json)
    return result

def main():
    # ---- Fetch sessions ----
    sessions_resp = requests.post(
        f"{BASE_URL}/api/public/get_kasms",
        verify=True,
        json=get_json(),
    )
    sessions_resp.raise_for_status()
    sessions = sessions_resp.json()["kasms"]

    if not sessions:
        print("No active or paused sessions found.")
        return

    # Fetch default session expiration time
    keepalive_resp = requests.post(
        f"{BASE_URL}/api/admin/get_settings_group",
        verify=True,
        json=get_json({"target_group": {"group_id": ALL_USERS_GROUP_ID}}),
    )
    keepalive_resp.raise_for_status()
    keepalive = (keepalive_setting := next(filter(lambda setting: setting['name'] == "keepalive_expiration", keepalive_resp.json()['settings'])))['value']

    if keepalive_setting['group_id'] != ALL_USERS_GROUP_ID:
        print('ERROR')
        return

    # ---- Display list ----
    print("\nAvailable sessions:")
    for i, s in enumerate(sessions, 1):
        print(f"[{i}] {s['start_date']} - {s['image']['friendly_name']} (state: {s['operational_status']})")

    choice = input(f"\nSelect session to extend (number)[1]: ")
    session_id = sessions[int(choice) - 1 if choice else 0]['kasm_id']

    # ---- Ask how many hours to extend ----
    extra_hours = input(f"New expiration time (in hours)[{DEFAULT_HOURS}]: ")

    set_keepalive(ALL_USERS_GROUP_ID, keepalive_setting['group_setting_id'], (int(extra_hours) if extra_hours else DEFAULT_HOURS)*60*60)

    # ---- Update session ----
    update_resp = requests.post(
        f"{BASE_URL}/api/public/keepalive",
        json=get_json({"kasm_id": session_id}),
        verify=True
    )
    update_resp.raise_for_status()
    if update_resp.json()['usage_reached']:
        print("ERROR: Session not modified, usage quota reached!")
        set_keepalive(session_id, keepalive_setting['group_setting_id'], keepalive)
        return

    set_keepalive(session_id, keepalive_setting['group_setting_id'], keepalive)

    print("✅ Session expiration updated successfully!")

if __name__ == "__main__":
    main()
