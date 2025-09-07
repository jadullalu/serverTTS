# servertts/audio.py
import os, time, tempfile
import requests
from urllib.parse import quote
import vlc

from . import config, state
from .history import load_history_cache, save_history_cache

# pycaw untuk ducking aplikasi lain (Windows)
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume  # type: ignore
from comtypes import CLSCTX_ALL  # type: ignore

def ensure_vlc_available():
    """Pastikan VLC dll & plugins path terbaca, lalu buat instance sekali."""
    if config.VLC_DIR and os.path.exists(config.VLC_DIR):
        try:
            os.add_dll_directory(config.VLC_DIR)  # Python 3.8+
        except Exception:
            pass
        plugins_dir = os.path.join(config.VLC_DIR, "plugins")
        if os.path.isdir(plugins_dir):
            os.environ["VLC_PLUGIN_PATH"] = plugins_dir

    if state.vlc_instance is None:
        state.vlc_instance = vlc.Instance()

def set_status(text: str):
    state.status_text = text

def set_other_apps_volume(names: list[str], level: float):
    """Turunkan/naikkan volume aplikasi lain (0.0..1.0)."""
    sessions = AudioUtilities.GetAllSessions()
    for s in sessions:
        if s.Process and s.Process.name() in names:
            vol = s._ctl.QueryInterface(ISimpleAudioVolume)
            vol.SetMasterVolume(level, None)

def play_blocking_file(path: str, volume: int):
    """Pemutar blocking generik (BGM)."""
    ensure_vlc_available()
    player = state.vlc_instance.media_player_new()
    media = state.vlc_instance.media_new(path)
    player.set_media(media)
    try:
        player.audio_set_volume(max(0, min(100, volume)))
    except:
        pass
    player.play()
    while True:
        st = player.get_state()
        if st in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
            break
        time.sleep(0.05)
    try:
        player.stop()
    except:
        pass

def play_tts_blocking_file(path: str, volume: int | None = None):
    """Pemutar TTS/MP3 dengan kontrol volume real-time via state.active_tts_player."""
    ensure_vlc_available()
    player = state.vlc_instance.media_player_new()
    media = state.vlc_instance.media_new(path)
    player.set_media(media)
    try:
        vol = state.tts_volume if volume is None else int(volume)
        player.audio_set_volume(max(0, min(100, vol)))
    except:
        pass

    state.active_tts_player = player
    state.tts_active_event.set()
    player.play()
    try:
        while True:
            st = player.get_state()
            if st in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
                break
            time.sleep(0.05)
    finally:
        try:
            player.stop()
        except:
            pass
        state.active_tts_player = None
        state.tts_active_event.clear()

def download_tts_if_needed(text: str) -> str | None:
    """Kembalikan path MP3 cache untuk teks; download jika belum ada."""
    cache = load_history_cache()
    p = cache.get(text)
    if p and os.path.exists(p):
        return p

    tmp = tempfile.NamedTemporaryFile(dir=config.CACHE_DIR, delete=False, suffix=".mp3")
    tmp_path = tmp.name
    tmp.close()
    try:
        tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={quote(text)}&tl=id&client=tw-ob"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(tts_url, headers=headers, timeout=20)
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            f.write(r.content)
        cache[text] = tmp_path
        save_history_cache(cache)
        return tmp_path
    except Exception as e:
        print("[ERROR] Download TTS gagal:", e)
        try: os.remove(tmp_path)
        except: pass
        return None

def bg_music_loop():
    """Loop BGM: putar file, lalu tunggu interval dengan countdown & pause/resume."""
    while True:
        if state.stop_music_flag.is_set():
            time.sleep(0.2); continue

        if not state.music_file or not os.path.exists(state.music_file):
            time.sleep(0.5); continue

        try:
            if state.music_player:
                st_now = state.music_player.get_state()
                if st_now in (vlc.State.Playing, vlc.State.Paused, vlc.State.Opening, vlc.State.Buffering):
                    time.sleep(0.2); continue
        except:
            pass

        try:
            ensure_vlc_available()
            state.music_player = state.vlc_instance.media_player_new()
            media = state.vlc_instance.media_new(state.music_file)
            state.music_player.set_media(media)
            try:
                state.music_player.audio_set_volume(state.music_volume)
            except:
                pass
            state.music_player.play()
            set_status("Musik Jalan")
        except Exception as e:
            print("[ERROR] gagal start music:", e)
            time.sleep(1); continue

        while True:
            try: st = state.music_player.get_state()
            except: st = None
            if state.stop_music_flag.is_set():
                try: state.music_player.stop()
                except: pass
                break
            if st in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
                break
            time.sleep(0.2)

        try: state.music_player.stop()
        except: pass

        with state.interval_lock:
            state.interval_remaining = float(state.music_interval) * 60.0

        set_status("Idle")

        last = time.monotonic()
        while True:
            with state.interval_lock:
                paused = state.interval_paused
                rem = state.interval_remaining
            if state.stop_music_flag.is_set() or rem <= 0: break
            if paused:
                last = time.monotonic()
                set_status("Interval Pause")
                time.sleep(0.2); continue
            now = time.monotonic()
            delta = now - last
            last = now
            with state.interval_lock:
                state.interval_remaining = max(0.0, state.interval_remaining - delta)
            time.sleep(0.2)
