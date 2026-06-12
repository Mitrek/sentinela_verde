from __future__ import annotations

import operational_units


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
