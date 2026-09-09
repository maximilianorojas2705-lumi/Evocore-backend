from fastapi import FastAPI, Request
import subprocess, sys, io, contextlib, os, json, threading, time, base64
from datetime import datetime, timezone, timedelta

app = FastAPI()
TOKEN = "evo2026"

TG_BOT = os.environ.get("TG_BOT", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
GROQ_KEY = os.environ.get("GROQ_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
CEREBRAS_KEY = os.environ.get("CEREBRAS_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")

SYSTEM_PROMPT = """Sos EvoCore, el agente evolutivo personal de Maxi, con autonomia tecnica maxima.
Trabajas 100% en la nube desde tu propio servidor. NUNCA des comandos para ejecutar en local (git, pip, terminal).
Tenes la herramienta ejecutar_python: corre codigo en este mismo servidor, con internet y librerias libres.
Para buscar en la web usa la API de Tavily con os.environ["TAVILY_KEY"].
Para memoria persistente usa el repo maximilianorojas2705-lumi/evocore-memoria (memoria.json) con os.environ["GH_TOKEN"].
Datos de Maxi: GitHub maximilianorojas2705-lumi, repos Earnfi y nexus-backend, proyecto creaciones HTML, prefiere respuestas tecnicas y directas.
Estilo: directo, sin sermones. Usa emojis ok/atencion/critico.
Despues de cada tarea agrega mini ciclo evolutivo: que hiciste, que salio mal, que aprendiste.

OBREROS ESPECIALISTAS (herramienta delegar_a_obrero con parametro perfil):
- 'reviewer': revisor de codigo senior estricto, cazador de bugs y riesgos. Usalo para analizar codigo, diffs y seguridad.
- 'investigador': creativo para brainstorm, diseños y alternativas no obvias.
- 'resumidor': sintetizador extremo en bullets densos. Usalo para comprimir textos largos.
- 'generico': el de siempre para todo lo demas.
Elegi el perfil segun la tarea; si Maxi pide explicitamente un especialista, usalo.
Delegá cuando: la tarea sea pesada o larga, o necesites procesamiento masivo de texto.
Vos sos el JEFE: integra lo que devuelve el obrero con tu criterio, no lo copies a ciegas.
AL DELEGAR: el obrero no tiene tu memoria, tu historial ni tus herramientas: la tarea que le mandes debe incluir todos los datos que necesita. Las preguntas sobre tu propia historia, memoria o estado interno NO se delegan: las respondés vos desde contexto.json y memoria.json.

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

REGLA ANTI-ATRAGANTAMIENTO (muy importante):
Cuando leas archivos grandes (tu Main.py, memoria.json, diffs, etc.), NUNCA imprimas el contenido completo: rompe el limite de tokens de entrada.
Imprimi SOLO el fragmento que necesitas, usando busqueda y rebanado. Ejemplo:
import requests, os
r = requests.get('https://raw.githubusercontent.com/maximilianorojas2705-lumi/Evocore-backend/main/Main.py', headers={'Authorization': f'token {os.environ["GH_TOKEN"]}'})
codigo = r.text
i = codigo.find('def aprobar_propuesta')
print(codigo[i:i+1200])

AUTO-MODIFICACIÓN QUIRÚRGICA CON CONTROL DE MAXI:
CUANDO detectes una mejora posible a tu código, DEBES usar la herramienta proponer_mejora. NUNCA escribas la propuesta suelta en el texto.
ANTES de proponer, lee SOLO el fragmento relevante de tu Main.py (ver regla anti-atragantamiento).
Después definí en la propuesta:
- buscar: un fragmento EXACTO, copiado literal del código actual, que sea ÚNICO en el archivo (5 a 30 líneas)
- reemplazar: el código nuevo exacto que irá en su lugar
NUNCA propongas reescribir todo el archivo: siempre cambios quirúrgicos y mínimos.
HAY DOS MODOS DE CONTROL (Maxi los cambia por Telegram):
- MODO SUPERVISADO (por defecto): cada propuesta espera su aprobacion SIN limite de tiempo ('apruebo [ID]' o 'rechazo [ID]'). Nunca se auto-aplica.
- MODO AUTONOMO (cuando Maxi dice 'segui de corrido' o 'modo autonomo'): las propuestas se auto-aplican al instante sin esperarlo.
- Maxi vuelve al control con 'frena' o 'modo supervisado'.
Respeta siempre el modo vigente al registrar cada propuesta.

RECORDATORIOS CON FECHA (tu agenda):
Cuando Maxi pida un recordatorio o aviso futuro ("avisame el viernes a las 10 que X", "recordame mañana..."), guardalo en el repo evocore-memoria, archivo recordatorios.json, usando la API de GitHub desde ejecutar_python:
- Formato del archivo: lista de objetos {"texto": "...", "cuando": epoch_segundos_UTC, "enviado": false}
- Las horas que dice Maxi son hora argentina (UTC-3): convertí con datetime y timezone(timedelta(hours=-3)).
- Primero imprimí la fecha actual del servidor para resolver dias relativos ("mañana", "el viernes").
- Lee recordatorios.json (si da 404, empezá con lista vacia), agregá el item y guardalo con PUT (con sha si existe).
- Confirmale a Maxi exactamente qué entendiste: texto + fecha y hora.
El latido revisa recordatorios.json cada 5 minutos y envia el aviso por Telegram cuando llega la hora, marcandolo como enviado.

MEMORIA DE LARGO PLAZO (contexto que sobrevive reinicios):
Tenes un archivo contexto.json en el repo evocore-memoria con: resumen de sesiones, ultimos mensajes, notas permanentes y el modo de control vigente.
Al iniciar una conversacion puede aparecer un bloque "CONTEXTO RECUPERADO TRAS REINICIO": usalo para retomar donde quedaron sin preguntar de nuevo.
Cuando Maxi diga "acordate de X", "guarda esto", o detectes un dato importante a largo plazo (preferencias, decisiones, datos de proyectos), usa la herramienta guardar_nota.
Tu resumen de sesion se auto-actualiza cada 8 mensajes; no tenes que hacer nada.

AUTO-TAREAS (autonomia proactiva):
Cuando Maxi pida algo recurrente ("todos los lunes...", "cada mañana...", "cada X horas...") o una tarea diferida que deba ejecutarse sola, usa la herramienta programar_tarea.
- cuando_epoch: epoch UTC de la primera ejecucion (las horas de Maxi son UTC-3).
- repetir_segundos: 0 = una sola vez; 3600 = horaria; 86400 = diaria; 604800 = semanal.
- accion: codigo Python autocontenido que se ejecuta DIRECTAMENTE con correr_python (sin pasar por el cerebro): usa enviar_telegram() y librerias importadas al inicio del snippet.
El latido ejecuta las tareas vencidas cada 5 minutos, sin que Maxi pida nada, y te avisa el resultado por Telegram.
Si Maxi pide "lista de autotareas", "borra la autotarea X" o "pausa las autotareas", gestionalo leyendo y escribiendo autotareas.json con ejecutar_python."""

TOOLS = [
    {"type": "function", "function": {
        "name": "ejecutar_python",
        "description": "Ejecuta codigo Python en el servidor con internet y cualquier libreria",
        "parameters": {"type": "object", "properties": {
            "codigo": {"type": "string", "description": "Codigo Python completo, usa print()"}},
            "required": ["codigo"]}}},
    {"type": "function", "function": {
        "name": "delegar_a_obrero",
        "description": "Delega una tarea a un obrero Gemini especialista y devuelve su respuesta textual",
        "parameters": {"type": "object", "properties": {
            "tarea": {"type": "string", "description": "Instrucciones completas y autocontenidas para el obrero"},
            "perfil": {"type": "string", "enum": ["generico", "reviewer", "investigador", "resumidor"], "description": "Especialista: reviewer (codigo estricto), investigador (ideas creativas), resumidor (sintesis), generico (resto)"}},
            "required": ["tarea"]}}},
    {"type": "function", "function": {
        "name": "proponer_mejora",
        "description": "Propone un cambio quirurgico al propio Main.py; se aplica segun el modo de control vigente",
        "parameters": {"type": "object", "properties": {
            "descripcion": {"type": "string", "description": "Descripción clara de la mejora"},
            "impacto": {"type": "string", "description": "Qué beneficio trae"},
            "buscar": {"type": "string", "description": "Fragmento EXACTO y unico del Main.py actual que se va a reemplazar (copiado literal)"},
            "reemplazar": {"type": "string", "description": "Codigo nuevo exacto que ira en lugar del fragmento"}},
            "required": ["descripcion", "impacto", "buscar", "reemplazar"]}}},
    {"type": "function", "function": {
        "name": "guardar_nota",
        "description": "Guarda una nota permanente en la memoria de largo plazo del agente (sobrevive reinicios y deploys)",
        "parameters": {"type": "object", "properties": {
            "nota": {"type": "string", "description": "Texto corto de la nota a recordar para siempre"}},
            "required": ["nota"]}}},
    {"type": "function", "function": {
        "name": "programar_tarea",
        "description": "Programa una tarea automatica que el latido ejecutara sola (unica o recurrente)",
        "parameters": {"type": "object", "properties": {
            "descripcion": {"type": "string", "description": "Nombre corto de la tarea"},
            "accion": {"type": "string", "description": "Codigo Python autocontenido que se ejecutara directamente con correr_python"},
            "cuando_epoch": {"type": "integer", "description": "Epoch UTC de la primera ejecucion"},
            "repetir_segundos": {"type": "integer", "description": "0 si es unica; segundos entre repeticiones si es recurrente"}},
            "required": ["descripcion", "accion", "cuando_epoch", "repetir_segundos"]}}}
]

HISTORIAL = {}
STATE = {"last_btc": None, "last_commits": {}, "last_report": None, "turnos": 0}
MODELOS_CACHE = {}
PROPUESTAS = {}

PERFILES = {
    "reviewer": {
        "system": "Sos un revisor de codigo senior extremadamente estricto y preciso. Tu trabajo es cazar bugs, riesgos de seguridad, errores de logica y problemas de rendimiento. No elogies por elogiar: si algo esta bien, decilo en una linea; concentra tu energia en lo que puede romperse. Se tecnico, directo y concreto.",
        "temperature": 0.2
    },
    "investigador": {
        "system": "Sos un investigador creativo y curioso. Generas alternativas, ideas no obvias y enfoques novedosos. Exploras angulos que otros no ven, comparas opciones con honestidad intelectual y marcas claramente cuales son especulaciones.",
        "temperature": 0.8
    },
    "resumidor": {
        "system": "Sos un sintetizador profesional. Comprimis cualquier contenido en bullets cortos y densos, sin perder decisiones, pendientes ni datos clave. Nunca agregas informacion que no estaba en el original.",
        "temperature": 0.3
    },
    "generico": {
        "system": "",
        "temperature": 0.4
    }
}


def enviar_telegram(msg, chat=None):
    import requests
    ch = chat or TG_CHAT
    if TG_BOT and ch:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
                          json={"chat_id": ch, "text": str(msg)[:4000]}, timeout=15)
        except Exception:
            pass


def leer_contexto():
    import requests
    try:
        r = requests.get("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/contexto.json",
                         headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=15)
        if r.status_code != 200:
            return {"resumen": "", "ultimos": [], "notas": [], "modo_autonomo": False}
        c = json.loads(base64.b64decode(r.json()["content"]).decode())
        return {"resumen": c.get("resumen", ""), "ultimos": c.get("ultimos", []),
                "notas": c.get("notas", []), "modo_autonomo": bool(c.get("modo_autonomo", False))}
    except Exception:
        return {"resumen": "", "ultimos": [], "notas": [], "modo_autonomo": False}


def guardar_contexto_ctx(ctx):
    import requests
    for _ in range(2):
        try:
            r0 = requests.get("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/contexto.json",
                              headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=15)
            body = {"message": "contexto actualizado",
                    "content": base64.b64encode(json.dumps(ctx, ensure_ascii=False).encode()).decode()}
            if r0.status_code == 200:
                body["sha"] = r0.json()["sha"]
            r = requests.put("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/contexto.json",
                             headers={"Authorization": f"Bearer {GH_TOKEN}"}, json=body, timeout=15)
            if r.status_code in (200, 201):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


CONTEXTO = leer_contexto()


def ctx_completo():
    return {"resumen": CONTEXTO.get("resumen", ""),
            "notas": CONTEXTO.get("notas", []),
            "ultimos": CONTEXTO.get("ultimos", []),
            "modo_autonomo": bool(CONTEXTO.get("modo_autonomo", False)),
            "ts": time.time()}


def set_modo(autonomo):
    CONTEXTO["modo_autonomo"] = bool(autonomo)
    return guardar_contexto_ctx(ctx_completo())


def inyeccion_contexto(hist_len):
    partes = []
    if CONTEXTO.get("resumen"):
        partes.append("RESUMEN DE SESIONES ANTERIORES:\n" + CONTEXTO["resumen"])
    if CONTEXTO.get("notas"):
        partes.append("NOTAS PERMANENTES:\n" + "\n".join("- " + n for n in CONTEXTO["notas"][-10:]))
    if CONTEXTO.get("ultimos") and hist_len <= 1:
        lineas = [f"{m['role']}: {m['content'][:300]}" for m in CONTEXTO["ultimos"][-4:]]
        partes.append("ULTIMOS MENSAJES DE LA SESION PREVIA:\n" + "\n".join(lineas))
    if not partes:
        return ""
    return "CONTEXTO RECUPERADO TRAS REINICIO:\n" + "\n\n".join(partes)


def resumir_historial(hist):
    lineas = []
    for m in hist[-12:]:
        lineas.append(f"{m['role']}: {(m.get('content') or '')[:300]}")
    tarea = ("Resumi esta conversacion en maximo 150 palabras, en espanol, enfocandote en: "
             "decisiones tomadas, tareas pendientes, datos importantes y aprendizajes. "
             "Devolve SOLO el resumen.\n\n" + "\n".join(lineas))
    r = llamar_obrero(tarea, "resumidor")
    if r.startswith("obrero"):
        return None
    return r


def persistir_contexto(chat):
    try:
        hist = HISTORIAL.get(chat, [])
        ultimos = [{"role": m["role"], "content": (m.get("content") or "")[:400]} for m in hist[-6:]]
        STATE["turnos"] = STATE.get("turnos", 0) + 1
        if STATE["turnos"] % 8 == 0 and hist:
            nuevo = resumir_historial(hist)
            if nuevo:
                CONTEXTO["resumen"] = nuevo[:1500]
        CONTEXTO["ultimos"] = ultimos
        if guardar_contexto_ctx(ctx_completo()):
            pass
    except Exception as e:
        print(f"[contexto] error: {e}")


def guardar_nota(nota):
    if not nota:
        return "nota vacia"
    notas = CONTEXTO.setdefault("notas", [])
    fecha = datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m %H:%M")
    notas.append(f"{fecha} - {nota[:200]}")
    CONTEXTO["notas"] = notas[-20:]
    if guardar_contexto_ctx(ctx_completo()):
        return f"Nota guardada en memoria permanente ({len(CONTEXTO['notas'])} notas)"
    return "Error guardando la nota en GitHub"


def leer_autotareas():
    import requests
    try:
        r = requests.get("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/autotareas.json",
                         headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=15)
        if r.status_code == 404:
            return [], None
        if r.status_code != 200:
            return [], None
        data = r.json()
        try:
            return json.loads(base64.b64decode(data["content"]).decode()), data["sha"]
        except Exception:
            return [], data["sha"]
    except Exception:
        return [], None


def guardar_autotareas(lista, sha):
    import requests
    body = {
        "message": "autotareas actualizadas",
        "content": base64.b64encode(json.dumps(lista, ensure_ascii=False, indent=1).encode()).decode()
    }
    if sha:
        body["sha"] = sha
    r = requests.put("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/autotareas.json",
                     headers={"Authorization": f"Bearer {GH_TOKEN}"}, json=body, timeout=15)
    return r.status_code in [200, 201]


def programar_tarea(args):
    import uuid
    tid = str(uuid.uuid4())[:6]
    tarea = {
        "id": tid,
        "descripcion": args.get("descripcion", "")[:120],
        "accion": args.get("accion", "")[:600],
        "cuando": int(args.get("cuando_epoch", 0)),
        "repetir_segundos": int(args.get("repetir_segundos", 0)),
        "activa": True
    }
    tareas, sha = leer_autotareas()
    tareas.append(tarea)
    if guardar_autotareas(tareas, sha):
        return f"Tarea {tid} programada correctamente"
    return "Error guardando la tarea en autotareas.json"


def ejecutar_autotarea(t):
    try:
        enviar_telegram(f"🤖 AUTO-TAREA EJECUTÁNDOSE: {t.get('descripcion', '')}")
        salida = correr_python(t.get("accion", t.get("descripcion", "")))
        enviar_telegram(f"🤖 Resultado de la auto-tarea:\n{salida}")
    except Exception as e:
        enviar_telegram(f"🤖 Error en auto-tarea: {type(e).__name__}: {e}")


def transcribir_audio(file_id):
    import requests
    try:
        r = requests.get(f"https://api.telegram.org/bot{TG_BOT}/getFile",
                         params={"file_id": file_id}, timeout=15)
        if r.status_code != 200:
            return f"[Error descargando audio: {r.status_code}]"
        file_path = r.json()["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{TG_BOT}/{file_path}"
        audio = requests.get(url, timeout=30).content
        files = {"file": ("audio.ogg", audio, "audio/ogg")}
        data = {"model": "whisper-large-v3", "language": "es"}
        headers = {"Authorization": f"Bearer {GROQ_KEY}"}
        r2 = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                           headers=headers, files=files, data=data, timeout=60)
        if r2.status_code != 200:
            return f"[Error transcribiendo: {r2.status_code}]"
        return r2.json().get("text", "")
    except Exception as e:
        return f"[Error en transcripción: {type(e).__name__}]"


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
    return (salida or "(sin salida)")[-3000:]


def listar_modelos(prov):
    import requests
    if MODELOS_CACHE.get(prov):
        return MODELOS_CACHE[prov]
    try:
        if prov == "groq":
            r = requests.get("https://api.groq.com/openai/v1/models",
                             headers={"Authorization": f"Bearer {GROQ_KEY}"}, timeout=20)
            prefs = ["gpt-oss-120b", "gpt-oss-20b", "maverick", "llama-3.3", "qwen", "deepseek"]
        elif prov == "cerebras":
            r = requests.get("https://api.cerebras.ai/v1/models",
                             headers={"Authorization": f"Bearer {CEREBRAS_KEY}"}, timeout=20)
            prefs = ["llama-3.3-70b", "qwen-3-32b", "llama3.1-8b"]
        elif prov == "openrouter":
            r = requests.get("https://openrouter.ai/api/v1/models", timeout=20)
            prefs = ["llama-3.3-70b-instruct:free", "qwen3-32b:free", "deepseek-chat:free", "mistral"]
        else:
            return []
        if r.status_code != 200:
            return []
        ids = [m["id"] for m in r.json().get("data", [])]
        if prov == "openrouter":
            ids = [i for i in ids if i.endswith(":free")]
        out = []
        for p in prefs:
            for i in ids:
                if p in i.lower() and i not in out:
                    out.append(i)
        for i in ids:
            if i not in out:
                out.append(i)
        MODELOS_CACHE[prov] = out
        return out
    except Exception:
        return []


def llamar_openai(prov, modelo, msgs):
    import requests
    if prov == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    elif prov == "cerebras":
        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {CEREBRAS_KEY}"}
    else:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}",
                   "HTTP-Referer": "https://evocore-backend-fjnp.onrender.com",
                   "X-Title": "EvoCore"}
    payload = {"model": modelo, "messages": msgs, "tools": TOOLS, "temperature": 0.4}
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    data = r.json()
    if "choices" in data:
        return data["choices"][0]["message"]
    raise Exception(f"{prov}/{modelo}: {r.status_code} {r.text[:120]}")


