from __future__ import annotations

from sentinela_verde.geo import operational_units
from sentinela_verde.geo.areas import _normalize_name, get_municipality_names, load_areas


def test_parse_units_aggregates_hierarchy_and_municipality_lists(monkeypatch):
    monkeypatch.setattr(
        operational_units,
        "get_municipality_names",
        lambda: ["Belo Horizonte", "Nova Lima", "Raposos", "Rio Acima"],
    )
    text = """
    COB UEOp CIA Pelotão RISP Municípios/bairros da área de atuação
    1º COMANDO OPERACIONAL DE BOMBEIROS
    BELO HORIZONTE
    1° BATALHÃO DE BOMBEIROS MILITAR
    BELO HORIZONTE
    1ª Cia BM
    Belo Horizonte
    1° ao 4° Pel BM
    Sede
    1ª RISP
    Belo Horizonte
    Municípios: Nova Lima, Raposos e Rio Acima. (03)
    """

    units = operational_units._parse_units_from_text(text)
    cob = next(unit for unit in units if unit["type"] == "cob")
    platoon = next(unit for unit in units if unit["type"] == "pelotao")

    assert set(cob["municipios"]) == {"Rio Acima", "Raposos", "Nova Lima"}
    assert set(platoon["direct_municipios"]) == {"Rio Acima", "Raposos", "Nova Lima"}


def test_parse_units_converts_neighborhood_division_to_municipality(monkeypatch):
    monkeypatch.setattr(
        operational_units,
        "get_municipality_names",
        lambda: ["Belo Horizonte", "Contagem"],
    )
    text = """
    1º COMANDO OPERACIONAL DE BOMBEIROS
    BELO HORIZONTE
    2º BATALHÃO DE BOMBEIROS MILITAR
    CONTAGEM
    1ª Cia BM
    Contagem
    5º Pel BM
    CEASA
    2ª RISP
    Contagem
    Bairros de Contagem: Bom Jesus, Caiapós. (02)
    Bairros de Belo Horizonte: Conjunto Confisco. (01)
    """

    units = operational_units._parse_units_from_text(text)
    platoon = next(unit for unit in units if unit["type"] == "pelotao")

    assert platoon["direct_municipios"] == ["Contagem", "Belo Horizonte"]
    assert platoon["uses_municipality_fallback"] is True


def test_parse_units_avoids_short_name_inside_long_municipality(monkeypatch):
    monkeypatch.setattr(
        operational_units,
        "get_municipality_names",
        lambda: ["Bicas", "São Joaquim de Bicas"],
    )
    text = """
    1º COMANDO OPERACIONAL DE BOMBEIROS
    BELO HORIZONTE
    2º BATALHÃO DE BOMBEIROS MILITAR
    CONTAGEM
    1ª Cia BM
    Contagem
    6° Pel BM
    Juatuba
    2ª RISP
    Contagem
    Município: São Joaquim de Bicas. (01)
    """

    units = operational_units._parse_units_from_text(text)
    platoon = next(unit for unit in units if unit["type"] == "pelotao")

    assert platoon["direct_municipios"] == ["São Joaquim de Bicas"]


def test_parse_units_finds_short_name_after_long_name_overlap(monkeypatch):
    monkeypatch.setattr(
        operational_units,
        "get_municipality_names",
        lambda: ["Caparaó", "Alto Caparaó", "Porteirinha", "Nova Porteirinha"],
    )
    text = """
    1º COMANDO OPERACIONAL DE BOMBEIROS
    BELO HORIZONTE
    1° BATALHÃO DE BOMBEIROS MILITAR
    BELO HORIZONTE
    1ª Cia BM
    Belo Horizonte
    1° Pel BM
    Sede
    Municípios: Alto Caparaó, Caparaó, Nova Porteirinha, Porteirinha. (04)
    """

    units = operational_units._parse_units_from_text(text)
    platoon = next(unit for unit in units if unit["type"] == "pelotao")

    assert set(platoon["direct_municipios"]) == {
        "Alto Caparaó",
        "Caparaó",
        "Nova Porteirinha",
        "Porteirinha",
    }


