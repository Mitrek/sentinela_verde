// Mock data for frontend development — replace with real API calls when merging with backend
const MOCK = {
  status: {
    last_fetch_at: "2026-06-12 08:30 UTC",
    total_events: 142,
  },
  areas: [
    { id: "triangulo", name: "Triângulo Mineiro", region: "Oeste" },
    { id: "norte", name: "Norte de Minas", region: "Norte" },
    { id: "vale_do_rio_doce", name: "Vale do Rio Doce", region: "Leste" },
    { id: "sul_sudoeste", name: "Sul/Sudoeste de Minas", region: "Sul" },
    { id: "zona_da_mata", name: "Zona da Mata", region: "Leste" },
    { id: "campos_das_vertentes", name: "Campos das Vertentes", region: "Sul" },
    { id: "metropolitana", name: "Metropolitana de BH", region: "Centro" },
  ],
  ucs: [
    { id: "parna_sempre_vivas", name: "PARNA Sempre-Vivas" },
    { id: "parna_grande_sertao", name: "PARNA Grande Sertão Veredas" },
    { id: "apa_carste", name: "APA Carste de Lagoa Santa" },
    { id: "rebio_mata_escura", name: "REBIO Mata Escura" },
  ],
  // Scattered fire events across Minas Gerais
  fires: [
    { latitude: -18.1, longitude: -44.0, frp: 150, acq_date: "2026-06-12", acq_time: "0712", satellite: "AQUA", confidence: "h" },
    { latitude: -17.5, longitude: -46.5, frp: 80,  acq_date: "2026-06-12", acq_time: "0830", satellite: "TERRA", confidence: "h" },
    { latitude: -19.2, longitude: -43.8, frp: 25,  acq_date: "2026-06-12", acq_time: "0900", satellite: "NOAA-20", confidence: "n" },
    { latitude: -16.7, longitude: -42.1, frp: 200, acq_date: "2026-06-11", acq_time: "1345", satellite: "AQUA", confidence: "h" },
    { latitude: -20.3, longitude: -45.6, frp: 55,  acq_date: "2026-06-11", acq_time: "1420", satellite: "TERRA", confidence: "n" },
    { latitude: -15.9, longitude: -44.9, frp: 10,  acq_date: "2026-06-12", acq_time: "0615", satellite: "NOAA-20", confidence: "n" },
    { latitude: -18.7, longitude: -47.8, frp: 310, acq_date: "2026-06-12", acq_time: "0745", satellite: "AQUA", confidence: "h" },
    { latitude: -21.1, longitude: -44.2, frp: 70,  acq_date: "2026-06-11", acq_time: "1530", satellite: "TERRA", confidence: "n" },
    { latitude: -17.0, longitude: -41.5, frp: 90,  acq_date: "2026-06-12", acq_time: "0820", satellite: "AQUA", confidence: "h" },
    { latitude: -19.9, longitude: -48.0, frp: 120, acq_date: "2026-06-11", acq_time: "1600", satellite: "NOAA-20", confidence: "h" },
    { latitude: -16.2, longitude: -43.5, frp: 40,  acq_date: "2026-06-12", acq_time: "0950", satellite: "TERRA", confidence: "n" },
    { latitude: -20.8, longitude: -46.1, frp: 185, acq_date: "2026-06-12", acq_time: "1005", satellite: "AQUA", confidence: "h" },
  ],
};