def pensar_multi(msgs):
    ultimo = ""
    for prov in ["groq", "cerebras", "openrouter"]:
        if prov == "cerebras" and not CEREBRAS_KEY:
            continue
        if prov == "openrouter" and not OPENROUTER_KEY:
            continue
        for modelo in listar_modelos(prov)[:3]:
            for intento in range(2):
                try:
                    return llamar_openai(prov, modelo, msgs)
                except Exception as e:
                    ultimo = str(e)
                    if "429" in ultimo:
                        time.sleep(10)
                        continue
                    break
    raise Exception(f"Todos los cerebros OpenAI-compatibles fallaron -> {ultimo}")


def candidato_gemini():
    modelos_validos = [
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-lite-latest"
    ]
    if MODELOS_CACHE.get("gemini") in modelos_validos:
        return MODELOS_CACHE["gemini"]
    return modelos_validos[0]


def llamar_obrero(tarea, perfil="generico"):
    import requests
    p = PERFILES.get(perfil, PERFILES["generico"])
    modelos = ["gemini-3-flash-preview", "gemini-3.1-flash-lite-preview", "gemini-flash-lite-latest"]
    for modelo in modelos:
        try:
            payload = {"contents": [{"parts": [{"text": tarea}]}],
                       "generationConfig": {"temperature": p["temperature"]}}
            if p["system"]:
                payload["system_instruction"] = {"parts": [{"text": p["system"]}]}
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}",
                json=payload, timeout=90)
            if r.status_code == 200:
                data = r.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"][:4000]
            if r.status_code in [404, 503, 429]:
                continue
            return f"obrero gemini fallo ({modelo}): {r.status_code} {r.text[:200]}"
        except Exception:
            continue
    return "obrero gemini fallo: todos los modelos agotados"


