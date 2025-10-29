// ====== Config auto para el backend ======
const API_BASE =
  location.protocol === "file:" || location.hostname === ""
    ? "http://127.0.0.1:8000"
    : window.location.origin;

// ====== UI refs ======
const ejemplo = `Hola, para mañana antes de las 3 pm necesito 250 buñuelos y 100 arepas de maíz para la tienda en Chapinero: Cra 7 #60-15, piso 2. Entregar en recepción. Por favor, empacar frágil. Tel 3201234567.`;
const $texto = document.getElementById("texto");
const $usarModelo = document.getElementById("usar_modelo");
const $btnEjemplo = document.getElementById("btnEjemplo");
const $btnEnviar = document.getElementById("btnEnviar");
const $btnLimpiar = document.getElementById("btnLimpiar");
const $btnCopy = document.getElementById("btnCopy");
const $btnClearRaw = document.getElementById("btnClearRaw");
const $btnClearClean = document.getElementById("btnClearClean");
const $salida = document.getElementById("salida");
const $vista = document.getElementById("vistaLimpia");
const $status = document.getElementById("status");
const $charCount = document.getElementById("charCount");

// --- Dropdown ---
const dropdown = document.getElementById("dropdownCanal");
const selected = document.getElementById("selectedCanal");
const menu = document.getElementById("menuCanal");

const CHANNEL_ICON = {
  formulario_web: "globe",
  whatsapp: "message-circle",
  email: "mail",
  telefono: "phone",
  otro: "more-horizontal",
};
const CHANNEL_COLOR = {
  formulario_web: "#C97A40",
  whatsapp: "#22C55E",
  email: "#3B82F6",
  telefono: "#8B5CF6",
  otro: "#6B7280",
};

// Renderiza todos los [data-lucide] iniciales
if (window.lucide) {
  lucide.createIcons();
}

// --- helpers dropdown ---
function renderSelected(value, label) {
  const icon = CHANNEL_ICON[value] || CHANNEL_ICON.otro;
  const color = CHANNEL_COLOR[value] || CHANNEL_COLOR.otro;

  // Reemplazamos TODO el contenido visible del seleccionado
  selected.innerHTML = `
    <span class="icon" data-lucide="${icon}"></span>
    <span class="label">${label}</span>
    <span class="arrow">▾</span>
  `;
  selected.dataset.value = value;

  // Re-render de Lucide para ese icono
  if (window.lucide) {
    lucide.createIcons();
    // colorear stroke del svg recién creado
    const svg = selected.querySelector("svg[data-lucide]");
    if (svg) svg.style.stroke = color;
  }
}

function getCanalSeleccionado() {
  return selected.dataset.value;
}

// abrir/cerrar: solo sobre el “selected”
selected.addEventListener("click", (e) => {
  e.stopPropagation();
  dropdown.classList.toggle("open");
});

// seleccionar opción
menu.querySelectorAll(".dropdown-item").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.stopPropagation();
    const value = item.getAttribute("data-value");
    const label = item.textContent.trim();
    renderSelected(value, label);
    dropdown.classList.remove("open");
  });
});

// cerrar al click fuera y con Esc
document.addEventListener("click", (e) => {
  if (!dropdown.contains(e.target)) dropdown.classList.remove("open");
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") dropdown.classList.remove("open");
});

// ====== utils ======
const setStatus = (msg, type = "") => {
  $status.className = "status " + (type || "");
  $status.textContent = msg || "";
};
const setLoading = (loading) => {
  $btnEnviar.disabled = loading;
  $btnEnviar.textContent = loading ? "Procesando…" : "Interpretar";
};
const pretty = (o) => JSON.stringify(o, null, 2);
const safe = (v) => (v === null || v === undefined || v === "" ? "—" : v);

// contador caracteres
const updateCharCount = () =>
  ($charCount.textContent = ($texto.value || "").length);
$texto.addEventListener("input", updateCharCount);
updateCharCount();

