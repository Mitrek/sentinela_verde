from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from shapely.geometry import Point

from areas import (
    _normalize_name,
    build_municipality_geometry,
    get_municipality_features,
    get_municipality_names,
)


ARTICULATION_TXT_PATH = Path(__file__).parent / "articulation" / "articulation.txt"

_UNITS_CACHE: list[dict] | None = None
_UNITS_BY_ID_CACHE: dict[str, dict] | None = None

_COB_RE = re.compile(r"^(\d+)[º°]\s+COMANDO OPERACIONAL DE BOMBEIROS$", re.IGNORECASE)
_BATTALION_RE = re.compile(r"^(\d+)[º°]\s+BATALH[ÃA]O DE BOMBEIROS MILITAR$", re.IGNORECASE)
_INDEPENDENT_COMPANY_RE = re.compile(
    r"^(\d+)[ªa]\s+(?:COMPANHIA INDEPENDENTE|CIA IND)",
    re.IGNORECASE,
)
_COMPANY_RE = re.compile(r"^\d+[ªa]\s+Cia(?:\s+BM)?$", re.IGNORECASE)
_PLATOON_RE = re.compile(
    r"^\d+[º°](?:\s+ao\s+\d+[º°])?\s+Pel(?:ot[ãa]o)?(?:\s+BM)?$",
    re.IGNORECASE,
)
_POST_RE = re.compile(r"^(?:PA(?:\s+BM)?|Brigada\s+municipal)$", re.IGNORECASE)
_RISP_RE = re.compile(r"^\d+[ªa]\s+RISP", re.IGNORECASE)
_MUNICIPALITY_LIST_RE = re.compile(
    r"Munic[ií]pios?:?\s*(.*?)(?=(?:\(\d+\)|Bairros|Regi[ãa]o|ANEXO|$))",
    re.IGNORECASE,
)
_LOWERCASE_WORDS = {"ao", "aos", "da", "de", "do", "das", "dos", "e"}
_UPPERCASE_WORDS = {"BM", "CBMMG", "COB", "PA", "RISP", "UEOP"}
_TITLECASE_WORDS = {
    "BATALHÃO",
    "BOMBEIROS",
    "COMANDO",
    "COMPANHIA",
    "INDEPENDENTE",
    "MILITAR",
    "OPERACIONAL",
}


def _clean_line(line: str) -> str:
    return " ".join(line.replace("–", "-").strip().split())


def _is_noise_line(line: str) -> bool:
    if not line:
        return True
    if line.isdigit():
        return True
    if line.startswith("ANEXO ÚNICO"):
        return True
    if line.startswith("COB UEOp"):
        return True
    if line.startswith("(a)"):
        return True
    return False


def _is_footnote_line(line: str) -> bool:
    return bool(re.match(r"^\d+\s", line) or re.match(r"^[¹²³]\s", line))


def _unit_kind(line: str) -> str | None:
    if _COB_RE.match(line):
        return "cob"
    if _BATTALION_RE.match(line) or _INDEPENDENT_COMPANY_RE.match(line):
        return "batalhao"
    if _COMPANY_RE.match(line):
        return "companhia"
    if _PLATOON_RE.match(line):
        return "pelotao"
    if _POST_RE.match(line):
        return "posto"
    return None


def _display_unit_type(unit_type: str) -> str:
    return {
        "cob": "COB",
        "batalhao": "Batalhão",
        "companhia": "Companhia",
        "pelotao": "Pelotão",
        "posto": "Posto Avançado",
    }[unit_type]


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", without_accents).strip("-").casefold()
    return slug or "unidade"


def _natural_word(word: str, is_first: bool = False) -> str:
    if not word:
        return word

    separator = "/" if "/" in word else "-" if "-" in word else None
    if separator:
        return separator.join(_natural_word(part, is_first and index == 0) for index, part in enumerate(word.split(separator)))

    stripped = word.strip()
    if stripped.upper() in _UPPERCASE_WORDS:
        return stripped.upper()

    lower = stripped.casefold()
    if not is_first and lower in _LOWERCASE_WORDS:
        return lower

    if stripped.upper() in _TITLECASE_WORDS or stripped.isupper():
        return stripped[:1].upper() + stripped[1:].casefold()

    return stripped[:1].upper() + stripped[1:]


def _natural_text(value: str) -> str:
    words = value.split()
    return " ".join(_natural_word(word, index == 0) for index, word in enumerate(words))


def _unit_id(unit_type: str, label: str, parent_id: str | None, used_ids: set[str]) -> str:
    base = f"{unit_type}-{_slugify(label)}"
    if parent_id:
        base = f"{parent_id}-{base}"

    unit_id = base
    index = 2
    while unit_id in used_ids:
        unit_id = f"{base}-{index}"
        index += 1
    used_ids.add(unit_id)
    return unit_id