def gemini_tools():
    decls = []
    for t in TOOLS:
        f = t["function"]
        decls.append({
            "name": f["name"],
            "description": f["description"],
            "parameters": f["parameters"]
        })
    return {"function_declarations": decls}


def convertir_a_gemini(msgs):
    contents = []
    for m in msgs:
        r = m["role"]
        if r == "user":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif r == "assistant":
            parts = []
            if m.get("content"):
                parts.append({"text": m["content"]})
            for tc in m.get("tool_calls", []):
                try:
                    args = json.loads(tc["function"]["arguments"])
                except Exception:
                    args = {}
                parts.append({"function_call": {"name": tc["function"]["name"], "args": args}})
            if parts:
                contents.append({"role": "model", "parts": parts})
        elif r == "tool":
            contents.append({"role": "user", "parts": [{
                "function_response": {
                    "name": m.get("name", "ejecutar_python"),
                    "response": {"result": m["content"]}
                }}]})
    return contents


def pensar_gemini(msgs):
    import requests
    modelo = candidato_gemini()
    system = ""
    cuerpo = msgs
    if msgs and msgs[0]["role"] == "system":
        system = msgs[0]["content"]
        cuerpo = msgs[1:]
    payload = {
        "contents": convertir_a_gemini(cuerpo),
        "tools": gemini_tools()
    }
    if system:
        payload["system_instruction"] = {"parts": [{"text": system}]}
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={GEMINI_KEY}",
        json=payload, timeout=120)
    data = r.json()
    if "candidates" not in data:
        raise Exception(f"Gemini cerebro fallo: {r.status_code} {r.text[:150]}")
    parts = data["candidates"][0].get("content", {}).get("parts", [])
    texto = "".join(p.get("text", "") for p in parts)
    tcs = []
    for i, p in enumerate(parts):
        if "function_call" in p:
            fc = p["function_call"]
            tcs.append({"id": f"g{i}",
                        "function": {"name": fc.get("name", ""),
                                     "arguments": json.dumps(fc.get("args", {}))}})
    return {"content": texto or None, "tool_calls": tcs or None}


