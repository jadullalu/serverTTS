# servertts/history.py
import os, json
from . import config

def load_history_cache():
    if config.HISTORY_CACHE_FILE.exists():
        try:
            with open(config.HISTORY_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except:
            pass
    return {}

def save_history_cache(d: dict):
    try:
        with open(config.HISTORY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[ERROR] save_history_cache:", e)

def load_history_gui():
    if config.HISTORY_GUI_FILE.exists():
        try:
            with open(config.HISTORY_GUI_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except:
            pass
    return []

def save_history_gui(lst: list):
    try:
        with open(config.HISTORY_GUI_FILE, "w", encoding="utf-8") as f:
            json.dump(lst, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[ERROR] save_history_gui:", e)

def append_history_gui_entry(entry: dict):
    lst = load_history_gui()
    lst.append(entry)
    save_history_gui(lst)

def clear_history_gui():
    save_history_gui([])

def cleanup_cache_and_json(update_gui=True) -> int:
    count = 0
    for f in os.listdir(config.CACHE_DIR):
        if f.endswith(".mp3") or f.endswith(".json"):
            p = config.CACHE_DIR / f
            try:
                p.unlink(); count += 1
            except Exception as e:
                print(f"[WARN] gagal hapus {p}: {e}")

    for jf in [config.HISTORY_CACHE_FILE, config.HISTORY_GUI_FILE, config.CONFIG_DIR / "history.json"]:
        try:
            if jf.exists():
                jf.unlink(); count += 1
        except Exception as e:
            print(f"[WARN] gagal hapus {jf}: {e}")

    if update_gui:
        try:
            save_history_gui([])
        except Exception as e:
            print(f"[WARN] failed updating history_gui: {e}")
    return count
