// ─── Style palettes per map layer ────────────────────────────────────────────
const STYLES = {
  dark: {
    fire:         { high: "#F46F25", medium: "#E98A3A", low: "#F0EBE4" },
    municipality: { color: "#cccccc", weight: 1.2, fillColor: "#ffffff", fillOpacity: 0.05 },
    uc:           { color: "#52b788", weight: 2.0, fillColor: "#52b788", fillOpacity: 0.12 },
  },
  satellite: {
    fire:         { high: "#F46F25", medium: "#E98A3A", low: "#F0EBE4" },
    municipality: { color: "#ffffff", weight: 1.5, fillColor: "#ffffff", fillOpacity: 0.06 },
    uc:           { color: "#39d353", weight: 2.0, fillColor: "#39d353", fillOpacity: 0.18 },
  },
};

// ─── Fire intensity helpers ───────────────────────────────────────────────────
function frpTier(frp) {
  if (frp > 100) return "high";
  if (frp > 30)  return "medium";
  return "low";
}

function frpColor(frp) {
  const palette = STYLES[activeLayer]?.fire || STYLES.dark.fire;
  if (frp > 100) return palette.high;
  if (frp > 30)  return palette.medium;
  return palette.low;
}

function frpLabel(frp) {
  if (frp > 100) return "Alta";
  if (frp > 30)  return "Moderada";
  return "Baixa";
}

function confidenceLabel(c) {
  return c === "h" ? "Alta (~95%)" : c === "n" ? "Nominal (~75%)" : "Baixa (~35%)";
}

function formattedDetectionTime(raw) {
  const time = String(raw ?? "").padStart(4, "0");
  return `${time.slice(0, 2)}h${time.slice(2)} UTC (${time.slice(0, 2)}:${time.slice(2)} no horário universal)`;
}

function fireMarkerSize(level) {
  const sizes = {
    high: 22,
    medium: 17,
    low: 12,
  };
  return sizes[level] || sizes.low;
}