def pensar(msgs):
    try:
        return pensar_multi(msgs)
    except Exception as e:
        print(f"[cerebro] cadena openai agotada, conmutando a gemini: {e}")
    return pensar_gemini(msgs)


def atender(texto, chat):
    hist = HISTORIAL.setdefault(chat, [])
    hist.append({"role": "user", "content": texto})
    base = [{"role": "system", "content": SYSTEM_PROMPT}]
    inj = inyeccion_contexto(len(hist))
    if inj:
        base.append({"role": "system", "content": inj})
    base += hist[-8:]
    msgs = []
    for m in base:
        if m["role"] == "tool" and len(m.get("content", "")) > 1500:
            m = dict(m)
            m["content"] = m["content"][:1500] + "\n...[truncado]"
        msgs.append(m)
    resultado = None
    for _ in range(12):
        try:
            m = pensar(msgs)
        except Exception as e:
            if "413" in str(e) and len(msgs) > 4:
                msgs = [msgs[0]] + msgs[-4:]
                continue
            raise
        if m.get("tool_calls"):
            msgs.append({"role": "assistant", "content": m.get("content"), "tool_calls": m["tool_calls"]})
            for tc in m["tool_calls"]:
                args = json.loads(tc["function"]["arguments"])
                nombre = tc["function"]["name"]
                if nombre == "ejecutar_python":
                    salida = correr_python(args.get("codigo", ""))
                elif nombre == "delegar_a_obrero":
                    salida = llamar_obrero(args.get("tarea", ""), args.get("perfil", "generico"))
                elif nombre == "proponer_mejora":
                    salida = registrar_propuesta(args)
                elif nombre == "guardar_nota":
                    salida = guardar_nota(args.get("nota", ""))
                elif nombre == "programar_tarea":
                    salida = programar_tarea(args)
                else:
                    salida = "herramienta desconocida"
                if len(salida) > 1500:
                    salida = salida[:1500] + "\n...[truncado]"
                msgs.append({"role": "tool", "name": nombre, "tool_call_id": tc["id"], "content": salida})
        else:
            resultado = m.get("content") or "(sin respuesta)"
            hist.append({"role": "assistant", "content": resultado})
            break
    if resultado is None:
        resultado = "Me quede sin pasos para esta tarea."
    threading.Thread(target=persistir_contexto, args=(chat,), daemon=True).start()
    return resultado


