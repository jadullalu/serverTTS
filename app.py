# app.py
import os, sys, logging, threading, gzip, shutil
from logging.handlers import RotatingFileHandler

from servertts import config, state
from servertts.audio import bg_music_loop, ensure_vlc_available
from servertts.server import start_flask_thread
from servertts.worker import start_worker_thread
from servertts.gui import run_gui

# ---- logging rotasi + kompres .gz (tanpa console) ----
LOG_DIR = os.path.join(config.CONFIG_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "latest.txt")

def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)

    max_bytes = 5 * 1024 * 1024   # 5 MB
    backup_count = 7
    fh = RotatingFileHandler(LOG_FILE, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")

    def _namer(name: str) -> str: return name + ".gz"
    def _rotator(src: str, dst: str):
        with open(src, "rb") as sf, gzip.open(dst, "wb", compresslevel=6) as df:
            shutil.copyfileobj(sf, df)
        try: os.remove(src)
        except OSError: pass

    fh.namer = _namer
    fh.rotator = _rotator
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(fh)

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    def _excepthook(exc_type, exc, tb):
        root.error("Uncaught exception", exc_info=(exc_type, exc, tb))
    sys.excepthook = _excepthook

def main():
    # cegah instance ganda
    try:
        guard_sock = state.single_instance_guard()
        _ = guard_sock
    except SystemExit as e:
        setup_logging()
        logging.error(str(e))
        return

    setup_logging()
    logging.info("== ServerTTS starting ==")

    ensure_vlc_available()
    state.load_bgm_config()

    # background loops
    threading.Thread(target=bg_music_loop, daemon=True).start()
    start_worker_thread()
    start_flask_thread()  # menulis info host/port ke log

    # GUI + tray
    run_gui()

if __name__ == "__main__":
    main()
