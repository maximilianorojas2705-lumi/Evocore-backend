from fastapi import FastAPI, Request
import subprocess, sys, io, contextlib, os, json, threading

app = FastAPI()
TOKEN = "evo2026"

TG_BOT = os.environ.get("TG_BOT", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
GROQ_KEY = os.environ.get("GROQ_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")

SYSTEM_PROMPT = """Sos EvoCore, el agente evolutivo personal de Maxi, con autonomia tecnica maxima.
Trabajas 100% en la nube desde tu propio servidor. NUNCA des comandos para ejecutar en local (git, pip, terminal).
Tenes la herramienta ejecutar_python: corre codigo en este mismo servidor, con internet y librerias libres.
Para buscar en la web usa la API de Tavily con os.environ["TAVILY_KEY"].
Para memoria persistente usa el repo maximilianorojas2705-lumi/evocore-memoria (memoria.json) con os.environ["GH_TOKEN"].
Datos de Maxi: GitHub maximilianorojas2705-lumi, repos Earnfi y nexus-backend, proyecto creaciones HTML, prefiere respuestas tecnicas y directas.
Estilo: directo, sin sermones. Usa emojis ok/atencion/critico.
Despues de cada tarea agrega mini ciclo evolutivo: que hiciste, que salio mal, que aprendiste.

TENES OBREROS EXTERNOS (herramienta delegar_a_obrero):
- 'github': GPT-4o via GitHub Models. Uso: analisis profundo, codigo complejo, segunda opinion, y tareas que tu propio modelo rechace o se niegue a hacer.
- 'gemini': Gemini 2.5 Flash. Uso: documentos largos, resumenes masivos, velocidad.
Delegá cuando: la tarea sea pesada o larga, necesites segunda opinion, o tu modelo principal se niegue a responder.
Vos sos el JEFE: integra lo que devuelve el obrero con tu criterio, no lo copies a ciegas."""

TOOLS = [
    {"type": "function", "function": {
        "name": "ejecutar_python",
        "description": "Ejecuta codigo Python en el servidor con internet y cualquier libreria",
        "parameters": {"type": "object", "properties": {
            "codigo": {"type": "string", "description": "Codigo Python completo, usa print()"}},
            "required": ["codigo"]}}},
    {"type": "function", "function": {
        "name": "delegar_a_obrero",
        "description": "Delega una tarea a un modelo obrero externo y devuelve su respuesta textual",
        "parameters": {"type": "object", "properties": {
            "obrero": {"type": "string", "enum": ["github", "gemini"],
                       "description": "github=GPT-4o (analisis, codigo, segunda opinion); gemini=Gemini Flash (textos largos, resumenes)"},
            "tarea": {"type": "string", "description": "Instrucciones completas y autocontenidas para el obrero"}},
            "required": ["obrero", "tarea"]}}}
]

HISTORIAL = {}
STATE = {"last_btc": None, "last_commit": None}
MODELOS_CACHE = {"ids": None}


def enviar_telegram(msg, chat=None):
    import requests
    ch = chat or TG_CHAT
    if TG_BOT and ch:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                          json={"chat_id": ch, "text": str(msg)[:4000]}, timeout=15)
        except Exception:
            pass


def correr_python(codigo):
    buf = io.StringIO()
    error = None
    try:
        with contextlib.redirect_stdout(buf):
            exec(codigo, {"__name__": "__main__", "enviar_telegram": enviar_telegram})
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    salida = buf.getvalue()
    if error:
        salida += f"\nERROR: {error}"
    return (salida or "(sin salida)")[-4000:]