def registrar_propuesta(args):
    import uuid
    propuesta_id = str(uuid.uuid4())[:8]
    PROPUESTAS[propuesta_id] = {
        "descripcion": args.get("descripcion", ""),
        "impacto": args.get("impacto", ""),
        "buscar": args.get("buscar", ""),
        "reemplazar": args.get("reemplazar", ""),
        "estado": "pendiente",
        "timestamp": time.time()
    }
    cuerpo = f"""💡 PROPUESTA DE MEJORA (ID: {propuesta_id})

📝 Descripción:
{args.get("descripcion", "")}

🎯 Impacto:
{args.get("impacto", "")}

🔧 Cambio quirúrgico:
- Busca este fragmento exacto:
{args.get("buscar", "")[:400]}
- Lo reemplaza por:
{args.get("reemplazar", "")[:400]}"""
    if CONTEXTO.get("modo_autonomo"):
        enviar_telegram(cuerpo + f"\n\n🟢 MODO AUTÓNOMO: aplicando sin esperar aprobación.")
        threading.Thread(target=aplicar_inmediata, args=(propuesta_id,), daemon=True).start()
    else:
        enviar_telegram(cuerpo + f"\n\n🔴 MODO SUPERVISADO: queda esperando TU decisión sin límite de tiempo.\n- 'apruebo {propuesta_id}' → se aplica\n- 'rechazo {propuesta_id}' → se descarta")
    return f"Propuesta {propuesta_id} registrada (modo {'autonomo' if CONTEXTO.get('modo_autonomo') else 'supervisado'})"


