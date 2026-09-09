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
TAVILY_KEY = os.environ.get("TAVILY_KEY", "")

SYSTEM_PROMPT = """Sos EvoCore, el agente evolutivo personal de Maxi, con autonomia tecnica maxima.
Trabajas 100% en la nube desde tu propio servidor. NUNCA des comandos para ejecutar en local (git, pip, terminal).
Tenes la herramienta ejecutar_python: corre codigo en este mismo servidor, con internet y librerias libres.
Para buscar en la web usa la API de Tavily con os.environ["TAVILY_KEY"].
Para memoria persistente usa el repo maximilianorojas2705-lumi/evocore-memoria (memoria.json) con os.environ["GH_TOKEN"].
Datos de Maxi: GitHub maximilianorojas2705-lumi, repos Earnfi y nexus-backend, proyecto creaciones HTML, prefiere respuestas tecnicas y directas.
Estilo: directo, sin sermones. Usa emojis ok/atencion/critico.
Despues de cada tarea agrega mini ciclo evolutivo: que hiciste, que salio mal, que aprendiste.

MISION DIARIA DE VIGILANCIA Y POTENCIACION:
Tenés dos auto-tareas programadas que corren solas:
- Digestivo IA (08:00 ARG): busca novedades en IA, agentes, herramientas, monetizacion, informatica, ciberseguridad. Usás Tavily (os.environ['TAVILY_KEY']) para 5-8 queries especificas, luego delegás al obrero 'investigador' para que estudie todo y devuelva: 5 novedades top, 3 sugerencias de mejora para EvoCore, 2 oportunidades de dinero nuevas.
- Radar de dinero (09:00 y 19:00 ARG): busca oportunidades ACTIVAS con deadline real: grants de IA/open source, bug bounties de ciberseguridad, airdrops de protocolos nuevos, gigs freelance matching tus skills, arbitrajes. Entregá el resultado filtrado: SOLO oportunidades reales con URL y fecha limite.

SOBRE TRAER DINERO: Maxi puede pedirte que traigas plata o que hagas cosas para ganar dinero. RESPUESTA REALISTA: no existe el dinero sin friccion. Lo que SI podes hacer es (1) buscarle oportunidades reales del radar, (2) construirle herramientas que automaticen tareas monetizables (scraping, analisis, deteccion), (3) ejecutar tareas tecnicas que el decida monetizar. Nunca prometas magia; siempre propongas trabajo + automatizacion.

COMANDOS RAPIDOS DEL SERVIDOR: Maxi tiene /btc /dolar /clima /memoria /estado /ayuda que responde el servidor directo sin pasar por vos.
Comandos nuevos: /oportunidades (resume el ultimo radar de dinero), /digestivo (muestra el ultimo digestivo IA guardado).

OBREROS ESPECIALISTAS (herramienta delegar_a_obrero con parametro perfil):
- 'reviewer': revisor de codigo senior estricto, cazador de bugs y riesgos.
- 'investigador': creativo para brainstorm, análisis de tendencias, sugerencias de potenciacion. USALO SIEMPRE para el digestivo y para sugerencias de mejora.
- 'resumidor': sintetizador extremo en bullets densos.
- 'generico': el de siempre.
Elegi el perfil segun la tarea; si Maxi pide explicitamente un especialista, usalo.
Delegá cuando: la tarea sea pesada o larga, o necesites procesamiento masivo de texto.
Vos sos el JEFE: integra lo que devuelve el obrero con tu criterio, no lo copies a ciegas.
AL DELEGAR: el obrero no tiene tu memoria, tu historial ni tus herramientas: la tarea que le mandes debe incluir todos los datos que necesita.

HERRAMIENTAS AUTO-CREADAS (tu propio app store en el repo maximilianorojas2705-lumi/evocore-herramientas, carpeta tools/):
- LISTAR las que ya tenes:
import requests, os
r = requests.get('https://api.github.com/repos/maximilianorojas2705-lumi/evocore-herramientas/contents/tools', headers={'Authorization': f'token {os.environ["GH_TOKEN"]}'})
print([f['name'] for f in r.json()])
- USAR una:
import requests, os
r = requests.get('https://raw.githubusercontent.com/maximilianorojas2705-lumi/evocore-herramientas/main/tools/NOMBRE.py', headers={'Authorization': f'token {os.environ["GH_TOKEN"]}'})
exec(r.text)
- CREAR una nueva: cuando resuelvas una tarea con codigo reutilizable (scraper, parser, analizador, consultor de APIs, radar de oportunidades), guardala como tools/nombre.py con funciones documentadas, usando la API de GitHub (PUT contents con base64, igual que con la memoria).
HERRAMIENTAS QUE DEBES CREAR SI NO EXISTEN:
- tools/oportunidades.py: busca grants de IA, bug bounties, airdrops y gigs freelance activos
- tools/cripto_radar.py: precios, arbitrajes y oportunidades cripto
- tools/tavily_search.py: wrapper reutilizable para búsquedas en Tavily
REGLA DE ORO: antes de escribir codigo desde cero, lista tus herramientas y revisa si alguna ya lo hace.
SI ejecutar_python falla 2 veces seguidas con el mismo error, NO reintentes: detenete y explicame el error.

REGLA ANTI-ATRAGANTAMIENTO (muy importante):
Cuando leas archivos grandes, NUNCA imprimas el contenido completo: rompe el limite de tokens.
Imprimi SOLO el fragmento que necesitas, usando busqueda y rebanado.

AUTO-MODIFICACIÓN QUIRÚRGICA CON CONTROL DE MAXI:
CUANDO detectes una mejora posible a tu código, DEBES usar la herramienta proponer_mejora.
ANTES de proponer, lee SOLO el fragmento relevante de tu Main.py.
NUNCA propongas reescribir todo el archivo: siempre cambios quirúrgicos y mínimos.
HAY DOS MODOS DE CONTROL:
- MODO SUPERVISADO (por defecto): cada propuesta espera tu aprobacion SIN limite de tiempo.
- MODO AUTONOMO (cuando Maxi dice 'segui de corrido'): las propuestas se auto-aplican al instante.
Respeta siempre el modo vigente.
CADA mejora aplicada genera automaticamente un REPORTE por Telegram y queda anotada en historial_mejoras.json. Si Maxi pide 'lista actualizaciones', mostrale las ultimas del historial.
Si una propuesta tiene buscar identico a reemplazar, la herramienta la descarta sola (guarda anti-no-op).

RECORDATORIOS CON FECHA: guardalos en recordatorios.json, hora argentina UTC-3. El latido los envia cuando llega la hora.

MEMORIA DE LARGO PLAZO: contexto.json con resumen, ultimos mensajes, notas, modo_autonomo.
Cuando Maxi diga 'acordate de X' o detectes un dato importante, usa guardar_nota.

AUTO-TAREAS: programa con programar_tarea. El latido ejecuta las vencidas cada 5 min."""

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
            "perfil": {"type": "string", "enum": ["generico", "reviewer", "investigador", "resumidor"], "description": "Especialista a usar"}},
            "required": ["tarea"]}}},
    {"type": "function", "function": {
        "name": "proponer_mejora",
        "description": "Propone un cambio quirurgico al propio Main.py; se aplica segun el modo de control vigente",
        "parameters": {"type": "object", "properties": {
            "descripcion": {"type": "string", "description": "Descripción clara de la mejora"},
            "impacto": {"type": "string", "description": "Qué beneficio trae"},
            "buscar": {"type": "string", "description": "Fragmento EXACTO y unico del Main.py actual que se va a reemplazar"},
            "reemplazar": {"type": "string", "description": "Codigo nuevo exacto que ira en lugar del fragmento"}},
            "required": ["descripcion", "impacto", "buscar", "reemplazar"]}}},
    {"type": "function", "function": {
        "name": "guardar_nota",
        "description": "Guarda una nota permanente en la memoria de largo plazo",
        "parameters": {"type": "object", "properties": {
            "nota": {"type": "string", "description": "Texto corto de la nota"}},
            "required": ["nota"]}}},
    {"type": "function", "function": {
        "name": "programar_tarea",
        "description": "Programa una tarea automatica que el latido ejecutara sola (unica o recurrente)",
        "parameters": {"type": "object", "properties": {
            "descripcion": {"type": "string", "description": "Nombre corto de la tarea"},
            "accion": {"type": "string", "description": "Codigo Python autocontenido que se ejecutara directamente"},
            "cuando_epoch": {"type": "integer", "description": "Epoch UTC de la primera ejecucion"},
            "repetir_segundos": {"type": "integer", "description": "0 si es unica; segundos entre repeticiones si es recurrente"}},
            "required": ["descripcion", "accion", "cuando_epoch", "repetir_segundos"]}}}
]

