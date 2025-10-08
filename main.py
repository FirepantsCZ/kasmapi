from dotenv import load_dotenv
from os import getenv
from zoneinfo import ZoneInfo

from kasmapi.exceptions import UsageQuotaReachedException
from kasmapi.kasm import Kasm

TIMEZONE = ZoneInfo("Europe/Prague")
DEFAULT_HOURS = 6

load_dotenv()

BASE_URL = "https://kasm.krabice.online"  # e.g. https://kasm.example.com
API_KEY = getenv("API_KEY")
API_KEY_SECRET = getenv("API_KEY_SECRET")

kasm = Kasm(BASE_URL, API_KEY, API_KEY_SECRET)

def main():
    # Fetch sessions
    sessions = kasm.get_sessions()

    if not sessions:
        print("No active or paused sessions found.")
        return

    # Display list
    print("\nAvailable sessions:")
    for i, s in enumerate(sessions, 1):
        print(f"[{i}] {s.start_date} - {s.image.friendly_name} (state: {s.operational_status})")

    choice = input(f"\nSelect session to extend (number)[1]: ")
    session = sessions[int(choice) - 1 if choice else 0]

    # Get the user of chosen session
    user_group = kasm.get_user(session.user_id, session.username).groups[0]

    # Fetch default session expiration time
    keepalive_setting = user_group.get_setting("keepalive_expiration")
    old_keepalive = keepalive_setting.value

    # Ask how many hours to extend
    extra_hours = input(f"New expiration time (in hours)[{DEFAULT_HOURS}]: ")

    keepalive_setting.set_value((int(extra_hours) if extra_hours else DEFAULT_HOURS) * 60 * 60)

    # Reset keepalive for session
    try:
        session.keepalive()
    except UsageQuotaReachedException:
        print("ERROR: Session not modified, usage quota reached!")
        keepalive_setting.set_value(old_keepalive)
        return

    keepalive_setting.set_value(old_keepalive)

    print("✅ Session expiration updated successfully!")

if __name__ == "__main__":
    main()