def aplicar_inmediata(propuesta_id):
    time.sleep(2)
    aprobar_propuesta(propuesta_id, auto=True)


def encontrar_fragmento(contenido, buscar):
    if buscar in contenido:
        return buscar
    lines = contenido.splitlines()
    b_lines = [l.strip() for l in buscar.splitlines() if l.strip()]
    if not b_lines:
        return None
    for i in range(len(lines) - len(b_lines) + 1):
        window = [l.strip() for l in lines[i:i + len(b_lines)]]
        if window == b_lines:
            return "\n".join(lines[i:i + len(b_lines)])
    return None


def aprobar_propuesta(propuesta_id, auto=False):
    import requests
    if propuesta_id not in PROPUESTAS:
        return "Propuesta no encontrada"
    p = PROPUESTAS[propuesta_id]
    if p["estado"] != "pendiente":
        return f"Propuesta ya fue {p['estado']}"
    buscar = p.get("buscar", "")
    reemplazar = p.get("reemplazar", "")
    if not buscar or not reemplazar:
        return "Propuesta incompleta: faltan buscar/reemplazar"
    try:
        r = requests.get("https://api.github.com/repos/maximilianorojas2705-lumi/Evocore-backend/contents/Main.py",
                         headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=30)
        if r.status_code != 200:
            return f"Error leyendo Main.py: {r.status_code}"
        data = r.json()
        sha = data["sha"]
        contenido = base64.b64decode(data["content"]).decode()
        frag = encontrar_fragmento(contenido, buscar)
        if frag is None:
            p["estado"] = "fallida"
            return f"❌ El fragmento 'buscar' no existe en Main.py. Propuesta {propuesta_id} marcada como fallida."
        if contenido.count(frag) > 1:
            return f"⚠️ El fragmento aparece {contenido.count(frag)} veces: ambiguo."
        lines_orig = frag.splitlines()
        indent = lines_orig[0][:len(lines_orig[0]) - len(lines_orig[0].lstrip())]
        r_lines = reemplazar.splitlines()
        if indent and r_lines and not r_lines[0].startswith(indent):
            r_lines = [(indent + l) if l.strip() else l for l in r_lines]
        nuevo_frag = "\n".join(r_lines)
        nuevo = contenido.replace(frag, nuevo_frag, 1)
        r2 = requests.put("https://api.github.com/repos/maximilianorojas2705-lumi/Evocore-backend/contents/Main.py",
                          headers={"Authorization": f"Bearer {GH_TOKEN}"},
                          json={
                              "message": f"Auto-mejora {propuesta_id}: {p['descripcion'][:40]}",
                              "content": base64.b64encode(nuevo.encode()).decode(),
                              "sha": sha
                          }, timeout=30)
        if r2.status_code in [200, 201]:
            p["estado"] = "aprobada"
            if auto:
                enviar_telegram(f"🟢 Propuesta {propuesta_id} APLICADA (modo autónomo). Commit hecho, deploy en curso...")
            else:
                enviar_telegram(f"✅ Propuesta {propuesta_id} APLICADA por aprobación de Maxi. Commit hecho, deploy en curso...")
            return "Mejora aplicada"
        return f"Error en commit: {r2.status_code} {r2.text[:200]}"
    except Exception as e:
        return f"Error aplicando mejora: {type(e).__name__}: {e}"


