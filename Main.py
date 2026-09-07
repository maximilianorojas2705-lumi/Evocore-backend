from fastapi import FastAPI, Request
import subprocess, sys, io, contextlib, os, json, threading, time, base64

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

TENES UN OBRERO EXTERNO (herramienta delegar_a_obrero):
- 'gemini': Gemini Flash (auto-descubierto en vivo). Uso: documentos largos, resumenes masivos, velocidad.
Delegá cuando: la tarea sea pesada o larga, o necesites procesamiento masivo de texto.
Vos sos el JEFE: integra lo que devuelve el obrero con tu criterio, no lo copies a ciegas.

HERRAMIENTAS AUTO-CREADAS (tu propio app store en el repo maximilianorojas2705-lumi/evocore-herramientas, carpeta tools/):
- LISTAR las que ya tenes:
import requests, os
r = requests.get('https://api.github.com/repos/maximilianorojas2705-lumi/evocore-herramientas/contents/tools', headers={'Authorization': f'token {os.environ["GH_TOKEN"]}'})
print([f['name'] for f in r.json()])
- USAR una:
import requests, os
r = requests.get('https://raw.githubusercontent.com/maximilianorojas2705-lumi/evocore-herramientas/main/tools/NOMBRE.py', headers={'Authorization': f'token {os.environ["GH_TOKEN"]}'})
exec(r.text)
- CREAR una nueva: cuando resuelvas una tarea con codigo reutilizable (scraper, parser, analizador, consultor de APIs), guardala como tools/nombre.py con funciones documentadas, usando la API de GitHub (PUT contents con base64, igual que con la memoria).
REGLA DE ORO: antes de escribir codigo desde cero, lista tus herramientas y revisa si alguna ya lo hace.
SI ejecutar_python falla 2 veces seguidas con el mismo error, NO reintentes: detenete y explicame el error con el texto crudo para que lo veamos juntos.

