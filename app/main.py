# ---------- app/main.py (bloque listo para pegar) ----------
import os
import json
from datetime import datetime
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
from dotenv import load_dotenv
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import task
from .logic import postproceso_modelo, armar_respuesta_final
from .prompts import SYSTEM_INSTRUCTIONS


load_dotenv()

# Flags / envs
USE_VERTEX = os.getenv("USE_VERTEX", "true").lower() == "true"
VERTEX_REGION = os.getenv("VERTEX_REGION", "us-central1")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")

# App FastAPI
app = FastAPI(title="POC Interprete Panadería", version="1.0.0")

Traceloop.init(
    disable_batch=True,
    api_key=os.getenv("TRACELOOP_API_KEY"),
)

# Vertex init (opcional según USE_VERTEX)
GEMINI = None
if USE_VERTEX:
    try:
        from vertexai import init as vertex_init
        from vertexai.generative_models import GenerativeModel
        vertex_init(project=PROJECT_ID, location=VERTEX_REGION)
        # Puedes usar "gemini-1.5-flash" en desarrollo si prefieres menor latencia/costo
        GEMINI = GenerativeModel(MODEL_NAME)
    except Exception as e:
        print("Vertex no disponible, se usará fallback local. Error:", e)
        GEMINI = None
        USE_VERTEX = False

# --------- Modelo de request (agrego usar_modelo opcional por solicitud) ----------
class Peticion(BaseModel):
    texto_libre: str = Field(..., description="Texto del cliente")
    canal: Literal["formulario_web","whatsapp","email","telefono","otro"] = "formulario_web"
    usar_modelo: Optional[bool] = None  # Si lo envías, sobrescribe USE_VERTEX por request

# ------------------------ ENDPOINT PRINCIPAL ------------------------
@app.post("/interpretar", name="interpretar_pedido")
@task(name="interpretar_pedido_span")
def interpretar(peticion: Peticion = Body(...)):
    texto = (peticion.texto_libre or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="texto_libre vacío.")

    # Decide si usamos IA en esta solicitud
    usar_modelo = peticion.usar_modelo if peticion.usar_modelo is not None else USE_VERTEX

    interpretacion = None

    # ---------- Llamado a Gemini (fix: lista de strings, sin Part/Content) ----------
    if usar_modelo and GEMINI is not None:
        try:
            resp = GEMINI.generate_content(
                [
                    SYSTEM_INSTRUCTIONS,
                    f"Texto del cliente:\n\n{texto}\n\nDevuelve SOLO el JSON del campo interpretacion_IA."
                ],
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 1024,
                    "response_mime_type": "application/json",
                },
            )
            raw = resp.text

            # Fallback por si .text viniera vacío
            if not raw:
                try:
                    raw = resp.candidates[0].content.parts[0].text
                except Exception:
                    raw = None

            # DEBUG: imprime el JSON crudo del modelo antes del postproceso
            if DEBUG_MODE:
                print("\n========== DEBUG: RESPUESTA CRUDA DEL MODELO ==========")
                print(raw if raw is not None else "<VACÍO>")
                print("=======================================================\n")

            if raw:
                interpretacion = json.loads(raw)

        except Exception as e:
            print("Error Vertex:", e)

    # ---------- Fallback local si no hubo modelo o falló ----------
    if not interpretacion:
        interpretacion = {
            "accion": "extraccion_pedido",
            "detalles": {
                "cliente": {"nombre": None, "telefono": None, "email": None},
                "direccion_entrega": {
                    "texto": None, "ciudad": None, "barrio": None,
                    "observaciones_entrega": None, "lat": None, "lng": None, "nivel_confianza": 0.5
                },
                "ventana_entrega": {
                    "inicio_iso": None, "fin_iso": None,
                    "expresion_detectada": None, "nivel_confianza": 0.5
                },
                "items": [],
                "restricciones": {
                    "manejo_fragil": False, "temperatura_controlada": False,
                    "acceso_restringido": False, "notas": []
                }
            },
            "normalizacion": {
                "diccionario_sinonimos": {
                    "buñuelos": ["bunuelos", "buñuelo"],
                    "arepas de maíz": ["arepas", "arepa de maiz"]
                },
                "reglas_tiempo": "Expresiones relativas convertidas a rango de fecha y hora en zona America/Bogota (UTC-5).",
                "politica_unidades": "Si no se especifica, unidad = 'unidad'."
            },
            "validaciones": {
                "campos_obligatorios": {
                    "direccion_entrega": False, "ventana_entrega": False, "items": False
                },
                "advertencias": [],
                "ambiguedades": []
            }
        }

        # Heurística simple para items y fragilidad
        import re
        for cant, nombre in re.findall(r"(\d+)\s+([a-záéíóúñ\s]+?)(?:,|\.|\by\b|$)", texto.lower()):
            nombre = nombre.strip()
            if any(x in nombre for x in ["buñuelo","bunuelos","buñuelos"]):
                interpretacion["detalles"]["items"].append({
                    "sku": None, "nombre_detectado": "buñuelos", "nombre_normalizado": "Buñuelos",
                    "cantidad": int(cant), "unidad": "unidad", "peso_kg": None, "volumen_m3": None, "nivel_confianza": 0.9
                })
            if any(x in nombre for x in ["arepa","arepas","arepa de maiz","arepas de maiz","arepas de maíz"]):
                interpretacion["detalles"]["items"].append({
                    "sku": None, "nombre_detectado": "arepas de maíz", "nombre_normalizado": "Arepas de maíz",
                    "cantidad": int(cant), "unidad": "unidad", "peso_kg": None, "volumen_m3": None, "nivel_confianza": 0.9
                })
        if "frágil" in texto.lower() or "fragil" in texto.lower():
            interpretacion["detalles"]["restricciones"]["manejo_fragil"] = True
            interpretacion["detalles"]["restricciones"]["notas"].append("Empacar frágil")

    # ---------- Postproceso local (tiempos, dirección, validaciones, etc.) ----------
    interpretacion = postproceso_modelo(interpretacion, texto)

    # ---------- Ensamble final (contrato JSON de salida) ----------
    respuesta = armar_respuesta_final(
        texto_libre=texto,
        canal=peticion.canal,
        interpretacion=interpretacion,
        nivel_confianza=0.92
    )
    return respuesta
# ---------- fin del bloque ----------
BASE_DIR = Path(__file__).resolve().parents[1]   # carpeta raíz del proyecto
WEB_DIR = BASE_DIR / "web"                       # <raíz>/web/index.html

if not WEB_DIR.exists():
    print(f"[WARN] Carpeta web no encontrada: {WEB_DIR}")
# Monta al final para no interferir con /interpretar
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="webroot")
