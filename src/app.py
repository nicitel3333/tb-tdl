from dataclasses import dataclass
import json
from pathlib import Path

class Task:
    def __init__(self,id, title, done=False):
        self.id = id
        self.title = title
        self.done = done
        
STORAGE_FILE = Path.home() /".local" /"share" /"tb-tdl" /"tasks.json"

def load_tasks() -> list[Task]:
    if not STORAGE_FILE.exists():
        return []
    with open(STORAGE_FILE) as f:
        data = json.load(f)
    return [Task(**t) for t in data]

def save_tasks(tasks: list[Task]) -> None:
    STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump([t.__dict__ for t in tasks], f)
