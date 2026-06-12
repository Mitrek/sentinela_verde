// ─── Config ──────────────────────────────────────────────────────────────────
const USE_MOCK = true; // Altere para false ao conectar ao backend real

// ─── API helpers (falls back to mock data when USE_MOCK is true) ──────────────
async function apiFetch(path) {
  if (!USE_MOCK) return fetch(path).then(r => r.json());
  if (path === "/api/status") return MOCK.status;
  if (path === "/api/areas")  return MOCK.areas;
  if (path === "/api/ucs")    return MOCK.ucs;
  if (path === "/api/fires")  return MOCK.fires;
  return null;
}

async function apiPost(path) {
  if (!USE_MOCK) return fetch(path, { method: "POST" });
  await new Promise(r => setTimeout(r, 1200)); // simula atraso
  MOCK.status.last_fetch_at = new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC";
  return { ok: true };
}

// ─── Fire intensity helpers ───────────────────────────────────────────────────
function frpTier(frp) {
  if (frp > 100) return "high";
  if (frp > 30)  return "mid";
  return "low";
}

function frpColor(frp) {
  if (frp > 100) return "#F48030";
  if (frp > 30)  return "#F68C29";
  return "#F0EBE4";
}

function frpLabel(frp) {
  if (frp > 100) return "Alta";
  if (frp > 30)  return "Moderada";
  return "Baixa";
}

function confidenceLabel(c) {
  return c === "h" ? "Alta" : "Nominal";
}

// ─── Map setup ────────────────────────────────────────────────────────────────
const map = L.map("map", {
  center: [-18.5, -44.5],
  zoom: 6,
  zoomControl: false,
});

L.control.zoom({ position: "bottomright" }).addTo(map);

const tileLayers = {
  dark: L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    { attribution: "© OpenStreetMap, © CARTO", maxZoom: 19 }
  ),
  satellite: L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "© Esri", maxZoom: 19 }
  ),
  terrain: L.tileLayer(
    "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    { attribution: "© OpenTopoMap", maxZoom: 17 }
  ),
};

tileLayers.dark.addTo(map);

let activeLayer = "dark";
document.querySelectorAll(".layer-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".layer-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    tileLayers[activeLayer].remove();
    activeLayer = btn.dataset.layer;
    tileLayers[activeLayer].addTo(map);
  });
});

// ─── Marker management ────────────────────────────────────────────────────────
let markerLayer = L.layerGroup().addTo(map);
let allFires = [];

function buildMarker(event) {
  const frp   = event.frp ?? 0;
  const color = frpColor(frp);
  const tier  = frpTier(frp);
  const radius = tier === "high" ? 10 : tier === "mid" ? 7 : 5;

  const marker = L.circleMarker([event.latitude, event.longitude], {
    radius,
    color,
    fillColor: color,
    fillOpacity: 0.85,
    weight: 1.5,
    className: `fire-marker fire-${tier}`,
  });

  marker.bindPopup(`
    <div class="popup-inner">
      <div class="popup-header" style="border-left: 3px solid ${color}">
        <span class="popup-tier">Intensidade ${frpLabel(frp)}</span>
      </div>
      <table class="popup-table">
        <tr><td>FRP</td><td><strong>${frp} MW</strong></td></tr>
        <tr><td>Data</td><td>${event.acq_date}</td></tr>
        <tr><td>Hora</td><td>${event.acq_time} UTC</td></tr>
        <tr><td>Satélite</td><td>${event.satellite}</td></tr>
        <tr><td>Confiança</td><td>${confidenceLabel(event.confidence)}</td></tr>
        <tr><td>Lat / Lon</td><td>${event.latitude.toFixed(3)}, ${event.longitude.toFixed(3)}</td></tr>
      </table>
    </div>
  `, { maxWidth: 260, className: "fire-popup" });

  return marker;
}

function renderFires(fires) {
  markerLayer.clearLayers();
  fires.forEach(f => buildMarker(f).addTo(markerLayer));
  updateStats(fires);
}

// ─── Stats panel ─────────────────────────────────────────────────────────────
function updateStats(fires) {
  const high = fires.filter(f => (f.frp ?? 0) > 100).length;
  const mid  = fires.filter(f => (f.frp ?? 0) > 30 && (f.frp ?? 0) <= 100).length;
  const low  = fires.filter(f => (f.frp ?? 0) <= 30).length;
  document.getElementById("stat-total").textContent = fires.length;
  document.getElementById("stat-high").textContent  = high;
  document.getElementById("stat-mid").textContent   = mid;
  document.getElementById("stat-low").textContent   = low;
}

// ─── Filters ──────────────────────────────────────────────────────────────────
const areaSelect = document.getElementById("area-select");

function applyFilters() {
  // No modo real, o backend filtra; no mock, mantemos todos os focos.
  renderFires(allFires);
}

areaSelect.addEventListener("change", () => {
  applyFilters();
});

// ─── Refresh ─────────────────────────────────────────────────────────────────
const refreshBtn   = document.getElementById("refresh-btn");
const refreshIcon  = document.getElementById("refresh-icon");
const lastUpdated  = document.getElementById("last-updated");

refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  refreshIcon.classList.add("spinning");
  try {
    await apiPost("/api/fetch");
    const status = await apiFetch("/api/status");
    lastUpdated.textContent = status.last_fetch_at;
  } catch {
    showToast("Falha ao buscar novos dados.", "error");
  } finally {
    refreshBtn.disabled = false;
    refreshIcon.classList.remove("spinning");
  }
});

// ─── Toast notifications ─────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.className = `toast toast-${type} show`;
  setTimeout(() => toast.classList.remove("show"), 3500);
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function boot() {
  // Status
  const status = await apiFetch("/api/status");
  lastUpdated.textContent = status.last_fetch_at;
  document.getElementById("total-events").textContent = status.total_events;

  // Seletor de áreas
  const areas = await apiFetch("/api/areas");
  areas.forEach(a => {
    const opt = document.createElement("option");
    opt.value = a.id;
    opt.textContent = `${a.name} (${a.region})`;
    areaSelect.appendChild(opt);
  });

  // Focos
  allFires = await apiFetch("/api/fires");
  renderFires(allFires);

  // Atualiza o status a cada 5 min
  setInterval(async () => {
    const s = await apiFetch("/api/status");
    lastUpdated.textContent = s.last_fetch_at;
  }, 5 * 60 * 1000);
}

boot();
