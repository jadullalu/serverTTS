# servertts/debounce.py
import time
from . import state, config

def enqueue_allowed_once(key: str) -> bool:
    now = time.monotonic()
    if state._last_enqueue_key == key and (now - state._last_enqueue_ts) < config.ENQUEUE_DEBOUNCE_WINDOW:
        return False
    state._last_enqueue_key = key
    state._last_enqueue_ts = now
    return True
