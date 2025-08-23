import json
import os

# Resolve the agent builder root (two levels up from this file)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SESSION_DIR = os.path.join(BASE_DIR, "session_data")
os.makedirs(SESSION_DIR, exist_ok=True)

def _session_path(session_id: str) -> str:
    return os.path.join(SESSION_DIR, f"{session_id}.json")

def update_session(session_id: str, key: str, value):
    session = get_session(session_id)
    session[key] = value
    with open(_session_path(session_id), "w") as f:
        json.dump(session, f)

def get_session(session_id: str):
    try:
        with open(_session_path(session_id), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
