import re
import uuid
import pytz
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from typing import Tuple, Optional, Dict, Any, List

TZ = pytz.timezone("America/Bogota")

SINONIMOS = {
    "buñuelos": ["bunuelos", "buñuelo", "bunelo", "bunuelos"],
    "arepas de maíz": ["arepas", "arepa de maiz", "arepa", "arepas de maiz"]
}

def now_iso() -> str:
    return datetime.now(TZ).isoformat()

def generar_pedido_id() -> str:
    return f"ORD-{str(uuid.uuid4())[:8].upper()}"

def generar_uuid_operacion() -> str:
    return str(uuid.uuid4())

def normalizar_item_nombre(nombre_detectado: str) -> str:
    nd = (nombre_detectado or "").strip().lower()
    for canonico, lista in SINONIMOS.items():
        if nd == canonico.lower() or nd in [x.lower() for x in lista]:
            return canonico
    # simplificación: mayúscula inicial para "desconocidos"
    return nd.capitalize() if nd else nd

def detectar_manejo_fragil(texto: str) -> bool:
    return bool(re.search(r"\b(frágil|fragil)\b", texto.lower()))

def detectar_temp_controlada(texto: str) -> bool:
    return bool(re.search(r"\b(frío|frio|refrigerad|congelad|temperatura controlada)\b", texto.lower()))

def detectar_acceso_restringido(texto: str) -> bool:
    return bool(re.search(r"\b(portería|porteria|acceso restringido|autorización|autorizacion)\b", texto.lower()))

def extraer_telefono(texto: str) -> Optional[str]:
    m = re.search(r"(?:\+?57)?\s?3\d{9}", texto.replace(" ", ""))
    return m.group(0)[-10:] if m else None

def extraer_email(texto: str) -> Optional[str]:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texto)
    return m.group(0) if m else None

