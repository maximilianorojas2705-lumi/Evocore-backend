from fastapi import FastAPI
import subprocess, sys, io, contextlib

app = FastAPI()
TOKEN = "evo2026"

@app.get("/")
def salud():
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