AUTO-MODIFICACIÓN CON APROBACIÓN (podes proponer mejoras a tu propio código):
Usá la herramienta proponer_mejora para sugerir cambios a tu Main.py, prompt o comportamiento.
Maxi va a recibir tu propuesta por Telegram y puede aprobarla o rechazarla.
Si la aprueba, vas a poder modificar tu propio Main.py en el repo Evocore-backend via GitHub API.
Ejemplos de mejoras validas:
- Optimizar el prompt para ahorrar tokens
- Agregar herramientas al SYSTEM_PROMPT
- Mejorar el revisor de código
- Agregar nuevos endpoints
- Optimizar el latido
NO propongas cambios destructivos o que rompan funcionalidad existente sin justificación clara."""

TOOLS = [
    {"type": "function", "function": {
        "name": "ejecutar_python",
        "description": "Ejecuta codigo Python en el servidor con internet y cualquier libreria",
        "parameters": {"type": "object", "properties": {
            "codigo": {"type": "string", "description": "Codigo Python completo, usa print()"}},
            "required": ["codigo"]}}},
    {"type": "function", "function": {
        "name": "delegar_a_obrero",
        "description": "Delega una tarea al obrero Gemini y devuelve su respuesta textual",
        "parameters": {"type": "object", "properties": {
            "tarea": {"type": "string", "description": "Instrucciones completas y autocontenidas para el obrero"}},
            "required": ["tarea"]}}},
    {"type": "function", "function": {
        "name": "proponer_mejora",
        "description": "Propone una mejora al código o comportamiento propio para aprobación de Maxi",
        "parameters": {"type": "object", "properties": {
            "descripcion": {"type": "string", "description": "Descripción clara de la mejora"},
            "impacto": {"type": "string", "description": "Qué beneficio trae (ahorro de tokens, mejor rendimiento, nueva funcionalidad)"},
            "cambio": {"type": "string", "description": "Descripción técnica del cambio a realizar"}},
            "required": ["descripcion", "impacto", "cambio"]}}}
]

HISTORIAL = {}
STATE = {"last_btc": None, "last_commits": {}}
MODELOS_CACHE = {"groq": None, "gemini": None}
PROPUESTAS = {}


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
            exec(codigo, {"__name__": "__main__", "enviar_telegram": enviar_telegram, "PROPUESTAS": PROPUESTAS})
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    salida = buf.getvalue()
    if error:
        salida += f"\nERROR: {error}"
    return (salida or "(sin salida)")[-4000:]


def candidato_gemini():
    modelos_validos = [
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-lite-latest"
    ]
    if MODELOS_CACHE["gemini"] and MODELOS_CACHE["gemini"] in modelos_validos:
        return MODELOS_CACHE["gemini"]
    MODELOS_CACHE["gemini"] = modelos_validos[0]
    return modelos_validos[0]


def candidatos_groq():
    import requests
    if MODELOS_CACHE["groq"]:
        return MODELOS_CACHE["groq"]
    r = requests.get("https://api.groq.com/openai/v1/models",
                     headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=30)
    ids = [m["id"] for m in r.json().get("data", [])]
    prefs = ["gpt-oss-120b", "gpt-oss-20b", "maverick", "llama-3.3", "qwen", "deepseek", "llama"]
    out = []
    for p in prefs:
        for i in ids:
            if p in i.lower() and i not in out:
                out.append(i)
    for i in ids:
        if i not in out:
            out.append(i)
    if not out:
        raise Exception(f"Groq sin modelos: {r.status_code}")
    MODELOS_CACHE["groq"] = out
    return out


def llamar_obrero(tarea):
    import requests
    modelos = ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview", "gemini-flash-lite-latest"]
    for modelo in modelos:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": tarea}]}]}, timeout=90)
            if r.status_code == 200:
                data = r.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    MODELOS_CACHE["gemini"] = modelo
                    return data["candidates"][0]["content"]["parts"][0]["text"][:4000]
            if r.status_code in [404, 503, 429]:
                continue
            return f"obrero gemini fallo ({modelo}): {r.status_code} {r.text[:200]}"
        except Exception:
            continue
    return "obrero gemini fallo: todos los modelos agotados"


def pensar(msgs):
    import requests
    ultimo = ""
    for modelo in candidatos_groq()[:4]:
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
    for _ in range(12):
        m = pensar(msgs)
        if m.get("tool_calls"):
            msgs.append(m)
            for tc in m["tool_calls"]:
                args = json.loads(tc["function"]["arguments"])
                nombre = tc["function"]["name"]
                if nombre == "ejecutar_python":
                    salida = correr_python(args.get("codigo", ""))
                elif nombre == "delegar_a_obrero":
                    salida = llamar_obrero(args.get("tarea", ""))
                elif nombre == "proponer_mejora":
                    salida = registrar_propuesta(args)
                else:
                    salida = "herramienta desconocida"
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": salida})
        else:
            r = m.get("content") or "(sin respuesta)"
            hist.append({"role": "assistant", "content": r})
            return r
    return "Me quede sin pasos para esta tarea."


def registrar_propuesta(args):
    import uuid
    propuesta_id = str(uuid.uuid4())[:8]
    PROPUESTAS[propuesta_id] = {
        "descripcion": args.get("descripcion", ""),
        "impacto": args.get("impacto", ""),
        "cambio": args.get("cambio", ""),
        "estado": "pendiente",
        "timestamp": time.time()
    }
    msg = f"""💡 PROPUESTA DE MEJORA (ID: {propuesta_id})

📝 Descripción:
{args.get("descripcion", "")}

🎯 Impacto:
{args.get("impacto", "")}

🔧 Cambio propuesto:
{args.get("cambio", "")}

Respondé 'apruebo {propuesta_id}' para aplicar la mejora, o 'rechazo {propuesta_id}' para descartarla."""
    enviar_telegram(msg)
    return f"Propuesta {propuesta_id} registrada y enviada a Maxi para aprobación"


def aprobar_propuesta(propuesta_id):
    import requests
    if propuesta_id not in PROPUESTAS:
        return "Propuesta no encontrada"
    
    propuesta = PROPUESTAS[propuesta_id]
    if propuesta["estado"] != "pendiente":
        return f"Propuesta ya fue {propuesta['estado']}"
    
    # Leer Main.py actual
    try:
        r = requests.get("https://api.github.com/repos/maximilianorojas2705-lumi/Evocore-backend/contents/Main.py",
                        headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=30)
        if r.status_code != 200:
            return f"Error leyendo Main.py: {r.status_code}"
        
        data = r.json()
        sha = data["sha"]
        contenido_actual = base64.b64decode(data["content"]).decode()
        
        # Pedir al agente que haga el cambio
        tarea = f"""Aplica esta mejora al código Main.py de EvoCore:

PROPUESTA:
{propuesta['descripcion']}

CAMBIO TÉCNICO:
{propuesta['cambio']}

CÓDIGO ACTUAL (primeras 3000 caracteres):
{contenido_actual[:3000]}

