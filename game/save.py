"""Progress and settings, stored as JSON next to the game."""
import json
import os

from .settings import SAVE_PATH

_data = None


def _default():
    return {"unlocked": 1, "levels": {}, "settings": {"music": 0.5, "sfx": 0.7, "fullscreen": False}, "finished": False}


def data():
    global _data
    if _data is None:
        _data = _default()
        try:
            with open(SAVE_PATH, encoding="utf-8") as f:
                loaded = json.load(f)
            _data.update(loaded)
        except (OSError, ValueError):
            pass
    return _data


def write():
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data(), f, indent=1)
    except OSError:
        pass


def key(path):
    return os.path.basename(path)


def level_record(path):
    return data()["levels"].get(key(path))


def record_level(path, seconds, gems, rank, coins, score):
    """Store a clear. Returns True if it is a new best time."""
    d = data()
    k = key(path)
    rec = d["levels"].get(k)
    order = "CBAS"
    new_best = rec is None or seconds < rec.get("time", 1e9)
    if rec is None:
        rec = {"time": seconds, "gems": sorted(gems), "rank": rank, "coins": coins, "score": score}
    else:
        rec["time"] = min(rec.get("time", 1e9), seconds)
        rec["gems"] = sorted(set(rec.get("gems", [])) | set(gems))
        if order.index(rank) > order.index(rec.get("rank", "C")):
            rec["rank"] = rank
        rec["coins"] = max(rec.get("coins", 0), coins)
        rec["score"] = max(rec.get("score", 0), score)
    d["levels"][k] = rec
    write()
    return new_best


def unlock(n):
    d = data()
    if n > d["unlocked"]:
        d["unlocked"] = n
        write()