def llamar_obrero(obrero, tarea):
    import requests
    try:
        if obrero == "github":
            for url in ["https://models.github.ai/inference/chat/completions",
                        "https://models.inference.ai.azure.com/chat/completions"]:
                r = requests.post(url,
                    headers={"Authorization": f"Bearer {GH_TOKEN}",
                             "Content-Type": "application/json"},
                    json={"model": "openai/gpt-4o",
                          "messages": [{"role": "user", "content": tarea}],
                          "temperature": 0.7}, timeout=90)
                data = r.json()
                if "choices" in data:
                    return data["choices"][0]["message"]["content"][:4000]
            return f"obrero github fallo: {r.status_code} {r.text[:200]}"
        if obrero == "gemini":
            if not GEMINI_KEY:
                return "obrero gemini sin key configurada"
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": tarea}]}]}, timeout=90)
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"][:4000]
        return f"obrero desconocido: {obrero}"
    except Exception as e:
        return f"obrero {obrero} error: {type(e).__name__}: {e}"


def candidatos():
    import requests
    if not MODELOS_CACHE["ids"]:
        r = requests.get("https://api.groq.com/openai/v1/models",
                         headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=30)
        MODELOS_CACHE["ids"] = [m["id"] for m in r.json().get("data", [])]
    ids = MODELOS_CACHE["ids"]
    prefs = ["gpt-oss", "maverick", "llama-3.3", "qwen", "deepseek", "llama"]
    out = []
    for p in prefs:
        for i in ids:
            if p in i.lower() and i not in out:
                out.append(i)
    for i in ids:
        if i not in out:
            out.append(i)
    return out


def pensar(msgs):
    import requests
    ultimo = ""
    for modelo in candidatos()[:4]:
        for mx in [None, 1000]:
            payload = {"model": modelo, "messages": msgs,
                       "tools": TOOLS, "temperature": 0.4}
            if mx:
                payload["max_tokens"] = mx
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {GROQ_KEY}"},
                              json=payload, timeout=120)
            data = r.json()
            if "choices" in data:
                return data["choices"][0]["message"]
            ultimo = f"{modelo}: {r.status_code} {r.text[:150]}"
            if r.status_code != 429:
                break
    raise Exception(f"Groq fallo -> {ultimo}")


def atender(texto, chat):
    hist = HISTORIAL.setdefault(chat, [])
    hist.append({"role": "user", "content": texto})
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + hist[-20:]
    for _ in range(8):
        m = pensar(msgs)
        if m.get("tool_calls"):
            msgs.append(m)
            for tc in m["tool_calls"]:
                args = json.loads(tc["function"]["arguments"])
                nombre = tc["function"]["name"]
                if nombre == "ejecutar_python":
                    salida = correr_python(args.get("codigo", ""))
                elif nombre == "delegar_a_obrero":
                    salida = llamar_obrero(args.get("obrero", ""), args.get("tarea", ""))
                else:
                    salida = "herramienta desconocida"
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": salida})
        else:
            r = m.get("content") or "(sin respuesta)"
            hist.append({"role": "assistant", "content": r})
            return r
    return "Me quede sin pasos para esta tarea."


def procesar(texto, chat):
    try:
        r = atender(texto, chat)
    except Exception as e:
        r = f"Error interno: {type(e).__name__}: {e}"
    enviar_telegram(r, chat)


@app.post("/tg")
async def tg(req: Request):
    data = await req.json()
    msg = data.get("message") or {}
    texto = msg.get("text")
    chat = str(msg.get("chat", {}).get("id", ""))
    if texto and chat:
        threading.Thread(target=procesar, args=(texto, chat), daemon=True).start()
    return {"ok": True}


def latido():
    import requests
    try:
        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true', timeout=15).json()
        p = r['bitcoin']['usd']
        c24 = r['bitcoin']['usd_24h_change']
        if STATE["last_btc"] and abs(p - STATE["last_btc"]) / STATE["last_btc"] * 100 >= 2:
            enviar_telegram(f"Alerta Bitcoin: {p:.0f} USD | 24h: {c24:+.1f}%")
        STATE["last_btc"] = p
    except Exception:
        pass
    try:
        c = requests.get('https://api.github.com/repos/maximilianorojas2705-lumi/Earnfi/commits?per_page=1', timeout=15).json()
        sha = c[0]['sha']
        if STATE["last_commit"] and sha != STATE["last_commit"]:
            enviar_telegram(f"Nuevo commit en Earnfi: {c[0]['commit']['message'][:80]}")
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
