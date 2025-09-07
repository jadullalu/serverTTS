# servertts/state.py
import os, json, socket
import threading
from queue import Queue
from flask import Flask
from . import config

app = Flask(__name__)

# Queues & flags
call_queue: "Queue[dict]" = Queue()
pending_entries = []

# BGM & TTS volumes
music_player = None
music_file: str | None = None
music_interval = 5
music_volume = 100   # BGM volume
tts_volume = 100     # TTS/MP3 volume
interval_lock = threading.Lock()
stop_music_flag = threading.Event()
interval_remaining = 0.0
interval_paused = False

# Active TTS tracking (untuk slider TTS realtime)
active_tts_player = None
tts_active_event = threading.Event()

# UI state
status_text = "Idle"
root = None
status_var = None
countdown_var = None
history_textbox = None

# VLC instance
vlc_instance = None

# Debounce key/time
_last_enqueue_key: str | None = None
_last_enqueue_ts: float = 0.0

def load_bgm_config():
    """Load/init BGM, interval, volume & tts volume"""
    global music_file, music_interval, music_volume, tts_volume, interval_remaining
    default_interval = 5 if getattr(__import__("sys"), 'frozen', False) else 1
    default_volume = 100
    default_tts_volume = 100
    default_file = config.DEFAULT_BGM

    if os.path.exists(config.BGM_CONFIG_FILE):
        try:
            with open(config.BGM_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                music_file = cfg.get("file", default_file)
                music_interval = int(cfg.get("interval", default_interval))
                music_volume = int(cfg.get("volume", default_volume))
                tts_volume   = int(cfg.get("tts_volume", default_tts_volume))
        except:
            music_file = default_file
            music_interval = default_interval
            music_volume = default_volume
            tts_volume = default_tts_volume
            save_bgm_config()
    else:
        music_file = default_file
        music_interval = default_interval
        music_volume = default_volume
        tts_volume = default_tts_volume
        save_bgm_config()

    if not os.path.exists(music_file):
        music_file = default_file

    music_volume = min(max(music_volume, 0), 100)
    tts_volume   = min(max(tts_volume, 0), 100)

    with interval_lock:
        interval_remaining = 0.0

def save_bgm_config():
    cfg = {
        "file": music_file,
        "interval": music_interval,
        "volume": music_volume,
        "tts_volume": tts_volume,
    }
    try:
        with open(config.BGM_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("[WARN] save_bgm_config:", e)

def single_instance_guard():
    """Stop jika sudah ada instance lain (bind ke port lokal)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", config.SINGLE_INSTANCE_PORT))
    except OSError:
        raise SystemExit("Aplikasi sudah berjalan!")
    return s  # simpan agar socket tetap terbuka
