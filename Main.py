from fastapi import FastAPI
import subprocess, sys, io, contextlib, os

app = FastAPI()
TOKEN = "evo2026"

STATE = {"last_btc": None, "last_commit": None}

def enviar_telegram(msg):
    import requests
    tg = os.environ.get("TG_BOT", "")
    ch = os.environ.get("TG_CHAT", "")
    if tg and ch:
        try:
            requests.post(f"https://api.telegram.org/bot{tg}/sendMessage",
                          json={"chat_id": ch, "text": msg}, timeout=15)
        except Exception:
            pass

def latido():
    import requests
    try:
        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true', timeout=15).json()
        p = r['bitcoin']['usd']
        c24 = r['bitcoin']['usd_24h_change']
        if STATE["last_btc"] and abs(p - STATE["last_btc"]) / STATE["last_btc"] * 100 >= 2:
            enviar_telegram(f"₿ Alerta Bitcoin: {p:.0f} USD | 24h: {c24:+.1f}%")
        STATE["last_btc"] = p
    except Exception:
        pass
    try:
        c = requests.get('https://api.github.com/repos/maximilianorojas2705-lumi/Earnfi/commits?per_page=1', timeout=15).json()
        sha = c[0]['sha']
        if STATE["last_commit"] and sha != STATE["last_commit"]:
            enviar_telegram(f"🟡 Nuevo commit en Earnfi: {c[0]['commit']['message'][:80]}")
        STATE["last_commit"] = sha
    except Exception:
        pass

@app.get("/")
def salud():
    latido()
    return {"status": "ok", "servicio": "Backend EvoCore"}

@app.post("/ejecutar")
def ejecutar(payload: dict):
    if payload.get("token") != TOKEN:
        return {"error": "token invalido"}
    codigo = payload.get("codigo", "")
    libs = payload.get("instalar", [])
    salida_instal = ""
    if libs:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", *libs], capture_output=True, text=True)
        salida_instal = (r.stdout + r.stderr)[-800:]
    buf = io.StringIO()
    error = None
    try:
        with contextlib.redirect_stdout(buf):
            exec(codigo, {})
    except Exception as e:
        error = str(e)
    return {"instalacion": salida_instal, "salida": buf.getvalue()[-4000:], "error": error}