function createFireIcon(level) {
  const size = fireMarkerSize(level);

  return L.divIcon({
    className: "fire-div-icon",
    html: `<span class="fire-marker fire-marker--${level}"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2)],
  });
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
};

tileLayers.dark.addTo(map);

let activeLayer = "dark";
let currentFires = [];

document.querySelectorAll(".layer-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    if (btn.dataset.layer === activeLayer) return;
    document.querySelectorAll(".layer-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    tileLayers[activeLayer].remove();
    activeLayer = btn.dataset.layer;
    tileLayers[activeLayer].addTo(map);

    // Re-apply polygon styles for new mode
    const s = STYLES[activeLayer];
    if (municipalityLayer) municipalityLayer.setStyle(s.municipality);
    if (ucLayer)           ucLayer.setStyle(s.uc);

    // Re-render fire markers with new palette
    if (currentFires.length > 0) renderFires(currentFires);
  });
});

// ─── Polygon layers ───────────────────────────────────────────────────────────
let municipalityLayer = null;
let ucLayer = null;

function clearPolygonLayers() {
  if (municipalityLayer) { map.removeLayer(municipalityLayer); municipalityLayer = null; }
  if (ucLayer)           { map.removeLayer(ucLayer);           ucLayer = null; }
}

async function loadPolygonLayers(unitId) {
  clearPolygonLayers();
  if (!unitId) return;

  try {
    const [munData, ucData] = await Promise.all([
      fetch(`/api/geojson/unit/${encodeURIComponent(unitId)}`).then(r => r.json()),
      fetch(`/api/geojson/ucs/${encodeURIComponent(unitId)}`).then(r => r.json()),
    ]);

    if (munData.features && munData.features.length > 0) {
      municipalityLayer = L.geoJSON(munData, {
        style: {
          color: "#F48030",
          weight: 1.5,
          fill: true,
          fillColor: "#F48030",
          fillOpacity: 0.08,
        },
        onEachFeature: (feature, layer) => {
          const name = feature.properties?.sv_nome || feature.properties?.NM_MUN || "";
          if (name) layer.bindTooltip(`Município: ${name}`, { sticky: true });
        },
      }).addTo(map);

      map.fitBounds(municipalityLayer.getBounds(), { padding: [20, 20] });
    }

    if (ucData.features && ucData.features.length > 0) {
      ucLayer = L.geoJSON(ucData, {
        style: {
          color: "#27ae60",
          weight: 2,
          fill: true,
          fillColor: "#27ae60",
          fillOpacity: 0.18,
        },
        onEachFeature: (feature, layer) => {
          const name = feature.properties?.sv_nome || feature.properties?.nome_uc || "";
          if (name) layer.bindTooltip(`UC: ${name}`, { sticky: true });
        },
      }).addTo(map);
    }
  } catch (e) {
    console.error("Erro ao carregar polígonos:", e);
  }
}

// ─── Marker management ────────────────────────────────────────────────────────
const markerLayer = L.layerGroup().addTo(map);

function buildMarker(event) {
  const frp    = event.frp ?? 0;
  const tier   = frpTier(frp);
  const color  = frpColor(frp);

  const marker = L.marker([event.latitude, event.longitude], {
    icon: createFireIcon(tier),
  });

  marker.bindPopup(`
    <div class="popup-inner">
      <div class="popup-header" style="border-left:3px solid ${color}">
        <span class="popup-tier">Intensidade ${frpLabel(frp)}</span>
      </div>
      <table class="popup-table">
        <tr><td>Data da detecção</td><td>${event.acq_date ?? "—"}<br><small>Dia em que o satélite identificou este foco.</small></td></tr>
        <tr><td>Horário da detecção</td><td>${formattedDetectionTime(event.acq_time)}<br><small>Horário universal; em Brasília, subtraia 3 horas.</small></td></tr>
        <tr><td>Potência Radiativa do Fogo (FRP)</td><td><strong>${frp} MW</strong><br><small>Estimativa da energia/calor emitido pelo fogo no momento da passagem do satélite.</small></td></tr>
        <tr><td>Satélite/sensor</td><td>${event.satellite ?? "—"}<br><small>Plataforma que detectou o foco.</small></td></tr>
        <tr><td>Confiança da detecção</td><td>${confidenceLabel(event.confidence)}</td></tr>
        <tr><td>Lat / Lon</td><td>${Number(event.latitude).toFixed(3)}, ${Number(event.longitude).toFixed(3)}</td></tr>
      </table>
      <div style="margin-top:8px;font-size:11px;color:#777;line-height:1.35">
        FRP = Fire Radiative Power, ou Potência Radiativa do Fogo. Valores maiores indicam maior energia emitida pelo foco.
      </div>
    </div>
  `, { maxWidth: 420 });

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

// ─── Cascading dropdowns ──────────────────────────────────────────────────────
const cobSelect      = document.getElementById("cob-select");
const battalionSelect = document.getElementById("battalion-select");
const companySelect  = document.getElementById("company-select");
const fractionSelect = document.getElementById("fraction-select");

let operationalUnits = [];

function selectedUnitId() {
  return fractionSelect.value || companySelect.value || battalionSelect.value || cobSelect.value || null;
}

function childrenOf(parentId, types) {
  return operationalUnits.filter(u => u.parent_id === parentId && types.includes(u.type));
}

function resetSelect(select, placeholder) {
  select.innerHTML = "";
  const opt = document.createElement("option");
  opt.value = "";
  opt.textContent = placeholder;
  select.appendChild(opt);
  select.disabled = true;
}

function populateSelect(select, units, placeholder) {
  resetSelect(select, placeholder);
  units.forEach(u => {
    const opt = document.createElement("option");
    opt.value = u.id;
    opt.textContent = u.name;
    select.appendChild(opt);
  });
  select.disabled = units.length === 0;
}

function populateBattalions() {
  const battalions = childrenOf(cobSelect.value || null, ["batalhao"]);
  populateSelect(battalionSelect, battalions, "Todos os batalhões");
  populateSelect(companySelect,  [], "Todas as companhias");
  populateSelect(fractionSelect, [], "Todos os pelotões e postos");
}

function populateCompanies() {
  const companies = childrenOf(battalionSelect.value, ["companhia"]);
  populateSelect(companySelect,  companies, "Todas as companhias");
  populateSelect(fractionSelect, [], "Todos os pelotões e postos");
}

function populateFractions() {
  const parentId  = companySelect.value || battalionSelect.value;
  const fractions = childrenOf(parentId, ["pelotao", "posto"]);
  populateSelect(fractionSelect, fractions, "Todos os pelotões e postos");
}

// ─── Status + fire fetch ──────────────────────────────────────────────────────
const lastUpdatedEl = document.getElementById("last-updated");
const totalEventsEl = document.getElementById("total-events");

async function updateStatus() {
  try {
    const unit = selectedUnitId();
    const url  = unit ? `/api/status?unit=${encodeURIComponent(unit)}` : "/api/status";
    const data = await fetch(url).then(r => r.json());
    lastUpdatedEl.textContent = data.last_fetch_at || "Nunca";
    totalEventsEl.textContent = data.total_events ?? 0;
  } catch (e) {
    console.error("Erro ao buscar status:", e);
  }
}

async function applyFilters() {
  try {
    const unit = selectedUnitId();
    const firesUrl = unit ? `/api/fires?unit=${encodeURIComponent(unit)}` : "/api/fires";
    const [fires] = await Promise.all([
      fetch(firesUrl).then(r => r.json()),
      loadPolygonLayers(unit),
    ]);
    currentFires = fires;
    renderFires(fires);
    await updateStatus();
  } catch (e) {
    console.error("Erro ao carregar focos:", e);
    showToast("Erro ao carregar focos de incêndio.", "error");
  }
}

// ─── Refresh button ───────────────────────────────────────────────────────────
const refreshBtn  = document.getElementById("refresh-btn");
const refreshIcon = document.getElementById("refresh-icon");

refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  refreshIcon.classList.add("spinning");
  try {
    const res = await fetch("/api/fetch", { method: "POST" });
    if (!res.ok) throw new Error("fetch failed");
    await applyFilters();
  } catch {
    showToast("Falha ao buscar novos dados.", "error");
  } finally {
    refreshBtn.disabled = false;
    refreshIcon.classList.remove("spinning");
  }
});

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.className = `toast toast-${type} show`;
  setTimeout(() => toast.classList.remove("show"), 3500);
}

// ─── Event listeners ──────────────────────────────────────────────────────────
cobSelect.addEventListener("change", () => {
  populateBattalions();
  applyFilters();
});
battalionSelect.addEventListener("change", () => {
  populateCompanies();
  populateFractions();
  applyFilters();
});
companySelect.addEventListener("change", () => {
  populateFractions();
  applyFilters();
});
fractionSelect.addEventListener("change", () => {
  applyFilters();
});

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    operationalUnits = await fetch("/api/operational-units").then(r => r.json());
    const cobs = operationalUnits.filter(u => u.type === "cob");
    populateSelect(cobSelect, cobs, "Todo o estado de Minas Gerais");
    if (cobs.length > 0) {
      cobSelect.value = cobs[0].id;
      populateBattalions();
    }
  } catch (e) {
    console.error("Erro ao carregar unidades operacionais:", e);
  }

  await applyFilters();
  setInterval(updateStatus, 5 * 60 * 1000);
}

boot();