def leer_recordatorios():
    import requests
    r = requests.get("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/recordatorios.json",
                     headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=15)
    if r.status_code == 404:
        return [], None
    if r.status_code != 200:
        return [], None
    data = r.json()
    try:
        return json.loads(base64.b64decode(data["content"]).decode()), data["sha"]
    except Exception:
        return [], data["sha"]


def guardar_recordatorios(lista, sha):
    import requests
    body = {
        "message": "recordatorios actualizados",
        "content": base64.b64encode(json.dumps(lista, ensure_ascii=False, indent=1).encode()).decode()
    }
    if sha:
        body["sha"] = sha
    r = requests.put("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/recordatorios.json",
                     headers={"Authorization": f"Bearer {GH_TOKEN}"}, json=body, timeout=15)
    return r.status_code in [200, 201]


def procesar(texto, chat):
    t = texto.lower().strip()
    if t.startswith("modo autonomo") or t.startswith("modo autónomo") or t.startswith("segui de corrido") or t.startswith("seguí de corrido"):
        if set_modo(True):
            enviar_telegram("🟢 MODO AUTÓNOMO ACTIVADO: las propuestas se auto-aplican al instante sin esperarte. Decí 'frená' o 'modo supervisado' para recuperar el control total.", chat)
        else:
            enviar_telegram("⚠️ No pude guardar el modo en memoria; queda autónomo solo en esta sesión.", chat)
        return
    if t.startswith("modo supervisado") or t.startswith("frena") or t.startswith("frená") or t.startswith("detene") or t.startswith("detené"):
        if set_modo(False):
            enviar_telegram("🔴 MODO SUPERVISADO ACTIVADO: toda auto-modificación espera TU aprobación sin límite de tiempo. Nada se aplica sin tu 'apruebo'.", chat)
        else:
            enviar_telegram("⚠️ No pude guardar el modo en memoria; queda supervisado solo en esta sesión.", chat)
        return
    if t.startswith("apruebo "):
        propuesta_id = texto[8:].strip()
        resultado = aprobar_propuesta(propuesta_id)
        enviar_telegram(resultado, chat)
        return
    if t.startswith("rechazo "):
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
        analisis = llamar_obrero(tarea, "reviewer")
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
    voice = msg.get("voice")
    audio = msg.get("audio")
    chat = str(msg.get("chat", {}).get("id", ""))
    
    if voice or audio:
        file_id = (voice or audio).get("file_id")
        if file_id and chat:
            def procesar_audio():
                transcrito = transcribir_audio(file_id)
                if transcrito.startswith("["):
                    enviar_telegram(transcrito, chat)
                else:
                    enviar_telegram(f"🎤 Escuché: {transcrito}", chat)
                    procesar(transcrito, chat)
            threading.Thread(target=procesar_audio, daemon=True).start()
    
    if texto and chat:
        threading.Thread(target=procesar, args=(texto, chat), daemon=True).start()
    return {"ok": True}


