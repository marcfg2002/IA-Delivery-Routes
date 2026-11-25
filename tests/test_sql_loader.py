"""Pruebas unitarias de la carga de la BBDD BDIADelivery (final en MySQL e inicial en SQL Server)."""
import hashlib
import re
from pathlib import Path

import pytest

from ia_delivery.sql_loader import (
    decode_geography_point,
    decode_mysql_point,
    detect_format,
    parse_sql_dump,
)

ROOT = Path(__file__).resolve().parents[1]
SQL_FINAL = ROOT / "data" / "raw" / "BDIADelivery_MySQL.sql"
SQL_INICIAL = ROOT / "data" / "raw" / "obsoleta" / "BDIADelivery_SQLServer_inicial.sql"

# Huellas de los scripts tal y como nos los dieron los profesores
MD5_FINAL = "7cbe7c377bef1684c88362c586edda11"
MD5_INICIAL = "fdc1a38dcbdeaaa89fbc12a232668b0b"

FILAS = {"Clientes": 500, "Destinos": 1500, "LineasPedido": 17689,
         "Pedidos": 133, "Productos": 10000, "Provincias": 47}


@pytest.fixture(scope="module")
def final():
    return parse_sql_dump(SQL_FINAL)


@pytest.fixture(scope="module")
def inicial():
    return parse_sql_dump(SQL_INICIAL)


# --- BBDD final (MySQL) --------------------------------------------------------

def test_script_final_sin_modificar():
    assert hashlib.md5(SQL_FINAL.read_bytes()).hexdigest() == MD5_FINAL


def test_detecta_formatos():
    assert detect_format(SQL_FINAL) == "mysql"
    assert detect_format(SQL_INICIAL) == "mssql"


def test_final_numero_de_filas(final):
    assert {k: len(v) for k, v in final.items()} == FILAS


def test_final_sin_nulos(final):
    for nombre, df in final.items():
        assert df.isna().sum().sum() == 0, nombre


def test_decodifica_point_mysql():
    lat, lon = decode_mysql_point(
        "ST_GeomFromText('POINT(-2.6415380 42.8480803)', 4326, 'axis-order=long-lat')")
    assert (lat, lon) == (42.8480803, -2.6415380)


def test_final_coordenadas_coinciden(final):
    # En la BBDD final la columna Coordenadas sí coincide con Latitud/Longitud
    d = final["Destinos"]
    assert ((d["Latitud"] - d["GeoLatitud"]).abs() < 1e-6).all()
    assert ((d["Longitud"] - d["GeoLongitud"]).abs() < 1e-6).all()


def test_final_latitud_longitud_iguales_al_script(final):
    with open(SQL_FINAL, encoding="utf-8") as fh:
        lineas = iter(fh)
        next(l for l in lineas if l.startswith("INSERT INTO Destinos"))
        primera = next(lineas)
    lat, lon = map(float, re.match(r"\(1,'[^']*','[^']*',\d+,'[^']*','\d+',([-\d.]+),([-\d.]+),", primera).groups())
    d1 = final["Destinos"].iloc[0]
    assert (d1["Latitud"], d1["Longitud"]) == (lat, lon)


def test_final_coordenadas_en_la_peninsula(final):
    d = final["Destinos"]
    assert d["Latitud"].between(35.9, 43.9).all()
    assert d["Longitud"].between(-9.5, 3.4).all()


# --- BBDD inicial (SQL Server, obsoleta) --------------------------------------
# Se conserva para poder reproducir el problema que detectamos con las coordenadas.

def test_script_inicial_sin_modificar():
    assert hashlib.md5(SQL_INICIAL.read_bytes()).hexdigest() == MD5_INICIAL


def test_inicial_numero_de_filas(inicial):
    assert {k: len(v) for k, v in inicial.items()} == FILAS


def test_decodifica_geography_sqlserver():
    lat, lon = decode_geography_point("0xE6100000010C5083F1030010454098194018957D1BC0")
    assert lat == pytest.approx(42.1250005, abs=1e-6)
    assert lon == pytest.approx(-6.8726391, abs=1e-6)


def test_inicial_coordenadas_no_coinciden(inicial):
    # El problema que encontramos: en la BBDD inicial Coordenadas != Latitud/Longitud
    d = inicial["Destinos"]
    distinto = ((d["Latitud"] - d["GeoLatitud"]).abs() > 1e-4) | ((d["Longitud"] - d["GeoLongitud"]).abs() > 1e-4)
    assert distinto.all()
