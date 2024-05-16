"""The main entry point for the CalChecker command line interface."""

import json
import logging
import os

import icalendar
import requests
from cryptography.fernet import Fernet
from dotenv import find_dotenv, load_dotenv

load_dotenv(dotenv_path=find_dotenv(usecwd=True))

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] - %(message)s",
    level=logging.INFO,
)
LOGGER: logging.Logger = logging.getLogger("CALCHECKER")
CALENDAR_URL: str = os.environ["CALENDAR_URL"]
ENCRYPTION_KEY: str = os.environ["ENCRYPTION_KEY"]
STATE_FILE: str = "state.bin"


def fetch_calendar(url: str) -> icalendar.Calendar:
    res: requests.models.Response = requests.get(url, timeout=10)
    res.raise_for_status()
    return icalendar.Calendar.from_ical(res.content)


def parse_calendar(calendar: icalendar.Calendar) -> dict[str, icalendar.cal.Event]:
    return {str(event["UID"]): event for event in calendar.walk("VEVENT")}


def load_state(filename: str, key: str) -> dict[str, icalendar.cal.Event]:
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            encrypted_data = f.read()
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data).decode()
        state_serializable: dict[str, str] = json.loads(decrypted_data)
        return {
            uid: icalendar.Calendar.from_ical(event) for uid, event in state_serializable.items()
        }
    return {}


def save_state(filename: str, state: dict[str, icalendar.cal.Event], key: str) -> None:
    fernet = Fernet(key)
    state_serializable: dict[str, str] = {
        uid: event.to_ical().decode() for uid, event in state.items()
    }
    encrypted_data = fernet.encrypt(json.dumps(state_serializable).encode())
    with open(filename, "wb") as f:
        f.write(encrypted_data)


def format_event(event: icalendar.cal.Event) -> str:
    return f"{event.decoded('summary').decode()} @ {event.decoded('dtstart').isoformat()}"


def monitor_calendar(url: str, state_file: str, key: str) -> str:
    calendar_data = fetch_calendar(url)

    previous_events = load_state(state_file, key)
    current_events = parse_calendar(calendar_data)
    logs = []

    if new_events := [event for event in current_events if event not in previous_events]:
        logs.append("New events added")
        for uid in new_events:
            logs.append(format_event(current_events[uid]))

    if deleted_events := [event for event in previous_events if event not in current_events]:
        if logs:
            logs.append("")
        logs.append("Events deleted")
        for uid in deleted_events:
            logs.append(format_event(previous_events[uid]))

    # Update previous events
    # save_state(state_file, current_events, key)
    # with open(GITHUB_ENV, "a") as f:
    #     f.write(f"LOGS={logs}\n")
    return "\n".join(logs)


if __name__ == "__main__":
    print(monitor_calendar(CALENDAR_URL, STATE_FILE, ENCRYPTION_KEY))
