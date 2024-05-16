"""The main entry point for the CalChecker command line interface."""

import json
import os
from pathlib import Path

import icalendar
import requests
from cryptography.fernet import Fernet
from dotenv import find_dotenv, load_dotenv

load_dotenv(dotenv_path=find_dotenv(usecwd=True))

CALENDAR_URL: str = os.environ["CALENDAR_URL"]
ENCRYPTION_KEY: str = os.environ["ENCRYPTION_KEY"]
STATE_FILE: str = "state.bin"


def fetch_calendar(url: str) -> icalendar.Calendar:
    """Fetch the calendar data from the given URL."""
    res: requests.models.Response = requests.get(url, timeout=10)
    res.raise_for_status()
    return icalendar.Calendar.from_ical(res.content)


def parse_calendar(calendar: icalendar.Calendar) -> dict[str, icalendar.cal.Event]:
    """Parse the calendar data and return a dictionary of events."""
    return {str(event["UID"]): event for event in calendar.walk("VEVENT")}


def load_state(filename: str, key: str) -> dict[str, icalendar.cal.Event]:
    """Load the state from the given file and return a dictionary of events."""
    if Path(filename).exists():
        encrypted_data = Path(filename).read_bytes()
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data).decode()
        state_serializable: dict[str, str] = json.loads(decrypted_data)
        return {
            uid: icalendar.Calendar.from_ical(event) for uid, event in state_serializable.items()
        }
    return {}


def save_state(filename: str, state: dict[str, icalendar.cal.Event], key: str) -> None:
    """Save the state to the given file."""
    fernet = Fernet(key)
    state_serializable: dict[str, str] = {
        uid: event.to_ical().decode() for uid, event in state.items()
    }
    encrypted_data = fernet.encrypt(json.dumps(state_serializable).encode())
    Path(filename).write_bytes(encrypted_data)


def format_event(event: icalendar.cal.Event) -> str:
    """Format the event data for logging."""
    return f"{event.decoded('summary').decode()} @ {event.decoded('dtstart').isoformat()}"


def main(url: str, state_file: str, key: str) -> str:
    """Monitor the calendar and return the changes."""
    calendar_data = fetch_calendar(url)

    previous_events = load_state(state_file, key)
    current_events = parse_calendar(calendar_data)
    logs = []

    if new_events := [event for event in current_events if event not in previous_events]:
        logs.append("New events added")
        logs.extend(format_event(current_events[uid]) for uid in new_events)
    if deleted_events := [event for event in previous_events if event not in current_events]:
        if logs:
            logs.append("")
        logs.append("Events deleted")
        logs.extend(format_event(previous_events[uid]) for uid in deleted_events)

    save_state(state_file, current_events, key)
    return "\n".join(logs)


if __name__ == "__main__":
    LOGS = main(CALENDAR_URL, STATE_FILE, ENCRYPTION_KEY)
    print(LOGS)  # noqa: T201
