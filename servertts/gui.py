# servertts/gui.py
import os, time, re, tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import pystray
from PIL import Image, ImageDraw
import threading
import vlc

from . import state, config
from .debounce import enqueue_allowed_once
from .history import (
    append_history_gui_entry, load_history_gui, clear_history_gui,
    cleanup_cache_and_json
)
from .worker import enqueue_tts

def set_status(text:str):
    state.status_text = text

def refresh_history_gui():
    if state.history_textbox is None:
        return
    try:
        history = load_history_gui()
        try:
            at_bottom = state.history_textbox.yview()[1] >= 0.999
        except:
            at_bottom = True
        state.history_textbox.config(state="normal")
        state.history_textbox.delete("1.0", tk.END)
        for item in history:
            mark = item.get("status", "⏳")
            t = item.get("time", "")
            txt = item.get("text", "")
            state.history_textbox.insert(tk.END, f"{t} {mark} {txt}\n")
        state.history_textbox.config(state="disabled")
        if at_bottom:
            state.history_textbox.yview_moveto(1.0)
    except Exception as e:
        print("[WARN] refresh_history_gui:", e)

def _bind_refresh_event(widget):
    widget.bind("<<RefreshHistory>>", lambda e: refresh_history_gui())

def on_clear_cache():
    c = cleanup_cache_and_json()
    messagebox.showinfo("Cache", f"{c} file cache dihapus", parent=state.root)

def on_select_music():
    path = filedialog.askopenfilename(title="Pilih Musik", filetypes=[("MP3", "*.mp3")])
    if path:
        state.music_file = path
        state.save_bgm_config()
        messagebox.showinfo("OK", f"Musik diset: {state.music_file}", parent=state.root)

def create_fallback_icon():
    img = Image.new('RGB', (64, 64), color='blue')
    d = ImageDraw.Draw(img)
    d.text((10, 25), "TTS", fill="white")
    return img

def tray_show_gui(icon, item):
    try:
        if state.root:
            state.root.deiconify()
            state.root.lift()
    except:
        pass

def tray_exit(icon, item):
    state.stop_music_flag.set()
    try:
        if state.root:
            state.root.destroy()
    except:
        pass
    icon.stop()
    os._exit(0)

