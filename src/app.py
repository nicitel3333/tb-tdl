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

STORAGE_FILE = Path.home() /".local" /"share" /"tb-tdl" /"tasks.json"

def load_tasks() -> list[Task]:
    if not STORAGE_FILE.exists():
        return []
    with open(STORAGE_FILE) as f:
        data = json.load(f)
    defaults = {"due_date": None, "priority": 4, "project": "Inbox", "description": None}
    return [Task(**{**defaults, **t}) for t in data]

def save_tasks(tasks: list[Task]) -> None:
    STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump([t.__dict__ for t in tasks], f)
