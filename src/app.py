from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class Task:
    id: int
    title: str
    done: bool = False
    due_date: str = None
    priority: int = 4
    project: str = "Inbox"
    description: str = None
    todoist_id: str = None

STORAGE_FILE = Path.home() /".local" /"share" /"tb-tdl" /"tasks.json"
STATE_FILE = Path.home() / ".local" / "share" / "tb-tdl" / "state.json"

def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def load_tasks() -> list[Task]:
    if not STORAGE_FILE.exists():
        return []
    with open(STORAGE_FILE) as f:
        data = json.load(f)
    defaults = {"due_date": None, "priority": 4, "project": "Inbox", "description": None, "todoist_id": None}   
    return [Task(**{**defaults, **t}) for t in data]

def save_tasks(tasks: list[Task]) -> None:
    STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump([t.__dict__ for t in tasks], f)
