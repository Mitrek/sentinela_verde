from __future__ import annotations

import httpx
import pytest

from fetcher import FIRMS_SOURCES, fetch_firms_data


VIIRS_SAMPLE_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
-10.123,-55.456,320.5,0.39,0.36,2026-06-04,1420,N,nominal,2.0NRT,290.1,45.2,D
"""
MODIS_SAMPLE_CSV = """latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight
-11.123,-56.456,315.5,1.00,0.80,2026-06-04,1520,T,80,6.1NRT,285.1,25.2,D
"""


@pytest.mark.asyncio
async def test_fetch_firms_data_parses_valid_csv(monkeypatch):
    async def mock_get(self, url):
        if "VIIRS_SNPP_NRT" in url:
            return httpx.Response(200, text=VIIRS_SAMPLE_CSV, request=httpx.Request("GET", url))
        return httpx.Response(500, text="server error", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    events = await fetch_firms_data("api-key", "-74,-34,-34,5.5", 1)

    assert len(events) == 1
    assert events[0] == {
        "latitude": -10.123,
        "longitude": -55.456,
        "brightness": 320.5,
        "scan": 0.39,
        "track": 0.36,
        "acq_date": "2026-06-04",
        "acq_time": "1420",
        "satellite": "N",
        "confidence": "nominal",
        "frp": 45.2,
        "daynight": "D",
    }


@pytest.mark.asyncio
async def test_fetch_firms_data_returns_empty_list_on_http_500(monkeypatch):
    async def mock_get(self, url):
        return httpx.Response(500, text="server error", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    events = await fetch_firms_data("api-key", "-74,-34,-34,5.5", 1)

    assert events == []


@pytest.mark.asyncio
async def test_fetch_firms_data_returns_empty_list_on_malformed_csv(monkeypatch):
    malformed_csv = "foo,bar\n1,2\n"

    async def mock_get(self, url):
        return httpx.Response(200, text=malformed_csv, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    events = await fetch_firms_data("api-key", "-74,-34,-34,5.5", 1)

    assert events == []


@pytest.mark.asyncio
async def test_fetch_firms_data_merges_all_three_sources(monkeypatch):
    source_payloads = {
        "VIIRS_SNPP_NRT": VIIRS_SAMPLE_CSV,
        "VIIRS_NOAA20_NRT": """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
-12.123,-57.456,330.5,0.50,0.40,2026-06-04,1620,J,high,2.0NRT,295.1,105.2,D
""",
        "MODIS_NRT": MODIS_SAMPLE_CSV,
    }

    async def mock_get(self, url):
        for source in FIRMS_SOURCES:
            if source in url:
                return httpx.Response(
                    200,
                    text=source_payloads[source],
                    request=httpx.Request("GET", url),
                )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    events = await fetch_firms_data("api-key", "-74,-34,-34,5.5", 1)

    assert len(events) == 3
    assert {event["satellite"] for event in events} == {"N", "J", "T"}
