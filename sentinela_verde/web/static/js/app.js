// ─── Style palettes per map layer ────────────────────────────────────────────
const STYLES = {
  dark: {
    fire:         { high: "#F46F25", medium: "#E98A3A", low: "#F0EBE4" },
    context:      { color: "#8f969b", weight: 0.7, fill: true, fillColor: "#8f969b", fillOpacity: 0.05, opacity: 0.45 },
    municipality: { color: "#cccccc", weight: 1.2, fill: true, fillColor: "#ffffff", fillOpacity: 0.05 },
    uc:           { color: "#52b788", weight: 2.0, fill: true, fillColor: "#52b788", fillOpacity: 0.12 },
  },
  satellite: {
    fire:         { high: "#F46F25", medium: "#E98A3A", low: "#F0EBE4" },
    context:      { color: "#b6bdc2", weight: 0.8, fill: true, fillColor: "#b6bdc2", fillOpacity: 0.04, opacity: 0.5 },
    municipality: { color: "#ffffff", weight: 1.5, fill: true, fillColor: "#ffffff", fillOpacity: 0.06 },
    uc:           { color: "#39d353", weight: 2.0, fill: true, fillColor: "#39d353", fillOpacity: 0.18 },
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

const SATELLITE_LABELS = {
  "Terra":   "Terra (MODIS)",
  "Aqua":    "Aqua (MODIS)",
  "N":       "NOAA-20 / VIIRS",
  "N-20":    "NOAA-20 / VIIRS",
  "NOAA-20": "NOAA-20 / VIIRS",
  "S":       "Suomi NPP / VIIRS",
  "NPP":     "Suomi NPP / VIIRS",
  "INPE":    "INPE Queimadas",
};

function satelliteLabel(sat) {
  return SATELLITE_LABELS[sat] || sat || "—";
}

function detectionSourceLabel(event) {
  if (event?.satellite === "Teste") return "Teste (Simulado)";
  return event?.satellite === "INPE" ? "INPE Queimadas" : "NASA FIRMS";
}

function formattedDetectionTime(raw) {
  const time = String(raw ?? "").padStart(4, "0");
  const hour = Number(time.slice(0, 2));
  const minute = time.slice(2);

  if (Number.isNaN(hour) || minute.length !== 2) {
    return "Não informado";
  }

  const brasiliaHour = (hour + 21) % 24;
  return `${String(brasiliaHour).padStart(2, "0")}:${minute} (horário de Brasília)`;
}

function formattedLastUpdate(raw) {
  if (!raw) return "Nunca";

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return "Nunca";

  const weekday = new Intl.DateTimeFormat("pt-BR", { weekday: "long" }).format(date);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");

  return `${hour}h${minute}min em ${weekday}, ${day}/${month}/${year}`;
}

function acquisitionKey(event) {
  const date = event?.acq_date || "";
  const time = String(event?.acq_time ?? "").padStart(4, "0");
  return `${date}T${time}`;
}

function currentUtcAcquisitionKey() {
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const time = `${String(now.getUTCHours()).padStart(2, "0")}${String(now.getUTCMinutes()).padStart(2, "0")}`;
  return `${date}T${time}`;
}

function maxAcquisitionKey(fires) {
  const keys = fires
    .map(acquisitionKey)
    .filter(key => key.length === 15 && key.includes("T"));
  return keys.length > 0 ? keys.sort().at(-1) : currentUtcAcquisitionKey();
}

function fireMarkerSize(level) {
  const sizes = {
    high: 26,
    medium: 22,
    low: 17,
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
map.createPane("municipality-context-pane");
map.getPane("municipality-context-pane").style.zIndex = 350;
map.createPane("state-boundary-pane");
map.getPane("state-boundary-pane").style.zIndex = 450;

let activeLayer = "dark";
let currentFires = [];
let showFirms = true;
let showInpe  = true;

function visibleFires() {
  return currentFires.filter(f => {
    if (f.satellite === "Teste") return true;
    return f.satellite === "INPE" ? showInpe : showFirms;
  });
}

const mapLoading = document.getElementById("map-loading");
const mapLoadingText = document.getElementById("map-loading-text");
let loadingCount = 0;

function setControlsLoading(isLoading) {
  document.querySelectorAll(".filter-control").forEach(control => {
    if (isLoading) {
      if (!control.dataset.loadingWasDisabled) {
        control.dataset.loadingWasDisabled = control.disabled ? "true" : "false";
      }
      control.disabled = true;
      return;
    }

    if (control.dataset.loadingWasDisabled) {
      control.disabled = control.dataset.loadingWasDisabled === "true";
      delete control.dataset.loadingWasDisabled;
    }
  });

  const refreshButton = document.getElementById("refresh-btn");
  if (!refreshButton) return;

  if (isLoading) {
    if (!refreshButton.dataset.loadingWasDisabled) {
      refreshButton.dataset.loadingWasDisabled = refreshButton.disabled ? "true" : "false";
    }
    refreshButton.disabled = true;
  } else if (refreshButton.dataset.loadingWasDisabled) {
    refreshButton.disabled = refreshButton.dataset.loadingWasDisabled === "true";
    delete refreshButton.dataset.loadingWasDisabled;
  }
}

function updateLoadingOverlay(label) {
  const isLoading = loadingCount > 0;
  if (label && mapLoadingText) mapLoadingText.textContent = label;
  mapLoading.classList.toggle("show", isLoading);
  mapLoading.setAttribute("aria-hidden", isLoading ? "false" : "true");
  setControlsLoading(isLoading);
}

function beginLoading(label = "Carregando focos de incêndio...") {
  loadingCount += 1;
  updateLoadingOverlay(label);

  let finished = false;
  return () => {
    if (finished) return;
    finished = true;
    loadingCount = Math.max(0, loadingCount - 1);
    updateLoadingOverlay();
  };
}

function waitForNextPaint() {
  return new Promise(resolve => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  });
}

function waitForTileLayerReady(layer, timeoutMs = 2500) {
  return new Promise(resolve => {
    if (!layer || layer._tilesToLoad === 0) {
      resolve();
      return;
    }

    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      clearTimeout(timeout);
      layer.off("load", finish);
      layer.off("tileerror", finish);
      resolve();
    };

    const timeout = setTimeout(finish, timeoutMs);
    layer.once("load", finish);
    layer.once("tileerror", finish);
  });
}

function setActiveLayer(nextLayer) {
  if (nextLayer === activeLayer) return;

  tileLayers[activeLayer].remove();
  activeLayer = nextLayer;
  tileLayers[activeLayer].addTo(map);
  document.querySelectorAll(".layer-btn").forEach(button => {
    button.classList.toggle("active", button.dataset.layer === activeLayer);
  });

  // Re-apply polygon styles for new mode
  const s = STYLES[activeLayer];
  if (municipalityContextLayer) municipalityContextLayer.setStyle(s.context);
  if (municipalityLayer) municipalityLayer.setStyle(s.municipality);
  if (ucLayer)           ucLayer.setStyle(s.uc);

  // Re-render fire markers with new palette
  if (currentFires.length > 0) renderFires(visibleFires());
}

document.querySelectorAll(".layer-btn").forEach(button => {
  button.addEventListener("click", () => {
    setActiveLayer(button.dataset.layer);
  });
});

function setSwitchState(button, enabled) {
  button.classList.toggle("active", enabled);
  button.setAttribute("aria-pressed", enabled ? "true" : "false");
}

// ─── Polygon layers ───────────────────────────────────────────────────────────
let stateBoundaryLayer = null;
let municipalityContextLayer = null;
let municipalityLayer = null;
let ucLayer = null;

const STATE_BOUNDARY_STYLE = {
  color: "#ffffff",
  weight: 1.8,
  fill: false,
  fillOpacity: 0,
  opacity: 0.9,
  interactive: false,
};

async function loadMunicipalityContextLayer() {
  if (municipalityContextLayer) return;

  const data = await fetch("/static/geojson/mg_municipios_simplified.geojson").then(r => r.json());
  if (!data.features || data.features.length === 0) return;

  municipalityContextLayer = L.geoJSON(data, {
    style: (STYLES[activeLayer] || STYLES.dark).context,
    interactive: false,
    pane: "municipality-context-pane",
  }).addTo(map);
}

function clearPolygonLayers() {
  if (municipalityLayer) { map.removeLayer(municipalityLayer); municipalityLayer = null; }
  if (ucLayer)           { map.removeLayer(ucLayer);           ucLayer = null; }
}

async function loadStateBoundary() {
  if (stateBoundaryLayer) return;

  try {
    const mgData = await fetch("/api/geojson/mg").then(r => r.json());
    if (!mgData.features || mgData.features.length === 0) return;

    stateBoundaryLayer = L.geoJSON(mgData, {
      style: STATE_BOUNDARY_STYLE,
      interactive: false,
      pane: "state-boundary-pane",
    }).addTo(map);
  } catch (e) {
    console.error("Erro ao carregar limite de Minas Gerais:", e);
  }
}

async function loadPolygonLayers(unitIds) {
  clearPolygonLayers();
  if (!unitIds || unitIds.length === 0) return;

  try {
    const styles = STYLES[activeLayer] || STYLES.dark;
    const query = unitsQueryString(unitIds);
    const [munData, ucData] = await Promise.all([
      fetch(`/api/geojson/units?${query}`).then(r => r.json()),
      fetch(`/api/geojson/ucs?${query}`).then(r => r.json()),
    ]);

    if (munData.features && munData.features.length > 0) {
      municipalityLayer = L.geoJSON(munData, {
        style: styles.municipality,
        onEachFeature: (feature, layer) => {
          const name = feature.properties?.sv_nome || feature.properties?.NM_MUN || "";
          if (name) layer.bindTooltip(`Município: ${name}`, { sticky: true });
        },
      }).addTo(map);

      map.fitBounds(municipalityLayer.getBounds(), { padding: [20, 20] });
    }

    if (ucData.features && ucData.features.length > 0) {
      ucLayer = L.geoJSON(ucData, {
        style: styles.uc,
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

function createTestFireIcon() {
  const size = 22;
  return L.divIcon({
    className: "fire-div-icon",
    html: `<span class="fire-marker fire-marker--teste"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2)],
  });
}

function buildMarker(event) {
  const frp    = event.frp ?? 0;
  const isInpe = event.satellite === "INPE";
  const isTest = event.satellite === "Teste";
  const tier   = frpTier(frp);
  const color  = isTest ? "#9b59b6" : frpColor(frp);
  const frpCell = isTest
    ? "Simulado"
    : isInpe
      ? "Desconhecido"
      : `<strong>${frp} MW</strong><br><small>Estimativa da energia/calor emitido pelo fogo no momento da passagem do satélite.</small>`;
  const testBadge = isTest
    ? `<div class="popup-test-badge">FOCO DE TESTE</div>`
    : "";

  const marker = L.marker([event.latitude, event.longitude], {
    icon: isTest ? createTestFireIcon() : createFireIcon(tier),
  });

  marker.bindPopup(`
    <div class="popup-inner">
      <div class="popup-header" style="border-left:3px solid ${color}">
        <span class="popup-tier">Intensidade ${frpLabel(frp)}</span>
      </div>
      ${testBadge}
      <table class="popup-table">
        <tr><td>Data da detecção</td><td>${event.acq_date ?? "—"}<br><small>Dia em que o satélite identificou este foco.</small></td></tr>
        <tr><td>Horário da detecção</td><td>${formattedDetectionTime(event.acq_time)}</td></tr>
        <tr><td>Potência Radiativa do Fogo (FRP)</td><td>${frpCell}</td></tr>
        <tr><td>Fonte de detecção</td><td>${detectionSourceLabel(event)}<br><small>Base que reportou este foco de incêndio.</small></td></tr>
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
const severityCards = {
  high: document.getElementById("stat-high-card"),
  mid: document.getElementById("stat-mid-card"),
  low: document.getElementById("stat-low-card"),
};
const severityEmpty = document.getElementById("severity-empty");
const municipalityList = document.getElementById("municipality-list");
const municipalityShowAll = document.getElementById("municipality-show-all");
let municipalitySummaryExpanded = false;

const sidebar = document.getElementById("sidebar");
const mobileSheetToggle = document.getElementById("mobile-sheet-toggle");
const sidebarTabs = document.querySelectorAll(".sidebar-tab");
const sidebarTabPanels = document.querySelectorAll(".sidebar-tab-panel");

function refreshMapSize() {
  window.setTimeout(() => map.invalidateSize(), 220);
}

function setMobileSheetExpanded(isExpanded) {
  if (!sidebar || !mobileSheetToggle) return;

  sidebar.classList.toggle("sidebar-expanded", isExpanded);
  mobileSheetToggle.setAttribute("aria-expanded", isExpanded ? "true" : "false");
  refreshMapSize();
}

function activateSidebarTab(tab) {
  sidebarTabs.forEach(button => {
    const isActive = button === tab;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  sidebarTabPanels.forEach(panel => {
    panel.hidden = panel.id !== tab.getAttribute("aria-controls");
    panel.classList.toggle("active", !panel.hidden);
  });

  closeUnitTree();
}

sidebarTabs.forEach(tab => {
  tab.addEventListener("click", () => activateSidebarTab(tab));
});

if (mobileSheetToggle) {
  mobileSheetToggle.addEventListener("click", () => {
    setMobileSheetExpanded(!sidebar.classList.contains("sidebar-expanded"));
  });
}

function setSeverityCard(tier, count) {
  const card = severityCards[tier];
  if (!card) return;

  card.hidden = count === 0;
  document.getElementById(`stat-${tier}`).textContent = count;
}

function municipalityCounts(fires) {
  const counts = new Map();
  fires.forEach(fire => {
    const municipality = fire.municipality || "Município não identificado";
    counts.set(municipality, (counts.get(municipality) || 0) + 1);
  });

  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "pt-BR"));
}

function renderMunicipalitySummary(fires) {
  const municipalities = municipalityCounts(fires);
  const visibleMunicipalities = municipalitySummaryExpanded
    ? municipalities
    : municipalities.slice(0, 5);

  municipalityList.innerHTML = "";

  if (municipalities.length === 0) {
    const item = document.createElement("li");
    item.className = "municipality-empty";
    item.textContent = "Nenhum município afetado";
    municipalityList.appendChild(item);
  } else {
    visibleMunicipalities.forEach(({ name, count }) => {
      const item = document.createElement("li");
      item.className = "municipality-item";

      const nameEl = document.createElement("span");
      nameEl.className = "municipality-name";
      nameEl.textContent = name;
      item.appendChild(nameEl);

      const countEl = document.createElement("span");
      countEl.className = "municipality-count";
      countEl.textContent = count === 1 ? "1 foco" : `${count} focos`;
      item.appendChild(countEl);

      municipalityList.appendChild(item);
    });
  }

  municipalityShowAll.hidden = municipalities.length <= 5;
  municipalityShowAll.textContent = municipalitySummaryExpanded ? "Ver menos" : "Ver todos";
}

function updateStats(fires) {
  const high = fires.filter(f => (f.frp ?? 0) > 100).length;
  const mid  = fires.filter(f => (f.frp ?? 0) > 30 && (f.frp ?? 0) <= 100).length;
  const low  = fires.filter(f => (f.frp ?? 0) <= 30).length;

  document.getElementById("stat-total").textContent = fires.length;
  setSeverityCard("high", high);
  setSeverityCard("mid", mid);
  setSeverityCard("low", low);
  severityEmpty.hidden = high + mid + low > 0;
  renderMunicipalitySummary(fires);
}

municipalityShowAll.addEventListener("click", () => {
  municipalitySummaryExpanded = !municipalitySummaryExpanded;
  renderMunicipalitySummary(visibleFires());
});

// ─── Nested unit tree ─────────────────────────────────────────────────────────
const unitTreeRoot = document.getElementById("unit-tree");
const unitTreeTrigger = document.getElementById("unit-tree-trigger");
const unitTreePanel = document.getElementById("unit-tree-panel");
const unitTreeSummary = document.getElementById("unit-tree-summary");
const unitTreeSearch = document.getElementById("unit-tree-search");
const unitTreeSelectAll = document.getElementById("unit-tree-select-all");
const unitTreeList = document.getElementById("unit-tree-list");
const applyFiltersBtn = document.getElementById("apply-filters-btn");

let operationalUnits = [];
let unitsById = new Map();
let childrenByParent = new Map();
let rootUnitIds = [];
let checkedUnitIds = new Set();
let expandedUnitIds = new Set();
let unitTreeSearchValue = "";

function compactUnitName(name) {
  return String(name || "")
    .replace(/\bComando Operacional de Bombeiros\b/gi, "COB")
    .replace(/\bBatalh[ãa]o de Bombeiros Militar\b/gi, "BBM");
}

function buildUnitTree(units) {
  unitsById = new Map(units.map(unit => [unit.id, unit]));
  childrenByParent = new Map();

  units.forEach(unit => {
    const parentId = unit.parent_id || null;
    if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
    childrenByParent.get(parentId).push(unit);
  });

  for (const [parentId, children] of childrenByParent.entries()) {
    children.sort((a, b) => a.name.localeCompare(b.name, "pt-BR"));
    childrenByParent.set(parentId, children);
  }

  rootUnitIds = (childrenByParent.get(null) || []).map(unit => unit.id);
}

function childUnits(unitId) {
  return childrenByParent.get(unitId) || [];
}

function hasChildren(unitId) {
  return childUnits(unitId).length > 0;
}

function collectDescendantIds(unitId, ids = []) {
  for (const child of childUnits(unitId)) {
    ids.push(child.id);
    collectDescendantIds(child.id, ids);
  }
  return ids;
}

function setSubtreeChecked(unitId, checked) {
  if (checked) {
    checkedUnitIds.add(unitId);
  } else {
    checkedUnitIds.delete(unitId);
  }

  for (const childId of collectDescendantIds(unitId, [])) {
    if (checked) checkedUnitIds.add(childId);
    else checkedUnitIds.delete(childId);
  }
}

function hasAnyCheckedDescendant(unitId) {
  for (const child of childUnits(unitId)) {
    if (checkedUnitIds.has(child.id) || hasAnyCheckedDescendant(child.id)) {
      return true;
    }
  }
  return false;
}

function syncAncestors(unitId) {
  let currentId = unitsById.get(unitId)?.parent_id || null;
  while (currentId) {
    const children = childUnits(currentId);
    const allChildrenChecked = children.length > 0 && children.every(child => checkedUnitIds.has(child.id));
    if (allChildrenChecked) checkedUnitIds.add(currentId);
    else checkedUnitIds.delete(currentId);
    currentId = unitsById.get(currentId)?.parent_id || null;
  }
}

function isUnitChecked(unitId) {
  return checkedUnitIds.has(unitId);
}

function isUnitIndeterminate(unitId) {
  return !isUnitChecked(unitId) && hasAnyCheckedDescendant(unitId);
}

function matchesSearch(unit, searchValue) {
  if (!searchValue) return true;
  const fullName = unit.name.toLocaleLowerCase("pt-BR");
  const compactName = compactUnitName(unit.name).toLocaleLowerCase("pt-BR");
  return fullName.includes(searchValue) || compactName.includes(searchValue);
}

function nodeVisible(unitId, searchValue) {
  const unit = unitsById.get(unitId);
  if (!unit) return false;
  if (matchesSearch(unit, searchValue)) return true;
  return childUnits(unitId).some(child => nodeVisible(child.id, searchValue));
}

function shouldExpandNode(unitId) {
  if (unitTreeSearchValue) return true;
  return expandedUnitIds.has(unitId);
}

function selectedUnitIds() {
  const effective = [];

  function visit(unitId) {
    if (checkedUnitIds.has(unitId)) {
      effective.push(unitId);
      return;
    }
    for (const child of childUnits(unitId)) visit(child.id);
  }

  rootUnitIds.forEach(visit);
  return effective;
}

function updateTreeSummary() {
  const effective = selectedUnitIds();
  if (effective.length === 0) {
    unitTreeSummary.textContent = "Todo o estado de Minas Gerais";
    return;
  }
  if (effective.length === 1) {
    unitTreeSummary.textContent = compactUnitName(unitsById.get(effective[0])?.name || "1 unidade");
    return;
  }
  unitTreeSummary.textContent = `${effective.length} unidades selecionadas`;
}

function updateSelectAllState() {
  const allChecked = rootUnitIds.length > 0 && rootUnitIds.every(id => checkedUnitIds.has(id));
  const someChecked = rootUnitIds.some(id => checkedUnitIds.has(id) || hasAnyCheckedDescendant(id));
  unitTreeSelectAll.checked = allChecked;
  unitTreeSelectAll.indeterminate = !allChecked && someChecked;
}

function renderTreeNode(unit, depth = 0) {
  if (!nodeVisible(unit.id, unitTreeSearchValue)) return null;

  const node = document.createElement("div");
  node.className = "unit-tree-node";
  if (shouldExpandNode(unit.id)) node.classList.add("expanded");

  const row = document.createElement("div");
  row.className = "unit-tree-row";
  row.style.setProperty("--depth", String(depth));
  node.appendChild(row);

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "unit-tree-toggle filter-control";
  if (!hasChildren(unit.id)) toggle.classList.add("is-leaf");
  toggle.setAttribute("aria-label", `Expandir ${unit.name}`);
  toggle.addEventListener("click", event => {
    event.stopPropagation();
    if (!hasChildren(unit.id)) return;
    if (expandedUnitIds.has(unit.id)) expandedUnitIds.delete(unit.id);
    else expandedUnitIds.add(unit.id);
    renderUnitTree();
  });
  row.appendChild(toggle);

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "unit-tree-checkbox filter-control";
  checkbox.checked = isUnitChecked(unit.id);
  checkbox.indeterminate = isUnitIndeterminate(unit.id);
  checkbox.addEventListener("change", async event => {
    setSubtreeChecked(unit.id, event.target.checked);
    syncAncestors(unit.id);
    renderUnitTree();
    updateTreeSummary();
    resetUcAlarmForFilterChange();
  });
  row.appendChild(checkbox);

  const label = document.createElement("span");
  label.className = "unit-tree-label";
  label.textContent = compactUnitName(unit.name);
  row.appendChild(label);

  row.addEventListener("click", event => {
    if (event.target === checkbox || event.target === toggle) return;

    if (hasChildren(unit.id)) {
      if (expandedUnitIds.has(unit.id)) expandedUnitIds.delete(unit.id);
      else expandedUnitIds.add(unit.id);
      renderUnitTree();
      return;
    }

    checkbox.click();
  });

  const children = childUnits(unit.id).filter(child => nodeVisible(child.id, unitTreeSearchValue));
  if (children.length > 0) {
    const childrenEl = document.createElement("div");
    childrenEl.className = "unit-tree-children";
    children.forEach(child => {
      const childNode = renderTreeNode(child, depth + 1);
      if (childNode) childrenEl.appendChild(childNode);
    });
    node.appendChild(childrenEl);
  }

  return node;
}

function renderUnitTree() {
  unitTreeList.innerHTML = "";
  const visibleRoots = rootUnitIds
    .map(id => unitsById.get(id))
    .filter(unit => unit && nodeVisible(unit.id, unitTreeSearchValue));

  if (visibleRoots.length === 0) {
    const empty = document.createElement("div");
    empty.className = "unit-tree-empty";
    empty.textContent = "Nenhuma unidade encontrada.";
    unitTreeList.appendChild(empty);
  } else {
    visibleRoots.forEach(unit => {
      const node = renderTreeNode(unit, 0);
      if (node) unitTreeList.appendChild(node);
    });
  }

  updateTreeSummary();
  updateSelectAllState();
}

function openUnitTree() {
  unitTreeRoot.classList.add("open");
  unitTreePanel.hidden = false;
  unitTreeTrigger.setAttribute("aria-expanded", "true");
}

function closeUnitTree() {
  unitTreeRoot.classList.remove("open");
  unitTreePanel.hidden = true;
  unitTreeTrigger.setAttribute("aria-expanded", "false");
}

unitTreeTrigger.addEventListener("click", () => {
  if (unitTreePanel.hidden) {
    openUnitTree();
    unitTreeSearch.focus();
  } else {
    closeUnitTree();
  }
});

unitTreeSearch.addEventListener("input", event => {
  unitTreeSearchValue = String(event.target.value || "").trim().toLocaleLowerCase("pt-BR");
  renderUnitTree();
});

unitTreeSelectAll.addEventListener("change", event => {
  rootUnitIds.forEach(rootId => setSubtreeChecked(rootId, event.target.checked));
  renderUnitTree();
  updateTreeSummary();
  resetUcAlarmForFilterChange();
});

applyFiltersBtn.addEventListener("click", async () => {
  closeUnitTree();
  await applyFilters();
});

document.addEventListener("click", event => {
  if (unitTreeRoot.contains(event.target)) return;
  if (unitTreePanel.contains(event.target)) return;
  closeUnitTree();
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape") closeUnitTree();
});

// ─── Status + fire fetch ──────────────────────────────────────────────────────
const lastUpdatedEl = document.getElementById("last-updated");
const totalEventsEl = document.getElementById("total-events");

let knownLastFetchAt = null;

function unitsQueryString(unitIds) {
  const params = new URLSearchParams();
  unitIds.forEach(unitId => params.append("units", unitId));
  return params.toString();
}

async function updateStatus() {
  try {
    const unitIds = selectedUnitIds();
    const query = unitsQueryString(unitIds);
    const url  = query ? `/api/status?${query}` : "/api/status";
    const data = await fetch(url).then(r => r.json());
    lastUpdatedEl.textContent = formattedLastUpdate(data.last_fetch_at);
    totalEventsEl.textContent = data.total_events ?? 0;

    if (knownLastFetchAt !== null && data.last_fetch_at !== knownLastFetchAt) {
      knownLastFetchAt = data.last_fetch_at;
      await applyFilters("Novos dados disponíveis...");
    } else {
      knownLastFetchAt = data.last_fetch_at;
    }
  } catch (e) {
    console.error("Erro ao buscar status:", e);
  }
}

async function loadCurrentSelection() {
  const unitIds = selectedUnitIds();
  const query = unitsQueryString(unitIds);
  const firesUrl = query ? `/api/fires?${query}` : "/api/fires";
  const [fires] = await Promise.all([
    fetch(firesUrl).then(r => r.json()),
    loadPolygonLayers(unitIds),
  ]);
  currentFires = fires;
  renderFires(visibleFires());
  await updateStatus();
  await checkUcAlerts();
}

async function applyFilters(loadingLabel = "Carregando focos de incêndio...") {
  const finishLoading = beginLoading(loadingLabel);
  try {
    await waitForNextPaint();
    await loadCurrentSelection();
  } catch (e) {
    console.error("Erro ao carregar focos:", e);
    showToast("Erro ao carregar focos de incêndio.", "error");
  } finally {
    finishLoading();
  }
}

// ─── Source toggles ───────────────────────────────────────────────────────────
document.getElementById("source-firms").addEventListener("click", function () {
  showFirms = !showFirms;
  setSwitchState(this, showFirms);
  renderFires(visibleFires());
});

document.getElementById("source-inpe").addEventListener("click", function () {
  showInpe = !showInpe;
  setSwitchState(this, showInpe);
  renderFires(visibleFires());
});

// ─── Refresh button ───────────────────────────────────────────────────────────
const refreshBtn  = document.getElementById("refresh-btn");
const refreshIcon = document.getElementById("refresh-icon");

refreshBtn.addEventListener("click", async () => {
  refreshIcon.classList.add("spinning");
  try {
    await applyFilters("Atualizando dados...");
  } finally {
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

// ─── UC alarm ────────────────────────────────────────────────────────────────
const UC_ALARM_POLL_MS = 60 * 1000;
const alarmToggle = document.getElementById("uc-alarm-toggle");
const alarmToggleLabel = document.getElementById("uc-alarm-toggle-label");
const alertModal = document.getElementById("uc-alert-modal");
const alertAckBtn = document.getElementById("uc-alert-ack");
const alertNameEl = document.getElementById("uc-alert-name");
const alertTimeEl = document.getElementById("uc-alert-time");
const alertSatelliteEl = document.getElementById("uc-alert-satellite");
const alertCountEl = document.getElementById("uc-alert-count");
const alertFrpEl = document.getElementById("uc-alert-frp");

let alarmEnabled = false;
let alarmAlerting = false;
let alarmAfter = null;
let alarmUnits = [];
let alarmTimer = null;
let audioContext = null;
let alarmSoundTimer = null;
let acknowledgedAlertKeys = new Set();

function setAlarmButtonState() {
  alarmToggle.classList.toggle("active", alarmEnabled);
  alarmToggle.classList.toggle("alerting", alarmAlerting);
  alarmToggle.setAttribute("aria-pressed", alarmEnabled ? "true" : "false");
  alarmToggleLabel.textContent = alarmAlerting
    ? "Alarme disparado"
    : alarmEnabled
      ? "Alarme UC ligado"
      : "Ativar alarme de incêndio em UC";
}

function ensureAudioContext() {
  const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextCtor) return null;
  if (!audioContext) audioContext = new AudioContextCtor();
  if (audioContext.state === "suspended") audioContext.resume();
  return audioContext;
}

function playAlarmBeep() {
  const context = ensureAudioContext();
  if (!context) return;

  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(740, context.currentTime);
  gain.gain.setValueAtTime(0.0001, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.32);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 0.34);
}

function startAlarmSound() {
  if (alarmSoundTimer) return;
  playAlarmBeep();
  alarmSoundTimer = setInterval(playAlarmBeep, 900);
}

function stopAlarmSound() {
  if (alarmSoundTimer) {
    clearInterval(alarmSoundTimer);
    alarmSoundTimer = null;
  }
}

function hideUcAlert() {
  alertModal.classList.remove("show");
  alertModal.setAttribute("aria-hidden", "true");
}

function showUcAlert(alert) {
  const timeLabel = formattedDetectionTime(alert.acq_time);
  const maxFrp = alert.max_frp == null ? "Não informado" : `${Number(alert.max_frp).toFixed(1)} MW (${alert.max_intensity})`;

  alertNameEl.textContent = alert.uc_name || "UC não informada";
  alertTimeEl.textContent = `${alert.acq_date || "Data não informada"} ${timeLabel}`;
  alertSatelliteEl.textContent = alert.satellite || "Não informado";
  alertCountEl.textContent = String(alert.event_count || 0);
  alertFrpEl.textContent = maxFrp;

  alertModal.classList.add("show");
  alertModal.setAttribute("aria-hidden", "false");
  alertAckBtn.focus();
}

function clearAlarmTimer() {
  if (alarmTimer) {
    clearInterval(alarmTimer);
    alarmTimer = null;
  }
}

function disableUcAlarm(showMessage = false) {
  alarmEnabled = false;
  alarmAlerting = false;
  alarmAfter = null;
  alarmUnits = [];
  clearAlarmTimer();
  stopAlarmSound();
  hideUcAlert();
  setAlarmButtonState();
  if (showMessage) showToast("Alarme de UC desligado.", "info");
}

async function checkUcAlerts() {
  if (!alarmEnabled || alarmAlerting || !alarmAfter) return;

  try {
    const params = new URLSearchParams({ after: alarmAfter });
    alarmUnits.forEach(unitId => params.append("units", unitId));
    const alerts = await fetch(`/api/alerts/uc-fires?${params.toString()}`).then(r => r.json());
    const alert = alerts.find(item => !acknowledgedAlertKeys.has(item.alert_key));
    if (!alert) return;

    acknowledgedAlertKeys.add(alert.alert_key);
    alarmAlerting = true;
    clearAlarmTimer();
    setAlarmButtonState();
    showUcAlert(alert);
    startAlarmSound();
  } catch (e) {
    console.error("Erro ao verificar alertas de UC:", e);
  }
}

function enableUcAlarm() {
  ensureAudioContext();
  alarmEnabled = true;
  alarmAlerting = false;
  alarmAfter = maxAcquisitionKey(currentFires);
  alarmUnits = selectedUnitIds();
  setAlarmButtonState();
  clearAlarmTimer();
  alarmTimer = setInterval(checkUcAlerts, UC_ALARM_POLL_MS);
  showToast("Alarme de UC ligado para novas passagens de satélite.", "info");
}

function handleUcAlarmToggle() {
  if (alarmEnabled) {
    disableUcAlarm(true);
    return;
  }
  enableUcAlarm();
}

function resetUcAlarmForFilterChange() {
  if (!alarmEnabled && !alarmAlerting) return;
  disableUcAlarm(false);
  showToast("Alarme de UC desligado pela mudança de filtro.", "info");
}

alarmToggle.addEventListener("click", handleUcAlarmToggle);
alertAckBtn.addEventListener("click", () => {
  disableUcAlarm(false);
  showToast("Alerta reconhecido. Alarme de UC desligado.", "info");
});

// ─── Infographic modal ────────────────────────────────────────────────────────
const infographicModal   = document.getElementById("infographic-modal");
const infographicClose   = document.getElementById("infographic-close");
const infographicBackdrop = infographicModal.querySelector(".infographic-backdrop");
const helpBtn            = document.getElementById("help-btn");

function openInfographic() {
  infographicModal.classList.add("show");
  infographicModal.setAttribute("aria-hidden", "false");
  infographicClose.focus();
}

function closeInfographic() {
  infographicModal.classList.remove("show");
  infographicModal.setAttribute("aria-hidden", "true");
  helpBtn.focus();
}

helpBtn.addEventListener("click", openInfographic);
infographicClose.addEventListener("click", closeInfographic);
infographicBackdrop.addEventListener("click", closeInfographic);

document.addEventListener("keydown", event => {
  if (event.key === "Escape" && infographicModal.classList.contains("show")) {
    closeInfographic();
  }
});

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function boot() {
  await waitForTileLayerReady(tileLayers.dark);
  const finishLoading = beginLoading("Carregando focos de incêndio...");

  try {
    await waitForNextPaint();

    operationalUnits = await fetch("/api/operational-units").then(r => r.json());
    buildUnitTree(operationalUnits);
    if (rootUnitIds.length > 0) {
      const firstRootId = rootUnitIds[0];
      setSubtreeChecked(firstRootId, true);
    }
    renderUnitTree();

    await loadCurrentSelection();
  } catch (e) {
    console.error("Erro ao carregar unidades operacionais:", e);
    showToast("Erro ao carregar dados iniciais.", "error");
  } finally {
    finishLoading();
  }

  Promise.all([
    loadStateBoundary(),
    loadMunicipalityContextLayer(),
  ]).catch(e => {
    console.error("Erro ao carregar camadas de contexto:", e);
  });

  setInterval(updateStatus, 60 * 1000);
}

boot();