def _next_location(lines: list[str], start_index: int) -> tuple[list[str], int]:
    location_lines = []
    index = start_index + 1
    while index < len(lines):
        line = lines[index]
        if _is_noise_line(line) or _unit_kind(line) or _RISP_RE.match(line):
            break
        if re.search(r"Munic[ií]pios?|Bairros|Regi[ãa]o de", line, re.IGNORECASE):
            break
        location_lines.append(line)
        index += 1
        if len(location_lines) >= 3:
            break
    return location_lines, index


def _normalize_source_label(label: str, location_lines: list[str]) -> str:
    source = label
    if label.endswith(" Pel") and location_lines and location_lines[0].casefold() == "bm":
        source = f"{label} BM"
        location_lines = location_lines[1:]

    location = " ".join(location_lines).strip()
    if location:
        return f"{_natural_text(source)} - {_natural_text(location)}"
    return _natural_text(source)


def _scan_municipalities(text: str, municipalities_by_normalized_name: dict[str, str]) -> list[str]:
    found = []
    padded_text = f" {_normalize_name(text)} "
    occupied_spans: list[tuple[int, int]] = []
    sorted_municipalities = sorted(
        municipalities_by_normalized_name.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for normalized_name, display_name in sorted_municipalities:
        match = re.search(rf"(?<!\w){re.escape(normalized_name)}(?!\w)", padded_text)
        if match is None:
            continue
        span = match.span()
        if any(start < span[1] and span[0] < end for start, end in occupied_spans):
            continue
        occupied_spans.append(span)
        found.append(display_name)
    return found


def _extract_bairro_municipality(
    line_index: int,
    lines: list[str],
    municipalities_by_normalized_name: dict[str, str],
) -> list[str]:
    line = lines[line_index]
    explicit_match = re.search(r"Bairros\s+de\s+([^:]+):", line, re.IGNORECASE)
    if explicit_match:
        found = _scan_municipalities(explicit_match.group(1), municipalities_by_normalized_name)
        if found:
            return found

    for start in range(line_index - 1, max(-1, line_index - 6), -1):
        for size in range(1, 4):
            candidate = " ".join(lines[start:start + size])
            normalized_candidate = _normalize_name(candidate)
            display_name = municipalities_by_normalized_name.get(normalized_candidate)
            if display_name:
                return [display_name]
    return []


def _extract_direct_municipios(
    raw_lines: list[str],
    municipalities_by_normalized_name: dict[str, str],
) -> tuple[list[str], bool]:
    municipios = []
    uses_municipality_fallback = False
    filtered_lines = [line for line in raw_lines if not _is_footnote_line(line)]
    text = " ".join(filtered_lines)

    for match in _MUNICIPALITY_LIST_RE.finditer(text):
        municipios.extend(_scan_municipalities(match.group(1), municipalities_by_normalized_name))

    for index, line in enumerate(filtered_lines):
        if re.search(r"\bBairros\b|Regi[ãa]o de", line, re.IGNORECASE):
            bairro_municipios = _extract_bairro_municipality(
                index,
                filtered_lines,
                municipalities_by_normalized_name,
            )
            if bairro_municipios:
                municipios.extend(bairro_municipios)
                uses_municipality_fallback = True

    deduped = []
    seen = set()
    for municipio in municipios:
        normalized_name = _normalize_name(municipio)
        if normalized_name not in seen:
            deduped.append(municipio)
            seen.add(normalized_name)
    return deduped, uses_municipality_fallback


def _append_unit(
    units: list[dict],
    used_ids: set[str],
    unit_type: str,
    label: str,
    parent_id: str | None,
    location_lines: list[str],
) -> dict:
    source_label = _normalize_source_label(label, location_lines.copy())
    unit = {
        "id": _unit_id(unit_type, source_label, parent_id, used_ids),
        "name": source_label,
        "type": unit_type,
        "type_label": _display_unit_type(unit_type),
        "parent_id": parent_id,
        "source_label": source_label,
        "municipios": [],
        "direct_municipios": [],
        "uses_municipality_fallback": False,
        "raw_lines": [],
    }
    units.append(unit)
    return unit


def _append_or_reuse_unit(
    units: list[dict],
    used_ids: set[str],
    reusable_units: dict[tuple[str, str | None, str], dict],
    unit_type: str,
    label: str,
    parent_id: str | None,
    location_lines: list[str],
) -> dict:
    source_label = _normalize_source_label(label, location_lines.copy())
    key = (unit_type, parent_id, source_label)
    if unit_type in {"cob", "batalhao", "companhia"} and key in reusable_units:
        return reusable_units[key]

    unit = _append_unit(units, used_ids, unit_type, label, parent_id, location_lines)
    if unit_type in {"cob", "batalhao", "companhia"}:
        reusable_units[key] = unit
    return unit


def _parse_units_from_text(text: str) -> list[dict]:
    raw_lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in raw_lines if not _is_noise_line(line)]
    municipalities_by_normalized_name = {
        _normalize_name(name): name
        for name in get_municipality_names()
    }

    units = []
    used_ids = set()
    reusable_units = {}
    current_cob = None
    current_battalion = None
    current_company = None
    current_unit = None

    index = 0
    while index < len(lines):
        line = lines[index]
        unit_type = _unit_kind(line)

        if unit_type is None:
            if current_unit is not None:
                current_unit["raw_lines"].append(line)
            index += 1
            continue

        location_lines, next_index = _next_location(lines, index)
        if unit_type == "cob":
            unit = _append_or_reuse_unit(
                units, used_ids, reusable_units, unit_type, line, None, location_lines[:1]
            )
            current_cob = unit
            current_battalion = None
            current_company = None
        elif unit_type == "batalhao":
            parent_id = current_cob["id"] if current_cob else None
            unit = _append_or_reuse_unit(
                units, used_ids, reusable_units, unit_type, line, parent_id, location_lines[:1]
            )
            current_battalion = unit
            current_company = None
        elif unit_type == "companhia":
            parent_id = current_battalion["id"] if current_battalion else (current_cob["id"] if current_cob else None)
            unit = _append_or_reuse_unit(
                units, used_ids, reusable_units, unit_type, line, parent_id, location_lines
            )
            current_company = unit
        else:
            parent = current_company or current_battalion or current_cob
            parent_id = parent["id"] if parent else None
            unit = _append_unit(units, used_ids, unit_type, line, parent_id, location_lines)

        current_unit = unit
        for consumed_line in lines[index + 1:next_index]:
            current_unit["raw_lines"].append(consumed_line)
        index = next_index

    units_by_id = {unit["id"]: unit for unit in units}
    children_by_parent: dict[str | None, list[dict]] = {}
    for unit in units:
        children_by_parent.setdefault(unit["parent_id"], []).append(unit)
        direct_municipios, uses_municipality_fallback = _extract_direct_municipios(
            unit["raw_lines"],
            municipalities_by_normalized_name,
        )
        unit["direct_municipios"] = direct_municipios
        unit["uses_municipality_fallback"] = uses_municipality_fallback

    def aggregate(unit: dict) -> list[str]:
        municipios = list(unit["direct_municipios"])
        uses_municipality_fallback = bool(unit["uses_municipality_fallback"])
        for child in children_by_parent.get(unit["id"], []):
            municipios.extend(aggregate(child))
            uses_municipality_fallback = uses_municipality_fallback or bool(child["uses_municipality_fallback"])

        deduped = []
        seen = set()
        for municipio in municipios:
            normalized_name = _normalize_name(municipio)
            if normalized_name not in seen:
                deduped.append(municipio)
                seen.add(normalized_name)

        unit["municipios"] = deduped
        unit["uses_municipality_fallback"] = uses_municipality_fallback
        return deduped

    for unit in units:
        if unit["parent_id"] is None:
            aggregate(unit)

    for unit in units:
        unit.pop("raw_lines", None)
        if unit["id"] not in units_by_id:
            continue

    return [unit for unit in units if unit["municipios"]]