def run_gui():
    last_announcement_path = None

    state.root = tk.Tk()
    state.root.title("Server TTS")
    state.root.geometry("780x600")
    try:
        state.root.iconbitmap(config.ICON_FILE)
    except Exception as e:
        print("[WARN] gagal set icon GUI:", e)

    state.root.protocol("WM_DELETE_WINDOW", lambda: state.root.withdraw())

    # top bar
    frame_top = tk.Frame(state.root); frame_top.pack(fill="x", padx=8, pady=6)
    state.status_var = tk.StringVar(value=f"Status: {state.status_text}")
    tk.Label(frame_top, textvariable=state.status_var, font=("Segoe UI", 11), fg="blue").pack(side="left", padx=(0,10))
    state.countdown_var = tk.StringVar(value="Interval: --s")
    tk.Label(frame_top, textvariable=state.countdown_var, font=("Segoe UI", 11)).pack(side="left")
    tk.Button(frame_top, text="Clear Cache", command=on_clear_cache).pack(side="right", padx=4)
    tk.Button(frame_top, text="Hapus History GUI", command=lambda:(clear_history_gui(), refresh_history_gui())).pack(side="right", padx=4)

    # history panel
    lf = tk.LabelFrame(state.root, text="Histori Panggilan (GUI)")
    lf.pack(fill="both", expand=True, padx=8, pady=(0,8))
    state.history_textbox = scrolledtext.ScrolledText(lf, wrap=tk.WORD, state="disabled", font=("Segoe UI", 10))
    state.history_textbox.pack(fill="both", expand=True)
    _bind_refresh_event(state.history_textbox)
    refresh_history_gui()

    # manual TTS
    valid_pattern = re.compile(r"[A-Za-z0-9\sáéíóúüñçăğşÁÉÍÓÚÜÑÇĂĞŞ.,?!]+")
    ftts = tk.LabelFrame(state.root, text="Input TTS Manual")
    ftts.pack(fill="x", padx=8, pady=(0,8))
    entry_var = tk.StringVar()
    entry_tts = tk.Entry(ftts, width=60, textvariable=entry_var)
    entry_tts.pack(side="left", padx=4, pady=4)

    def on_entry_change(var, index, mode):
        txt = entry_var.get()
        filtered = "".join(valid_pattern.findall(txt))[:100]
        if txt != filtered:
            entry_var.set(filtered)
    entry_var.trace_add("write", on_entry_change)

    def send_manual_tts(event=None):
        txt = entry_var.get().strip()
        if not txt: return
        entry_var.set("")
        if not enqueue_allowed_once(f"text::{txt}"): return
        enqueue_tts({"text": txt})
    tk.Button(ftts, text="Kirim TTS", command=send_manual_tts).pack(side="left", padx=4)
    entry_tts.bind("<Return>", send_manual_tts)

    # announcements
    fann = tk.LabelFrame(state.root, text="Putar Pengumuman")
    fann.pack(fill="x", padx=8, pady=(0,8))
    lbl_last = tk.Label(fann, text="", fg="green")
    lbl_last.pack(side="left", padx=(4,0))

    def update_announcement_ui():
        if last_announcement_path:
            btn_replay.pack(side="left", padx=4)
            lbl_last.config(text=os.path.basename(last_announcement_path))
        else:
            btn_replay.pack_forget()
            lbl_last.config(text="")   # FIX argumen

    def enqueue_announcement(path: str):
        nonlocal last_announcement_path
        if not path or not os.path.exists(path):
            messagebox.showwarning("Peringatan","File pengumuman tidak ditemukan",parent=state.root)
            return
        if not enqueue_allowed_once(f"announce::{os.path.abspath(path)}"): return

        last_announcement_path = path
        entry_time = time.strftime("%Y-%m-%d %H:%M:%S")
        text = f"[Pengumuman] {os.path.basename(path)}"

        append_history_gui_entry({"time": entry_time, "text": text, "status": "⏳"})
        refresh_history_gui()

        state.call_queue.put({"text": text, "mp3": path, "is_announcement": True, "_entry_time": entry_time})
        update_announcement_ui()

    def pick_and_play():
        p = filedialog.askopenfilename(title="Pilih File MP3", filetypes=[("MP3", "*.mp3")])
        if p: enqueue_announcement(p)

    def replay_announcement():
        if last_announcement_path:
            enqueue_announcement(last_announcement_path)
        else:
            messagebox.showwarning("Peringatan","Belum ada file pengumuman yang diputar", parent=state.root)

    def pengumuman_tutup():
        enqueue_announcement(config.ANNOUNCE_CLOSE)

    tk.Button(fann, text="Pilih & Putar MP3", command=pick_and_play).pack(side="left", padx=4, pady=4)
    btn_replay = tk.Button(fann, text="Putar Ulang", command=replay_announcement)
    update_announcement_ui()
    tk.Button(fann, text="Pengumuman Tutup", command=pengumuman_tutup).pack(side="left", padx=4, pady=4)

    # footer controls
    fb = tk.Frame(state.root); fb.pack(fill="x", padx=8, pady=(0,8))
    tk.Button(fb, text="Pilih Musik", command=on_select_music).pack(side="left", padx=4)

    tk.Label(fb, text="Interval (menit):").pack(side="left", padx=(10,4))
    interval_var = tk.StringVar(value=str(state.music_interval))
    tk.Entry(fb, width=4, textvariable=interval_var).pack(side="left")

    def apply_interval():
        try:
            num = int(interval_var.get())
            if num < 1: raise ValueError
            with state.interval_lock:
                state.music_interval = num
                if state.interval_remaining <= 0:
                    state.interval_remaining = float(state.music_interval) * 60.0
            state.save_bgm_config()
            messagebox.showinfo("OK", f"Interval diset ke {num} menit", parent=state.root)
        except ValueError:
            messagebox.showerror("Error", "Interval harus angka >=1", parent=state.root)
    tk.Button(fb, text="Apply", command=apply_interval).pack(side="left", padx=4)

    # sliders volume
    tk.Label(fb, text="BGM Vol:").pack(side="left", padx=(12,4))
    bgm_vol_var = tk.IntVar(value=state.music_volume)
    def on_bgm_slide(val):
        try: state.music_volume = int(float(val))
        except: return
        # bila TTS sedang aktif, jangan ganggu TTS player
        if state.tts_active_event.is_set():
            state.save_bgm_config(); return
        try:
            if state.music_player:
                state.music_player.audio_set_volume(state.music_volume)
        except: pass
        state.save_bgm_config()
    tk.Scale(fb, from_=0, to=100, orient="horizontal", showvalue=True, length=130,
             variable=bgm_vol_var, command=on_bgm_slide).pack(side="left")

    tk.Label(fb, text="TTS Vol:").pack(side="left", padx=(12,4))
    tts_vol_var = tk.IntVar(value=state.tts_volume)
    def on_tts_slide(val):
        try: state.tts_volume = int(float(val))
        except: return
        try:
            if state.active_tts_player is not None:
                state.active_tts_player.audio_set_volume(state.tts_volume)
        except: pass
        state.save_bgm_config()
    tk.Scale(fb, from_=0, to=100, orient="horizontal", showvalue=True, length=130,
             variable=tts_vol_var, command=on_tts_slide).pack(side="left")

    # update tick
    def tick():
        state.status_var.set(f"Status: {state.status_text}")
        with state.interval_lock:
            state.countdown_var.set(f"Interval: {int(state.interval_remaining)} s")
        state.root.after(300, tick)
    tick()

    # tray
    try:
        icon_img = Image.open(config.ICON_FILE)
    except:
        icon_img = create_fallback_icon()
    menu = pystray.Menu(
        pystray.MenuItem("Tampilkan GUI", tray_show_gui),
        pystray.MenuItem("Exit", tray_exit)
    )
    tray = pystray.Icon(config.APP_NAME, icon_img, menu=menu)
    threading.Thread(target=tray.run, daemon=True).start()

    refresh_history_gui()
    state.root.mainloop()
