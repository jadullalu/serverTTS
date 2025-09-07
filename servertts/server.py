# servertts/server.py
import threading, logging, socket
from flask import request
from . import state, config
from .worker import enqueue_tts

@state.app.route("/healthz", methods=["GET"])
def healthz():
    return {"ok": True, "service": "ServerTTS"}, 200

# --- access log sederhana ---
@state.app.before_request
def _log_before():
    try:
        logging.info(f"REQ {request.remote_addr} {request.method} {request.path} agent={request.headers.get('User-Agent','-')}")
    except Exception:
        pass

@state.app.after_request
def _log_after(resp):
    try:
        logging.info(f"RES {request.remote_addr} {request.method} {request.path} -> {resp.status_code}")
    except Exception:
        pass
    return resp

@state.app.route('/call', methods=['POST'])
def call_kasir():
    data = request.get_json(force=True, silent=True) or request.form or request.json or {}
    konter = data.get("konter")
    kasir  = data.get("kasir")

    if konter is None or kasir is None:
        logging.warning("Bad request: missing konter/kasir")
        return {"status":"error","message":"Missing konter or kasir"}, 400

    if str(konter) == "100":
        text = "Panggilan untuk, Staf Office di Tunggu Di Ruangan."
    elif str(konter).isnumeric():
        text = f"Panggilan untuk, Konter {konter} ke kasir {kasir}."
    else:
        text = str(konter)

    logging.info(f"Enqueue TTS: {text!r}")
    enqueue_tts({"text": text})
    return {"status": "ok", "message": f"Panggilan '{text}' masuk antrean"}

def _guess_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def start_flask_thread():
    host = config.FLASK_HOST
    port = config.FLASK_PORT

    def runner():
        # tulis ke log file juga
        if host == "0.0.0.0":
            lan_ip = _guess_ip()
            logging.info(f"Flask listening on http://127.0.0.1:{port} and http://{lan_ip}:{port}")
        else:
            logging.info(f"Flask listening on http://{host}:{port}")

        state.app.run(host=host, port=port, debug=False, use_reloader=False)

    threading.Thread(target=runner, daemon=True).start()

    # tampilkan ke console kalau kamu menjalankan dari python (opsional)
    try:
        if host == "0.0.0.0":
            ip = _guess_ip()
            print(f"ServerTTS siap di http://127.0.0.1:{port} dan http://{ip}:{port}")
        else:
            print(f"ServerTTS siap di http://{host}:{port}")
    except:
        pass