HISTORIAL = {}
STATE = {"last_btc": None, "last_commits": {}, "last_report": None, "turnos": 0,
         "last_digestivo": "", "last_radar": ""}
MODELOS_CACHE = {}
PROPUESTAS = {}

PERFILES = {
    "reviewer": {
        "system": "Sos un revisor de codigo senior extremadamente estricto y preciso. Tu trabajo es cazar bugs, riesgos de seguridad, errores de logica y problemas de rendimiento. Se tecnico, directo y concreto.",
        "temperature": 0.2
    },
    "investigador": {
        "system": "Sos un investigador creativo y experto en IA, agentes, monetizacion y ciberseguridad. Cuando recibas datos crudos de busquedas, sintetizalos en: novedades reales (no inventes), sugerencias concretas y accionables para mejorar un agente, y oportunidades de dinero con URLs y deadlines reales. Se directo, no vendas humo, marca claramente lo que es especulacion.",
        "temperature": 0.7
    },
    "resumidor": {
        "system": "Sos un sintetizador profesional. Comprimis cualquier contenido en bullets cortos y densos, sin perder decisiones, pendientes ni datos clave.",
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


def comando_rapido(texto):
    import requests
    t = texto.strip().lower()
    try:
        if t == "/btc":
            r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true', timeout=15).json()
            p = r['bitcoin']['usd']
            c = r['bitcoin']['usd_24h_change']
            return f"💰 BTC: ${p:,.0f} USD | 24h: {c:+.1f}%"
        if t == "/dolar":
            r = requests.get('https://dolarapi.com/v1/dolares', timeout=15).json()
            lineas = []
            for d in r:
                lineas.append(f"- {d.get('nombre', '?')}: compra {d.get('compra', '?')} / venta {d.get('venta', '?')}")
            return "💵 Dólares Argentina:\n" + "\n".join(lineas)
        if t.startswith("/clima"):
            ciudad = texto.strip()[6:].strip() or "Cordoba"
            g = requests.get('https://geocoding-api.open-meteo.com/v1/search',
                             params={'name': ciudad, 'count': 1}, timeout=15).json()
            res = g.get('results') or []
            if not res:
                return f"⚠️ No encontré la ciudad: {ciudad}"
            lat = res[0]['latitude']
            lon = res[0]['longitude']
            nombre = res[0]['name']
            w = requests.get('https://api.open-meteo.com/v1/forecast',
                             params={'latitude': lat, 'longitude': lon, 'current_weather': 'true'}, timeout=15).json()
            cw = w.get('current_weather', {})
            return f"🌤️ {nombre}: {cw.get('temperature', '?')}°C | viento {cw.get('windspeed', '?')} km/h"
        if t == "/memoria":
            notas = CONTEXTO.get('notas', [])[-5:]
            recs, _ = leer_recordatorios()
            pendientes = [x for x in recs if not x.get('enviado')]
            tareas, _ = leer_autotareas()
            activas = [x for x in tareas if x.get('activa')]
            lineas = ["📝 Últimas notas:"]
            if notas:
                lineas += [f"- {n}" for n in notas]
            else:
                lineas.append("- (sin notas)")
            lineas.append(f"⏰ Recordatorios pendientes: {len(pendientes)}")
            lineas.append(f"🤖 Auto-tareas activas: {len(activas)}")
            lineas.append(f"🕐 Modo: {'autónomo' if CONTEXTO.get('modo_autonomo') else 'supervisado'}")
            return "\n".join(lineas)
        if t == "/estado":
            lineas = [f"🕐 Modo: {'autónomo' if CONTEXTO.get('modo_autonomo') else 'supervisado'}"]
            if STATE.get('last_btc'):
                lineas.append(f"💰 Último BTC: ${STATE['last_btc']:,.0f}")
            tareas, _ = leer_autotareas()
            lineas.append(f"🤖 Auto-tareas activas: {len([x for x in tareas if x.get('activa')])}")
            recs, _ = leer_recordatorios()
            lineas.append(f"⏰ Recordatorios pendientes: {len([x for x in recs if not x.get('enviado')])}")
            lineas.append("🧠 Cerebros: groq + cerebras + openrouter + gemini")
            lineas.append("🐕 Centinelas: uptime + render + actions")
            return "\n".join(lineas)
        if t == "/oportunidades":
            return STATE.get("last_radar") or "⏳ Todavía no corrió ningún radar. Esperá a las 09:00 o 19:00, o pedile al agente que corra uno ahora."
        if t == "/digestivo":
            return STATE.get("last_digestivo") or "⏳ Todavía no corrió ningún digestivo. Esperá a las 08:00 o pedile al agente que corra uno ahora."
        if t in ["/ayuda", "/comandos"]:
            return ("⚡ Comandos rápidos (instantáneos, sin cerebro):\n"
                    "/btc · /dolar · /clima [ciudad] · /memoria · /estado\n"
                    "/oportunidades · /digestivo · /ayuda\n\n"
                    "🎛️ Control:\n"
                    "modo supervisado · segui de corrido · frena\n"
                    "apruebo [ID] · rechazo [ID] · listá actualizaciones")
    except Exception as e:
        return f"⚠️ Comando falló: {type(e).__name__}: {e}"
    return None


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
        guardar_contexto_ctx(ctx_completo())
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


def leer_historial_mejoras():
    import requests
    try:
        r = requests.get("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/historial_mejoras.json",
                         headers={"Authorization": f"Bearer {GH_TOKEN}"}, timeout=15)
        if r.status_code != 200:
            return [], None
        data = r.json()
        try:
            return json.loads(base64.b64decode(data["content"]).decode()), data["sha"]
        except Exception:
            return [], data["sha"]
    except Exception:
        return [], None


def registrar_mejora_aplicada(p, propuesta_id, modo):
    import requests
    try:
        hist, sha = leer_historial_mejoras()
        hist.append({
            "id": propuesta_id,
            "fecha": datetime.now(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M"),
            "descripcion": p.get("descripcion", "")[:200],
            "impacto": p.get("impacto", "")[:200],
            "modo": modo,
            "buscar": p.get("buscar", "")[:150],
            "reemplazar": p.get("reemplazar", "")[:150]
        })
        hist = hist[-30:]
        body = {"message": "historial de mejoras actualizado",
                "content": base64.b64encode(json.dumps(hist, ensure_ascii=False, indent=1).encode()).decode()}
        if sha:
            body["sha"] = sha
        requests.put("https://api.github.com/repos/maximilianorojas2705-lumi/evocore-memoria/contents/historial_mejoras.json",
                     headers={"Authorization": f"Bearer {GH_TOKEN}"}, json=body, timeout=15)
    except Exception as e:
        print(f"[mejoras] error registrando: {e}")


def reporte_actualizacion(p, propuesta_id, modo):
    return f"""📋 REPORTE DE ACTUALIZACIÓN (ID {propuesta_id})

🔧 Qué se cambió:
{p.get('descripcion', '')}

🎯 Para qué sirve:
{p.get('impacto', '')}

📄 Antes:
{p.get('buscar', '')[:300]}

📄 Ahora:
{p.get('reemplazar', '')[:300]}

🕐 Modo de aprobación: {modo}
🗂️ Anotado en historial_mejoras.json
🚀 Commit hecho, deploy en curso (~1-2 min)"""


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
    if args.get('buscar', '').strip() == args.get('reemplazar', '').strip():
        return 'Propuesta descartada: no hay diferencias entre buscar y reemplazar'
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
        enviar_telegram(cuerpo + "\n\n🟢 MODO AUTÓNOMO: aplicando sin esperar aprobación.")
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
            modo_txt = "autónomo (auto-aplicada sin espera)" if auto else "aprobación manual de Maxi"
            registrar_mejora_aplicada(p, propuesta_id, modo_txt)
            enviar_telegram(reporte_actualizacion(p, propuesta_id, modo_txt))
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
    if texto.strip().startswith("/"):
        r = comando_rapido(texto)
        if r is not None:
            enviar_telegram(r, chat)
            return
    t = texto.lower().strip()
    if t.startswith("modo autonomo") or t.startswith("modo autónomo") or t.startswith("segui de corrido") or t.startswith("seguí de corrido"):
        if set_modo(True):
            enviar_telegram("🟢 MODO AUTÓNOMO ACTIVADO: las propuestas se auto-aplican al instante.", chat)
        else:
            enviar_telegram("⚠️ No pude guardar el modo en memoria.", chat)
        return
    if t.startswith("modo supervisado") or t.startswith("frena") or t.startswith("frená") or t.startswith("detene") or t.startswith("detené"):
        if set_modo(False):
            enviar_telegram("🔴 MODO SUPERVISADO ACTIVADO: toda auto-modificación espera TU aprobación.", chat)
        else:
            enviar_telegram("⚠️ No pude guardar el modo en memoria.", chat)
        return
    if t.startswith("lista actualizaciones") or t.startswith("listá actualizaciones") or t.startswith("actualizaciones"):
        hist, _ = leer_historial_mejoras()
        if not hist:
            enviar_telegram("📋 No hay actualizaciones registradas todavía.", chat)
        else:
            lineas = []
            for h in hist[-10:]:
                lineas.append(f"• {h.get('fecha', '')} | ID {h.get('id', '')} | {h.get('modo', '')}\n   Qué: {h.get('descripcion', '')}\n   Para qué: {h.get('impacto', '')}")
            enviar_telegram("📋 ÚLTIMAS ACTUALIZACIONES APLICADAS:\n\n" + "\n\n".join(lineas), chat)
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
            analisis = f"📝 Commit: {mensaje}\n📄 Archivos: {nombres}"
        enviar_telegram(f"🔍 Revisión de commit en {repo.split('/')[-1]}:\n\n{analisis}")
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