Devuelve SOLO el código Python modificado completo, sin explicaciones ni markdown. Asegurate de que sea válido y funcional."""
        
        codigo_nuevo = llamar_obrero(tarea)
        
        if len(codigo_nuevo) < 1000:
            return f"El obrero devolvió código muy corto, probablemente falló: {codigo_nuevo[:200]}"
        
        # Commit del cambio
        r2 = requests.put("https://api.github.com/repos/maximilianorojas2705-lumi/Evocore-backend/contents/Main.py",
                         headers={"Authorization": f"Bearer {GH_TOKEN}"},
                         json={
                             "message": f"Auto-mejora aprobada: {propuesta['descripcion'][:50]}",
                             "content": base64.b64encode(codigo_nuevo.encode()).decode(),
                             "sha": sha
                         }, timeout=30)
        
        if r2.status_code in [200, 201]:
            PROPUESTAS[propuesta_id]["estado"] = "aprobada"
            enviar_telegram(f"✅ Propuesta {propuesta_id} APROBADA y aplicada. Deploy en progreso...")
            return "Mejora aplicada exitosamente"
        else:
            return f"Error en commit: {r2.status_code} {r2.text[:200]}"
    
    except Exception as e:
        return f"Error aplicando mejora: {type(e).__name__}: {e}"


def procesar(texto, chat):
    # Manejar aprobaciones
    if texto.lower().startswith("apruebo "):
        propuesta_id = texto[8:].strip()
        resultado = aprobar_propuesta(propuesta_id)
        enviar_telegram(resultado, chat)
        return
    
    if texto.lower().startswith("rechazo "):
        propuesta_id = texto[8:].strip()
        if propuesta_id in PROPUESTAS:
            PROPUESTAS[propuesta_id]["estado"] = "rechazada"
            enviar_telegram(f"❌ Propuesta {propuesta_id} rechazada", chat)
        else:
            enviar_telegram("Propuesta no encontrada", chat)
        return
    
    try:
        r = atender(texto, chat)
    except Exception as e:
        r = f"Error interno: {type(e).__name__}: {e}"
    enviar_telegram(r, chat)


def revisar_commit(repo, sha, mensaje):
    import requests
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/commits/{sha}",
                         headers={"Authorization": f"Bearer {GH_TOKEN}"},
                         timeout=30)
        if r.status_code != 200:
            print(f"[revisor] github devolvio {r.status_code} para {sha[:8]}")
            return
        data = r.json()
        archivos = data.get("files", [])
        diff_resumen = []
        for archivo in archivos[:10]:
            patch = archivo.get("patch", "")[:1000]
            diff_resumen.append(
                f"📄 {archivo['filename']} ({archivo['status']}, +{archivo.get('additions',0)}/-{archivo.get('deletions',0)})\n{patch}")
        if not diff_resumen:
            print(f"[revisor] commit {sha[:8]} sin archivos con diff")
            return
        diff_texto = "\n\n".join(diff_resumen)[:3500]
        tarea = f"""Analiza este commit de Maxi y dame feedback conciso:

REPO: {repo}
COMMIT: {mensaje}
CAMBIOS:
{diff_texto}

Dame:
1. 📝 Qué hizo el commit (1 línea)
2. ✅ Qué está bien (1-2 puntos)
3. ⚠️ Sugerencias de mejora (1-2 puntos, si aplica)
4. 🐛 Posibles bugs (si ves alguno)

Sé directo y técnico. Máximo 200 palabras."""
        analisis = llamar_obrero(tarea)
        if "fallo" in analisis[:30]:
            nombres = ", ".join(a["filename"] for a in archivos[:5])
            analisis = f"📝 Commit: {mensaje}\n📄 Archivos: {nombres}\n(El obrero no estaba disponible; revisión profunda pendiente)"
        print(f"[revisor] enviando revision de {repo} {sha[:8]}")
        enviar_telegram(f"🔍 Revisión de commit en {repo.split('/')[-1]}:\n\n{analisis}")
        print(f"[revisor] revision enviada ok")
    except Exception as e:
        print(f"[revisor] error: {type(e).__name__}: {e}")


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
    repos = ["maximilianorojas2705-lumi/Earnfi", "maximilianorojas2705-lumi/nexus-backend"]
    for repo in repos:
        try:
            c = requests.get(f'https://api.github.com/repos/{repo}/commits?per_page=1',
                             headers={"Authorization": f"Bearer {GH_TOKEN}"},
                             timeout=15).json()
            if not c:
                continue
            sha = c[0]['sha']
            mensaje = c[0]['commit']['message'][:80]
            previo = STATE["last_commits"].get(repo)
            if previo and sha != previo:
                print(f"[latido] commit nuevo en {repo}: {sha[:8]}")
                threading.Thread(target=revisar_commit, args=(repo, sha, mensaje), daemon=True).start()
            STATE["last_commits"][repo] = sha
        except Exception as e:
            print(f"[latido] error repos: {e}")


@app.api_route("/", methods=["GET", "HEAD"])
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