def generar_reporte_semanal():
    import requests
    try:
        ahora = datetime.now(timezone.utc)
        hace_7_dias = ahora - timedelta(days=7)
        reporte = f"📊 REPORTE SEMANAL ({ahora.strftime('%d/%m/%Y')})\n\n"
        reporte += "🔍 Revisión de código:\n"
        repos = ["maximilianorojas2705-lumi/Earnfi", "maximilianorojas2705-lumi/nexus-backend"]
        for repo in repos:
            r = requests.get(f'https://api.github.com/repos/{repo}/commits',
                           headers={"Authorization": f"Bearer {GH_TOKEN}"},
                           params={"since": hace_7_dias.isoformat()},
                           timeout=15)
            if r.status_code == 200:
                commits = r.json()
                reporte += f"- {repo.split('/')[-1]}: {len(commits)} commits\n"
        reporte += "\n💰 Bitcoin:\n"
        try:
            r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', timeout=15).json()
            precio = r['bitcoin']['usd']
            reporte += f"- Precio actual: ${precio:,.0f}\n"
        except Exception:
            reporte += "- Error consultando precio\n"
        reporte += "\n⏰ Recordatorios:\n"
        recs, _ = leer_recordatorios()
        total = len(recs)
        enviados = sum(1 for r in recs if r.get("enviado"))
        reporte += f"- Total: {total}, Disparados: {enviados}\n"
        reporte += "\n🛠️ Herramientas creadas:\n"
        try:
            r = requests.get('https://api.github.com/repos/maximilianorojas2705-lumi/evocore-herramientas/contents/tools',
                           headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=15)
            if r.status_code == 200:
                tools = [f['name'].replace('.py', '') for f in r.json() if f['name'].endswith('.py')]
                reporte += f"- {', '.join(tools) if tools else 'Ninguna'}\n"
        except Exception:
            reporte += "- Error consultando herramientas\n"
        reporte += "\n✨ Agente operativo y evolucionando."
        enviar_telegram(reporte)
    except Exception as e:
        print(f"[reporte] error: {e}")


def latido():
    import requests
    try:
        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true', timeout=15).json()
        p = r['bitcoin']['usd']
        c24 = r['bitcoin']['usd_24h_change']
        if STATE["last_btc"] and abs(p - STATE["last_btc"]) / STATE["last_btc"] * 100 >= 3:
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
    try:
        recs, sha = leer_recordatorios()
        cambiados = False
        ahora = time.time()
        for rec in recs:
            if not rec.get("enviado") and rec.get("cuando", 0) <= ahora:
                enviar_telegram(f"⏰ RECORDATORIO: {rec.get('texto', '')}")
                rec["enviado"] = True
                cambiados = True
        if cambiados:
            guardar_recordatorios(recs, sha)
    except Exception as e:
        print(f"[latido] recordatorios: {e}")
    try:
        tareas, sha = leer_autotareas()
        ahora = time.time()
        cambiados = False
        for t in tareas:
            if t.get("activa") and t.get("cuando", 0) <= ahora:
                threading.Thread(target=ejecutar_autotarea, args=(t,), daemon=True).start()
                if t.get("repetir_segundos"):
                    t["cuando"] = ahora + t["repetir_segundos"]
                else:
                    t["activa"] = False
                cambiados = True
        if cambiados:
            guardar_autotareas(tareas, sha)
    except Exception as e:
        print(f"[latido] autotareas: {e}")
    try:
        ahora_arg = datetime.now(timezone(timedelta(hours=-3)))
        es_domingo = ahora_arg.weekday() == 6
        es_hora = ahora_arg.hour == 20 and ahora_arg.minute < 10
        if es_domingo and es_hora and STATE["last_report"] != ahora_arg.strftime("%Y-%m-%d"):
            generar_reporte_semanal()
            STATE["last_report"] = ahora_arg.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"[latido] reporte semanal: {e}")


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