def extraer_direccion_y_ciudad(texto: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    # Heurística simple: busca "Cra|Calle|Av|Carrera|Transv|#|N°", barrio y ciudad comunes (ej: Bogotá)
    t = texto.strip()
    dir_pat = r"(?:cra|cr|carrera|calle|cll|av|avenida|transv|transversal|diag|diagonal)\s?[0-9a-zA-Z#\s\-\.\,]+"
    m = re.search(dir_pat, t, re.IGNORECASE)
    direccion = m.group(0).strip(" .,") if m else None

    ciudad = None
    if re.search(r"\b(bogotá|bogota)\b", t, re.IGNORECASE): ciudad = "Bogotá"

    # Barrio: extrae después de "en|para|a|en el barrio|barrio" + palabra capitalizada o conocida
    barrio = None
    b = re.search(r"(?:barrio\s+)?(chapinero|cedritos|usaqu[eé]n|suba|kennedy|fontib[oó]n|teusaquillo)", t, re.IGNORECASE)
    if b: barrio = b.group(1).capitalize()

    obs = None
    obs_m = re.search(r"(entregar en [^\.]+|port[eí]a|recepci[oó]n|piso\s?\d+)", t, re.IGNORECASE)
    if obs_m: obs = obs_m.group(0).strip().capitalize()

    return direccion, ciudad, barrio, obs

def parse_exp_tiempo_relativa(texto: str, now: Optional[datetime] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Convierte expresiones como:
      - "mañana antes de las 3 pm"
      - "hoy entre 2 y 4 pm"
      - "pasado mañana a las 10am"
    Retorna (inicio_iso, fin_iso, expresion_detectada)
    """
    if now is None:
        now = datetime.now(TZ)

    low = texto.lower()

    # Detecta el día base
    if "pasado mañana" in low:
        base = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif "mañana" in low:
        base = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif "hoy" in low:
        base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        base = None

    # Rangos "antes de las X"
    m_antes = re.search(r"antes de las\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
    if base and m_antes:
        hh = int(m_antes.group(1))
        mm = int(m_antes.group(2) or 0)
        ampm = (m_antes.group(3) or "").lower()
        if ampm == "pm" and hh < 12: hh += 12
        fin = base.replace(hour=hh, minute=mm)
        return base.isoformat(), fin.isoformat(), m_antes.group(0)

    # Rangos "entre X y Y"
    m_entre = re.search(r"entre\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+y\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
    if base and m_entre:
        h1 = int(m_entre.group(1)); m1 = int(m_entre.group(2) or 0); ap1 = (m_entre.group(3) or "").lower()
        h2 = int(m_entre.group(4)); m2 = int(m_entre.group(5) or 0); ap2 = (m_entre.group(6) or "").lower()
        if ap1 == "pm" and h1 < 12: h1 += 12
        if ap2 == "pm" and h2 < 12: h2 += 12
        ini = base.replace(hour=h1, minute=m1)
        fin = base.replace(hour=h2, minute=m2)
        return ini.isoformat(), fin.isoformat(), m_entre.group(0)

    # Puntos "a las X"
    m_a = re.search(r"a las\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
    if base and m_a:
        h = int(m_a.group(1)); m = int(m_a.group(2) or 0); ap = (m_a.group(3) or "").lower()
        if ap == "pm" and h < 12: h += 12
        ini = base.replace(hour=h, minute=m)
        fin = ini + timedelta(minutes=90)  # ventana de 90 min por defecto si no hay rango
        return ini.isoformat(), fin.isoformat(), m_a.group(0)

    # Si solo dice "mañana" sin hora, asumimos 00:00 a 15:00 como en tu ejemplo
    if base and "mañana" in low:
        return base.isoformat(), base.replace(hour=15).isoformat(), "mañana"

    return None, None, None

def postproceso_modelo(interpretacion: Dict[str, Any], texto_libre: str) -> Dict[str, Any]:
    # Telef/Email locales (si el modelo no los puso)
    tel = interpretacion["detalles"]["cliente"].get("telefono")
    if not tel:
        interpretacion["detalles"]["cliente"]["telefono"] = extraer_telefono(texto_libre)

    email = interpretacion["detalles"]["cliente"].get("email")
    if not email:
        interpretacion["detalles"]["cliente"]["email"] = extraer_email(texto_libre)

    # Dirección/ciudad/barrio/obs (si faltan)
    dir_info = interpretacion["detalles"].get("direccion_entrega", {}) or {}
    d_txt, ciudad, barrio, obs = extraer_direccion_y_ciudad(texto_libre)
    if not dir_info.get("texto"): dir_info["texto"] = d_txt
    if not dir_info.get("ciudad"): dir_info["ciudad"] = ciudad
    if not dir_info.get("barrio"): dir_info["barrio"] = barrio
    if not dir_info.get("observaciones_entrega") and obs:
        dir_info["observaciones_entrega"] = obs
    if "nivel_confianza" not in dir_info or dir_info["nivel_confianza"] is None:
        dir_info["nivel_confianza"] = 0.80 if d_txt else 0.40
    dir_info["lat"] = None
    dir_info["lng"] = None
    interpretacion["detalles"]["direccion_entrega"] = dir_info

    # Ventana de entrega desde expresiones relativas si vienen en el texto original
    v = interpretacion["detalles"].get("ventana_entrega", {}) or {}
    if not v.get("inicio_iso") or not v.get("fin_iso"):
        ini, fin, expr = parse_exp_tiempo_relativa(texto_libre)
        v["inicio_iso"] = ini
        v["fin_iso"] = fin
        if expr and not v.get("expresion_detectada"):
            v["expresion_detectada"] = expr
        if "nivel_confianza" not in v or v["nivel_confianza"] is None:
            v["nivel_confianza"] = 0.85 if (ini and fin) else 0.5
        interpretacion["detalles"]["ventana_entrega"] = v

    # Items: normaliza nombres y completa unidad si falta
    items = interpretacion["detalles"].get("items", []) or []
    for it in items:
        it["nombre_normalizado"] = normalizar_item_nombre(it.get("nombre_detectado") or it.get("nombre_normalizado"))
        if not it.get("unidad"):
            it["unidad"] = "unidad"
        it["sku"] = None
        it["peso_kg"] = it.get("peso_kg", None)
        it["volumen_m3"] = it.get("volumen_m3", None)
        if "nivel_confianza" not in it or it["nivel_confianza"] is None:
            it["nivel_confianza"] = 0.80

    interpretacion["detalles"]["items"] = items

    # Restricciones
    restr = interpretacion["detalles"].get("restricciones", {}) or {}
    restr["manejo_fragil"] = detectar_manejo_fragil(texto_libre)
    restr["temperatura_controlada"] = detectar_temp_controlada(texto_libre)
    restr["acceso_restringido"] = detectar_acceso_restringido(texto_libre)
    if "notas" not in restr or restr["notas"] is None:
        restr["notas"] = []
    if restr["manejo_fragil"]:
        if "Empacar frágil" not in restr["notas"]:
            restr["notas"].append("Empacar frágil")
    interpretacion["detalles"]["restricciones"] = restr

    # Validaciones
    val = interpretacion.get("validaciones", {}) or {}
    campos = val.get("campos_obligatorios", {}) or {}
    campos["direccion_entrega"] = bool(interpretacion["detalles"]["direccion_entrega"].get("texto"))
    campos["ventana_entrega"] = bool(interpretacion["detalles"]["ventana_entrega"].get("inicio_iso")) and bool(interpretacion["detalles"]["ventana_entrega"].get("fin_iso"))
    campos["items"] = len(interpretacion["detalles"]["items"]) > 0
    val["campos_obligatorios"] = campos

    advertencias: List[str] = val.get("advertencias", []) or []
    advertencias.append("No se detectó SKU para los items; se requiere mapeo en la fase de coordinación.")
    if not interpretacion["detalles"]["direccion_entrega"].get("lat") or not interpretacion["detalles"]["direccion_entrega"].get("lng"):
        advertencias.append("No hay coordenadas (lat/lng); se recomienda geocodificación en la fase de coordinación.")
    val["advertencias"] = list(dict.fromkeys(advertencias))  # quita duplicados
    val["ambiguedades"] = val.get("ambiguedades", []) or []
    interpretacion["validaciones"] = val

    return interpretacion

def armar_respuesta_final(
    texto_libre: str,
    canal: str,
    interpretacion: Dict[str, Any],
    nivel_confianza: float = 0.92
) -> Dict[str, Any]:
    now = datetime.now(TZ)
    return {
        "pedido_id": generar_pedido_id(),
        "solicitud_cliente": "Recibir e interpretar el pedido",
        "entrada_original": {
            "canal": canal,
            "timestamp_iso": now.isoformat(),
            "texto_libre": texto_libre
        },
        "interpretacion_IA": interpretacion,
        "paso_siguiente_sugerido": {
            "accion": "planificacion_entrega",
            "inputs_requeridos": [
                "Geocodificar direccion_entrega",
                "Mapear items a SKU y validar stock",
                "Asignar ventana exacta según capacidad de ruta"
            ]
        },
        "nivel_confianza": nivel_confianza,
        "metadatos": {
            "version_agente": "interprete-1.0.0",
            "uuid_operacion": generar_uuid_operacion()
        }
    }
