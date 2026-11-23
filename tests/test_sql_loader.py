"""Pruebas unitarias de la carga del script SQL de la BBDD BDIADelivery."""
import hashlib
import re
from pathlib import Path

import pytest

from ia_delivery.sql_loader import decode_geography_point, parse_sql_dump

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "data" / "raw" / "BDIADelivery_script.sql"
MD5_ORIGINAL = "fdc1a38dcbdeaaa89fbc12a232668b0b"  # script tal y como lo dieron los profesores


@pytest.fixture(scope="module")
def tables():
    return parse_sql_dump(SQL)


def test_script_original_sin_modificar():
    assert hashlib.md5(SQL.read_bytes()).hexdigest() == MD5_ORIGINAL


def test_numero_de_filas(tables):
    esperado = {"Clientes": 500, "Destinos": 1500, "LineasPedido": 17689,
                "Pedidos": 133, "Productos": 10000, "Provincias": 47}
    assert {k: len(v) for k, v in tables.items()} == esperado


def test_sin_nulos(tables):
    for nombre, df in tables.items():
        assert df.isna().sum().sum() == 0, nombre


def test_decodifica_geography():
    # Destino 1 del script: 0xE6100000010C5083F1030010454098194018957D1BC0
    lat, lon = decode_geography_point("0xE6100000010C5083F1030010454098194018957D1BC0")
    assert lat == pytest.approx(42.1250005, abs=1e-6)
    assert lon == pytest.approx(-6.8726391, abs=1e-6)


def test_latitud_longitud_iguales_al_script(tables):
    # Comparamos con el texto literal del primer INSERT de Destinos
    with open(SQL, encoding="utf-8") as fh:
        linea = next(l for l in fh if l.startswith("INSERT [dbo].[Destinos]"))
    lat, lon = map(float, re.findall(r"CAST\(([-\d.]+) AS Decimal", linea))
    d1 = tables["Destinos"].iloc[0]
    assert (d1["Latitud"], d1["Longitud"]) == (lat, lon)