// ejemplo
$btnEjemplo.onclick = () => {
  $texto.value = ejemplo;
  updateCharCount();
};

// limpiar entrada + salidas
const clearRaw = () => {
  $salida.textContent = "{}";
};
const clearClean = () => {
  $vista.innerHTML = '<span class="muted">Sin datos aún.</span>';
};
$btnLimpiar.onclick = () => {
  $texto.value = "";
  updateCharCount();
  setStatus("");
  clearRaw();
  clearClean();
  $texto.focus();
};
$btnClearRaw.onclick = clearRaw;
$btnClearClean.onclick = clearClean;

// copiar JSON
$btnCopy.onclick = async () => {
  try {
    await navigator.clipboard.writeText($salida.textContent || "{}");
    setStatus("JSON copiado", "ok");
    setTimeout(() => setStatus(""), 1200);
  } catch {
    setStatus("No se pudo copiar", "err");
  }
};

// ====== Vista limpia ======
function renderVistaLimpia(data) {
  try {
    const i = data.interpretacion_IA || {};
    const d = i.detalles || {};
    const cli = d.cliente || {};
    const dir = d.direccion_entrega || {};
    const ven = d.ventana_entrega || {};
    const items = Array.isArray(d.items) ? d.items : [];
    const restr = d.restricciones || {};
    const val = i.validaciones || {};
    const campos = val.campos_obligatorios || {};
    const paso = data.paso_siguiente_sugerido || {};

    const itemsRows =
      items
        .map(
          (it) => `
        <tr>
          <td>${safe(it.nombre_detectado)}</td>
          <td>${safe(it.nombre_normalizado)}</td>
          <td>${safe(it.cantidad)}</td>
          <td>${safe(it.unidad)}</td>
          <td>${safe(it.nivel_confianza)}</td>
        </tr>`
        )
        .join("") || `<tr><td colspan="5" class="muted">Sin items</td></tr>`;

    const advs =
      (val.advertencias || []).map((a) => `<li>${a}</li>`).join("") ||
      '<li class="muted">—</li>';
    const ambs =
      (val.ambiguedades || []).map((a) => `<li>${a}</li>`).join("") ||
      '<li class="muted">—</li>';
    const notas =
      (restr.notas || []).map((n) => `<li>${n}</li>`).join("") ||
      '<li class="muted">—</li>';
    const inputsReq =
      (paso.inputs_requeridos || []).map((n) => `<li>${n}</li>`).join("") ||
      '<li class="muted">—</li>';

    $vista.innerHTML = `
      <div class="kv">
        <div>Pedido ID</div><div>${safe(data.pedido_id)}</div>
        <div>Solicitud</div><div>${safe(data.solicitud_cliente)}</div>
        <div>Canal</div><div>${safe(data.entrada_original?.canal)}</div>
        <div>Timestamp</div><div>${safe(
          data.entrada_original?.timestamp_iso
        )}</div>
        <div>Texto original</div><div>${safe(
          data.entrada_original?.texto_libre
        )}</div>
      </div>

      <div class="section-title">Cliente</div>
      <div class="kv">
        <div>Nombre</div><div>${safe(cli.nombre)}</div>
        <div>Teléfono</div><div>${safe(cli.telefono)}</div>
        <div>Email</div><div>${safe(cli.email)}</div>
      </div>

      <div class="section-title">Entrega</div>
      <div class="kv">
        <div>Dirección</div><div>${safe(dir.texto)}</div>
        <div>Ciudad / Barrio</div><div>${safe(dir.ciudad)} / ${safe(
      dir.barrio
    )}</div>
        <div>Obs. entrega</div><div>${safe(dir.observaciones_entrega)}</div>
        <div>Ventana</div><div>${safe(ven.inicio_iso)} → ${safe(
      ven.fin_iso
    )} (${safe(ven.expresion_detectada)})</div>
      </div>

      <div class="section-title">Items</div>
      <table>
        <thead><tr><th>Detectado</th><th>Normalizado</th><th>Cant.</th><th>Unidad</th><th>Conf.</th></tr></thead>
        <tbody>${itemsRows}</tbody>
      </table>

      <div class="section-title">Restricciones</div>
      <div class="kv">
        <div>Manejo frágil</div><div>${restr.manejo_fragil ? "Sí" : "No"}</div>
        <div>Temp. controlada</div><div>${
          restr.temperatura_controlada ? "Sí" : "No"
        }</div>
        <div>Acceso restringido</div><div>${
          restr.acceso_restringido ? "Sí" : "No"
        }</div>
        <div>Notas</div><div><ul style="margin:0 0 0 18px">${notas}</ul></div>
      </div>

      <div class="section-title">Validaciones</div>
      <div class="kv">
        <div>Campos obligatorios</div>
        <div>dirección: ${
          campos.direccion_entrega ? "OK" : "Falta"
        } · ventana: ${campos.ventana_entrega ? "OK" : "Falta"} · items: ${
      campos.items ? "OK" : "Falta"
    }</div>
        <div>Advertencias</div><div><ul style="margin:0 0 0 18px">${advs}</ul></div>
        <div>Ambigüedades</div><div><ul style="margin:0 0 0 18px">${ambs}</ul></div>
      </div>

      <div class="section-title">Siguiente paso sugerido</div>
      <div class="kv">
        <div>Acción</div><div>${safe(paso.accion)}</div>
        <div>Inputs requeridos</div><div><ul style="margin:0 0 0 18px">${inputsReq}</ul></div>
      </div>
    `;
  } catch (e) {
    $vista.innerHTML = `<span class="muted">No se pudo renderizar la vista limpia: ${e.message}</span>`;
  }
}

