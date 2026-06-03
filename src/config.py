import configparser
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "tb-tdl" / "config.ini"

DEFAULTS = {
    "colors": {
        "default": "white",
        "today": "yellow",
        "tomorrow": "cyan",
        "overdue": "red",
    },
    "keybinds": {
        "add_task": "i",
        "move_down": "j",
        "move_up": "k",
        "quit": "q",
        "toggle_done": "d",
        "delete_task": "D",
        "cycle_priority": "s",
        "set_date": "a",
        "edit_title": "e",
        "toggle_panel": "c",
        "cycle_sort": "w",
        "sync": "r",
        "set_time": "t",
        "remove_date": "A",
        "remove_time": "T",
        "toggle_help": "/",
    },
    "todoist": {
        "api_key": "",
    },
}

_CHAR_TO_KEY = {
    "/": "slash",
    "\\": "backslash",
    ".": "period",
    ",": "comma",
    ";": "semicolon",
    "'": "apostrophe",
    "`": "grave_accent",
    "[": "left_square_bracket",
    "]": "right_square_bracket",
    "-": "minus",
    "=": "equals_sign",
    " ": "space",
}

def to_textual_key(key: str) -> str:
    return _CHAR_TO_KEY.get(key, key)

def load_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    for section, values in DEFAULTS.items():
        config[section] = values
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    return config

def create_default_config() -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    for section, values in DEFAULTS.items():
        config[section] = values
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
