import json
import os
import threading
LOCK = threading.Lock()
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
FILES = {
    "economy": "economy.json",
    "levels": "levels.json",
    "warns": "warns.json",
    "automod": "automod.json",
    "invites": "invites.json",
    "tickets": "tickets.json",
    "settings": "settings.json",
    "blacklist": "blacklist.json",
}
def _path(name):
    return os.path.join(DATA_DIR, FILES[name])
def load(name):
    path = _path(name)
    if not os.path.exists(path):
        return {}
    with LOCK:
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
def save(name, data):
    path = _path(name)
    with LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
def get_user_economy(guild_id, user_id):
    data = load("economy")
    g = data.setdefault(str(guild_id), {})
    u = g.setdefault(str(user_id), {
        "balance": 0,
        "luck": 0,
        "inventory": {},
        "last_work": 0,
        "last_daily": 0,
        "last_luckybox": 0,
        "last_mine": 0,
        "last_lucky": 0,
    })
    return data, u
def get_user_levels(guild_id, user_id):
    data = load("levels")
    g = data.setdefault(str(guild_id), {})
    u = g.setdefault(str(user_id), {"messages": 0, "level": 0})
    return data, u