// --- Enhancer: toggle clickeable en todo el control
(function setupIASwitch() {
  const wrap = document.getElementById("switchIA");
  const input = document.getElementById("usar_modelo");
  const sw = wrap.querySelector(".switch");
  const label = wrap.querySelector(".switch-label");

  // Clic en el wrap → alterna el checkbox (evita doble toggle al click directo en input)
  wrap.addEventListener("click", (e) => {
    // Si el click fue exactamente sobre el input, dejamos que el navegador lo maneje
    if (e.target === input) return;
    input.checked = !input.checked;
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  // Opcional: feedback visual o log
  input.addEventListener("change", () => {
    // console.log("Usar IA:", input.checked);
  });
})();

// ====== Enviar ======
$btnEnviar.onclick = async () => {
  const texto = ($texto.value || "").trim();
  const canal = getCanalSeleccionado();
  const usar_modelo = $usarModelo.checked;

  if (!texto) {
    alert("Escribe un texto");
    $texto.focus();
    return;
  }

  setLoading(true);
  setStatus("Procesando…");
  $salida.textContent = "Procesando…";
  $vista.innerHTML = '<span class="muted">Procesando…</span>';

  try {
    const resp = await fetch(`${API_BASE}/interpretar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto_libre: texto, canal, usar_modelo }),
    });
    if (!resp.ok) {
      const t = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${t}`);
    }

    const data = await resp.json();
    $salida.textContent = pretty(data);
    renderVistaLimpia(data);
    setStatus("Listo", "ok");
  } catch (err) {
    setStatus("Error: " + err.message, "err");
    clearRaw();
    clearClean();
  } finally {
    setLoading(false);
  }
};

// ====== Atajos ======
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") $btnEnviar.click();
  if (e.key === "Escape") {
    clearRaw();
    clearClean();
  }
});

// ====== Init (sincroniza UI con valor inicial del HTML) ======
(function initDropdown() {
  // Asegúrate de que en tu HTML el seleccionado tenga data-value inicial, ej:
  // <div id="selectedCanal" data-value="formulario_web">...</div>
  const initValue = selected.dataset.value || "formulario_web";
  const initLabel = (
    menu.querySelector(`.dropdown-item[data-value="${initValue}"]`)
      ?.textContent || "formulario_web"
  ).trim();
  renderSelected(initValue, initLabel);
})();