def test_parse_units_formats_operational_names_as_natural_text(monkeypatch):
    monkeypatch.setattr(
        operational_units,
        "get_municipality_names",
        lambda: ["Belo Horizonte"],
    )
    text = """
    1º COMANDO OPERACIONAL DE BOMBEIROS
    BELO HORIZONTE
    1° BATALHÃO DE BOMBEIROS MILITAR
    BELO HORIZONTE
    1ª Cia BM
    Belo Horizonte
    1° Pel BM
    Sede
    Municípios: Belo Horizonte. (01)
    """

    units = operational_units._parse_units_from_text(text)

    assert next(unit for unit in units if unit["type"] == "cob")["name"] == "1º Comando Operacional de Bombeiros - Belo Horizonte"
    assert next(unit for unit in units if unit["type"] == "batalhao")["name"] == "1° Batalhão de Bombeiros Militar - Belo Horizonte"


def test_parse_units_matches_source_text_municipality_variants(monkeypatch):
    municipality_names = [
        "Barão do Monte Alto",
        "Brazópolis",
        "Cachoeira de Pajeú",
        "Olhos-d'Água",
        "Pingo-d'Água",
        "Prudente de Morais",
        "Ribeirão das Neves",
        "São Gonçalo do Abaeté",
    ]
    monkeypatch.setattr(
        operational_units,
        "get_municipality_names",
        lambda: municipality_names,
    )
    text = """
    1º COMANDO OPERACIONAL DE BOMBEIROS
    BELO HORIZONTE
    1° BATALHÃO DE BOMBEIROS MILITAR
    BELO HORIZONTE
    1ª Cia BM
    Belo Horizonte
    1° Pel BM
    Sede
    Municípios: Barão de Monte Alto, Brasópolis, Cachoeira do Pajeú,
    Olhos D’água, Pingo-d’água, Prudente de Moraes,
    Ribeirão das Neves1, São Gonçalo do Abaeté3. (08)
    """

    units = operational_units._parse_units_from_text(text)
    platoon = next(unit for unit in units if unit["type"] == "pelotao")

    assert set(platoon["direct_municipios"]) == set(municipality_names)


def test_real_operational_cobs_cover_all_mg_municipalities():
    all_municipalities = {_normalize_name(name) for name in get_municipality_names()}
    assert len(all_municipalities) == 853

    area_union = {
        _normalize_name(municipio)
        for area in load_areas()
        for municipio in area.get("municipios", [])
    }
    assert area_union == all_municipalities

    expected_counts = {
        "1COB": 119,
        "2COB": 93,
        "3COB": 146,
        "4COB": 115,
        "5COB": 221,
        "6COB": 159,
    }
    areas_by_number = {
        "".join(char for char in area["id"] if char.isdigit()): area
        for area in load_areas()
    }

    top_level_cobs = [
        unit
        for unit in operational_units.load_operational_units()
        if unit["type"] == "cob" and unit["parent_id"] is None
    ]
    operational_union = set()
    for cob in top_level_cobs:
        cob_number = cob["name"].split("º", 1)[0]
        area = areas_by_number[cob_number]
        municipios = {_normalize_name(name) for name in cob["municipios"]}
        operational_union.update(municipios)

        assert len(municipios) == expected_counts[area["id"]]
        assert municipios == {_normalize_name(name) for name in area["municipios"]}

    assert operational_union == all_municipalities


def test_get_operational_units_features_deduplicates_municipality_union(monkeypatch):
    monkeypatch.setattr(
        operational_units,
        "_UNITS_BY_ID_CACHE",
        {
            "unit-a": {"id": "unit-a", "municipios": ["Belo Horizonte", "Nova Lima"]},
            "unit-b": {"id": "unit-b", "municipios": ["Nova Lima", "Raposos"]},
        },
    )
    monkeypatch.setattr(
        operational_units,
        "get_municipality_features",
        lambda municipios: [{"name": name} for name in municipios],
    )

    features = operational_units.get_operational_units_features(["unit-a", "unit-b"])

    assert features == [
        {"name": "Belo Horizonte"},
        {"name": "Nova Lima"},
        {"name": "Raposos"},
    ]
