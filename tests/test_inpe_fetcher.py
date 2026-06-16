from __future__ import annotations

import httpx
import pytest

from sentinela_verde.services.inpe import fetch_inpe_data


KML_NS = "http://www.opengis.net/kml/2.2"

_KML_WRAPPER = """\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Folder>
      {placemarks}
    </Folder>
  </Document>
</kml>"""

_POINT_PLACEMARK = """\
<Placemark>
  <description>
&lt;table&gt;
  &lt;tr&gt;&lt;td&gt;&lt;b&gt;Tipo&lt;/b&gt;&lt;/td&gt;&lt;td&gt;{tipo}&lt;/td&gt;&lt;/tr&gt;
  &lt;tr&gt;&lt;td&gt;&lt;b&gt;Estado&lt;/b&gt;&lt;/td&gt;&lt;td&gt;{estado}&lt;/td&gt;&lt;/tr&gt;
  &lt;tr&gt;&lt;td&gt;&lt;b&gt;Último foco&lt;/b&gt;&lt;/td&gt;&lt;td&gt;{ultimo_foco}&lt;/td&gt;&lt;/tr&gt;
&lt;/table&gt;
  </description>
  <Point>
    <coordinates>{lon},{lat},0.0</coordinates>
  </Point>
</Placemark>"""

_POLYGON_PLACEMARK = """\
<Placemark>
  <description>
&lt;table&gt;
  &lt;tr&gt;&lt;td&gt;&lt;b&gt;Tipo&lt;/b&gt;&lt;/td&gt;&lt;td&gt;Nova Queima Isolada&lt;/td&gt;&lt;/tr&gt;
  &lt;tr&gt;&lt;td&gt;&lt;b&gt;Estado&lt;/b&gt;&lt;/td&gt;&lt;td&gt;MINAS GERAIS&lt;/td&gt;&lt;/tr&gt;
  &lt;tr&gt;&lt;td&gt;&lt;b&gt;Último foco&lt;/b&gt;&lt;/td&gt;&lt;td&gt;2026-06-11 04:14:00&lt;/td&gt;&lt;/tr&gt;
&lt;/table&gt;
  </description>
  <Polygon>
    <outerBoundaryIs>
      <LinearRing>
        <coordinates>-44.0,-19.0,0.0 -43.9,-19.0,0.0 -43.9,-19.1,0.0 -44.0,-19.0,0.0</coordinates>
      </LinearRing>
    </outerBoundaryIs>
  </Polygon>
</Placemark>"""


def _make_kml(
    tipo="Nova Queima Isolada",
    estado="MINAS GERAIS",
    ultimo_foco="2026-06-11 04:14:00",
    lat="-19.5",
    lon="-43.9",
) -> str:
    placemark = _POINT_PLACEMARK.format(
        tipo=tipo,
        estado=estado,
        ultimo_foco=ultimo_foco,
        lat=lat,
        lon=lon,
    )
    return _KML_WRAPPER.format(placemarks=placemark)


def _mock_response(kml: str):
    async def mock_get(self, url):
        return httpx.Response(200, content=kml.encode(), request=httpx.Request("GET", url))
    return mock_get


@pytest.mark.asyncio
async def test_valid_mg_point_parsed(monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(_make_kml()))
    events = await fetch_inpe_data("http://test")
    assert len(events) == 1
    e = events[0]
    assert e["satellite"] == "INPE"
    assert e["confidence"] == "n"
    assert e["acq_date"] == "2026-06-11"
    assert e["acq_time"] == "0414"
    assert e["frp"] is None
    assert e["latitude"] == pytest.approx(-19.5)
    assert e["longitude"] == pytest.approx(-43.9)


@pytest.mark.asyncio
async def test_incendio_tipo_sets_moderate_frp(monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(_make_kml(tipo="Incêndio")))
    events = await fetch_inpe_data("http://test")
    assert len(events) == 1
    assert events[0]["frp"] == 50.0


@pytest.mark.asyncio
async def test_nova_queima_isolada_sets_low_frp(monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(_make_kml(tipo="Nova Queima Isolada")))
    events = await fetch_inpe_data("http://test")
    assert len(events) == 1
    assert events[0]["frp"] is None


@pytest.mark.asyncio
async def test_atividades_antropicas_sets_low_frp(monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(_make_kml(tipo="Atividades Antrópicas")))
    events = await fetch_inpe_data("http://test")
    assert len(events) == 1
    assert events[0]["frp"] is None


@pytest.mark.asyncio
async def test_polygon_placemark_ignored(monkeypatch):
    kml = _KML_WRAPPER.format(placemarks=_POLYGON_PLACEMARK)
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(kml))
    events = await fetch_inpe_data("http://test")
    assert events == []


@pytest.mark.asyncio
async def test_non_mg_estado_filtered_out(monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(_make_kml(estado="SÃO PAULO")))
    events = await fetch_inpe_data("http://test")
    assert events == []


@pytest.mark.asyncio
async def test_invalid_ultimo_foco_skips_event(monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(_make_kml(ultimo_foco="not-a-date")))
    events = await fetch_inpe_data("http://test")
    assert events == []


@pytest.mark.asyncio
async def test_invalid_coordinates_skips_event(monkeypatch):
    kml = _KML_WRAPPER.format(placemarks=_POINT_PLACEMARK.format(
        tipo="Nova Queima Isolada",
        estado="MINAS GERAIS",
        ultimo_foco="2026-06-11 04:14:00",
        lat="not-a-number",
        lon="also-bad",
    ))
    monkeypatch.setattr(httpx.AsyncClient, "get", _mock_response(kml))
    events = await fetch_inpe_data("http://test")
    assert events == []


@pytest.mark.asyncio
async def test_http_error_returns_empty_list(monkeypatch):
    async def mock_get(self, url):
        return httpx.Response(500, text="error", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    events = await fetch_inpe_data("http://test")
    assert events == []


@pytest.mark.asyncio
async def test_malformed_xml_returns_empty_list(monkeypatch):
    async def mock_get(self, url):
        return httpx.Response(200, content=b"this is not xml", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    events = await fetch_inpe_data("http://test")
    assert events == []
