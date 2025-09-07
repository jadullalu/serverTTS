# servertts/config.py
import os, sys
from pathlib import Path

APP_NAME = "ServerTTS"

# Root path (dev vs frozen/EXE)
if getattr(sys, 'frozen', False):
    ROOT_PATH = sys._MEIPASS  # type: ignore
else:
    ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Assets (dibundle)
ASSETS_DIR = os.path.join(ROOT_PATH, "assets")
HEADER_FILE = os.path.join(ASSETS_DIR, "header.mp3")
ICON_FILE   = os.path.join(ASSETS_DIR, "tts.ico")
DEFAULT_BGM = os.path.join(ASSETS_DIR, "jinggel.mp3")
ANNOUNCE_CLOSE = os.path.join(ASSETS_DIR, "pengumuman_tutup.mp3")

# VLC portable (dibundle)
VLC_DIR = os.path.join(ROOT_PATH, "portable_vlc")

# Profile user (config & cache)
CONFIG_DIR = Path.home() / "AppData" / "Roaming" / "TTS" / APP_NAME
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR = CONFIG_DIR / "cache_tts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_CACHE_FILE = CONFIG_DIR / "history.json"
HISTORY_GUI_FILE   = CONFIG_DIR / "history_gui.json"
BGM_CONFIG_FILE    = CONFIG_DIR / "bgmusic.json"

# Flask host/port
FLASK_HOST = "0.0.0.0"   # agar bisa diakses dari LAN; untuk lokal-only pakai "127.0.0.1"
FLASK_PORT = 5000

# (Opsional) API key untuk proteksi LAN (kosong = nonaktif)
API_KEY = ""  # contoh: "SECRET123"

# Single instance via local port
SINGLE_INSTANCE_PORT = 50500

# Debounce window (detik) untuk cegah klik ganda
ENQUEUE_DEBOUNCE_WINDOW = 0.75
