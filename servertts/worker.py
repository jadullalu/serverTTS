# servertts/worker.py
import time, os, threading, vlc
from . import state
from .history import load_history_gui, save_history_gui, append_history_gui_entry
from .audio import set_other_apps_volume, play_tts_blocking_file, download_tts_if_needed
from . import config as cfg

OTHER_APPS_DUCK = ["chrome.exe", "firefox.exe", "msedge.exe"]

def set_status(t: str):
    state.status_text = t

def refresh_history_gui_async():
    try:
        if state.root and state.root.winfo_exists() and state.history_textbox:
            state.root.after(0, lambda: state.history_textbox.event_generate("<<RefreshHistory>>"))
    except:
        pass

def enqueue_tts(item: dict):
    """Public API untuk masukkan item TTS/pengumuman ke queue + tulis GUI history."""
    text = (item.get("text") or "").strip()
    if not text: return

    entry_time = item.get("_entry_time") or time.strftime("%Y-%m-%d %H:%M:%S")

    # [local]/[down] hint di GUI
    from .history import load_history_cache
    cache = load_history_cache()
    cache_path = cache.get(text)
    is_local = bool(cache_path and os.path.exists(cache_path))
    entry_text = ("[local]+" if is_local else "[down]+") + text

    append_history_gui_entry({"time": entry_time, "text": entry_text, "status": "⏳"})
    refresh_history_gui_async()

    item["_entry_time"] = entry_time
    state.call_queue.put(item)

def tts_worker():
    while True:
        item = state.call_queue.get()
        try:
            entry_time = item.get("_entry_time")
            text = (item.get("text") or "").strip()

            # Announcement MP3
            if item.get("is_announcement") and item.get("mp3"):
                mp3_path = item["mp3"]

                music_was_playing = False
                try:
                    if state.music_player:
                        st = state.music_player.get_state()
                        if st in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering):
                            state.music_player.pause()
                            music_was_playing = True
                            time.sleep(0.05)
                except: pass

                with state.interval_lock:
                    state.interval_paused = True
                set_status("TTS Aktif")

                set_other_apps_volume(OTHER_APPS_DUCK, 0.2)

                if os.path.exists(cfg.HEADER_FILE):
                    play_tts_blocking_file(cfg.HEADER_FILE, volume=state.tts_volume)
                if os.path.exists(mp3_path):
                    play_tts_blocking_file(mp3_path, volume=state.tts_volume)

                try:
                    if state.music_player and music_was_playing:
                        if state.music_player.get_state() == vlc.State.Paused:
                            state.music_player.play()
                            state.music_player.audio_set_volume(state.music_volume)
                            set_status("Musik Jalan")
                except: pass

                set_other_apps_volume(OTHER_APPS_DUCK, 1.0)

                with state.interval_lock:
                    state.interval_paused = False

                if entry_time:
                    gui = load_history_gui()
                    for g in gui:
                        if g.get("time") == entry_time:
                            g["status"] = "✅"
                            break
                    save_history_gui(gui)
                    refresh_history_gui_async()
                time.sleep(0.5)
                continue

            # TTS text
            if not text:
                state.call_queue.task_done()
                continue

            cache_path = download_tts_if_needed(text)
            if cache_path is None:
                gui = load_history_gui()
                for g in gui:
                    if g.get("time") == entry_time:
                        g["status"] = "❌"
                        break
                save_history_gui(gui)
                refresh_history_gui_async()
                time.sleep(0.5)
                continue

            music_was_playing = False
            try:
                if state.music_player:
                    st = state.music_player.get_state()
                    if st in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering):
                        state.music_player.pause()
                        music_was_playing = True
                        time.sleep(0.05)
            except: pass

            with state.interval_lock:
                state.interval_paused = True
            set_status("TTS Aktif")

            set_other_apps_volume(OTHER_APPS_DUCK, 0.2)

            if os.path.exists(cfg.HEADER_FILE):
                play_tts_blocking_file(cfg.HEADER_FILE, volume=state.tts_volume)
            if os.path.exists(cache_path):
                play_tts_blocking_file(cache_path, volume=state.tts_volume)

            try:
                if state.music_player and music_was_playing:
                    if state.music_player.get_state() == vlc.State.Paused:
                        state.music_player.play()
                        state.music_player.audio_set_volume(state.music_volume)
                        set_status("Musik Jalan")
            except: pass

            set_other_apps_volume(OTHER_APPS_DUCK, 1.0)

            with state.interval_lock:
                state.interval_paused = False

            gui = load_history_gui()
            for g in gui:
                if g.get("time") == entry_time:
                    g["status"] = "✅"
                    break
            save_history_gui(gui)
            refresh_history_gui_async()
            time.sleep(0.5)

        finally:
            state.call_queue.task_done()

def start_worker_thread():
    threading.Thread(target=tts_worker, daemon=True).start()