def load_operational_units() -> list[dict]:
    """Return parsed operational CBMMG units from articulation.txt."""
    global _UNITS_CACHE, _UNITS_BY_ID_CACHE

    if _UNITS_CACHE is None:
        try:
            _UNITS_CACHE = _parse_units_from_text(ARTICULATION_TXT_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Failed to parse operational units: {exc}")
            _UNITS_CACHE = []
        _UNITS_BY_ID_CACHE = {unit["id"]: unit for unit in _UNITS_CACHE}

    return _UNITS_CACHE


def get_operational_unit(unit_id: str) -> dict | None:
    if _UNITS_BY_ID_CACHE is None:
        load_operational_units()
    return (_UNITS_BY_ID_CACHE or {}).get(unit_id)


def get_operational_unit_features(unit_id: str) -> list[dict]:
    unit = get_operational_unit(unit_id)
    if unit is None:
        return []
    return get_municipality_features(unit.get("municipios", []))


def get_operational_unit_geometry(unit_id: str) -> object | None:
    unit = get_operational_unit(unit_id)
    if unit is None:
        return None
    return build_municipality_geometry(
        unit.get("municipios", []),
        cache_key=f"operational:{unit_id}",
    )


def get_operational_unit_bounds(unit_id: str) -> tuple[float, float, float, float] | None:
    try:
        geometry = get_operational_unit_geometry(unit_id)
        if geometry is None:
            return None
        min_lon, min_lat, max_lon, max_lat = geometry.bounds
        return (min_lat, min_lon, max_lat, max_lon)
    except Exception as exc:
        print(f"Failed to get operational unit bounds for {unit_id}: {exc}")
        return None


def filter_events_by_operational_unit(events: list[dict], unit_id: str) -> list[dict]:
    try:
        geometry = get_operational_unit_geometry(unit_id)
        if geometry is None:
            return events
        return [
            event for event in events
            if geometry.covers(Point(float(event["longitude"]), float(event["latitude"])))
        ]
    except Exception as exc:
        print(f"Failed to filter events for operational unit {unit_id}: {exc}")
        return events
