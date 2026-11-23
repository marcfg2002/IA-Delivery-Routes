"""
Carga del script SQL Server (BDIADelivery) a tablas de pandas / CSV.

El script entregado en clase es un volcado de SQL Server (T-SQL) con sentencias
`INSERT [dbo].[Tabla] (...) VALUES (...)`. Para no depender de tener un SQL
Server instalado, este módulo parsea directamente esos INSERT y genera un CSV
por tabla en `data/processed/`. El script original (data/raw/) solo se lee: nunca
se modifica.

Uso:
    python -m ia_delivery.sql_loader data/raw/BDIADelivery_script.sql data/processed
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

import pandas as pd

# INSERT [dbo].[Tabla] ([Col1], [Col2]) VALUES (v1, v2)
INSERT_RE = re.compile(
    r"^INSERT \[dbo\]\.\[(?P<table>\w+)\] \((?P<cols>.*?)\) VALUES \((?P<vals>.*)\)\s*$"
)
# CAST(N'2026-11-18T19:53:33.360' AS DateTime) / CAST(11.92 AS Decimal(10, 2))
CAST_RE = re.compile(r"^CAST\((?P<inner>.+?) AS [\w ]+(\(\s*\d+\s*(,\s*\d+\s*)?\))?\)$")


def _split_values(raw: str) -> list[str]:
    """Separa la lista de valores por comas, respetando comillas y paréntesis."""
    out, buf, depth, in_str = [], [], 0, False
    i = 0
    while i < len(raw):
        c = raw[i]
        if in_str:
            buf.append(c)
            if c == "'":
                # comilla escapada ('')
                if i + 1 < len(raw) and raw[i + 1] == "'":
                    buf.append("'")
                    i += 1
                else:
                    in_str = False
        elif c == "'":
            in_str = True
            buf.append(c)
        elif c == "(":
            depth += 1
            buf.append(c)
        elif c == ")":
            depth -= 1
            buf.append(c)
        elif c == "," and depth == 0:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        out.append("".join(buf).strip())
    return out


def _parse_value(token: str):
    """Convierte un literal T-SQL a un valor Python."""
    if token.upper() == "NULL":
        return None
    m = CAST_RE.match(token)
    if m:
        token = m.group("inner").strip()
    if token.startswith("N'"):
        token = token[1:]
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    if token.startswith("0x"):  # binarios (columna geography): se guardan en hex y se descodifican luego
        return token
    try:
        return int(token)
    except ValueError:
        return float(token)


def decode_geography_point(hex_value: str | None) -> tuple[float, float] | tuple[None, None]:
    """
    Descodifica un punto del tipo geography de SQL Server (formato binario nativo).

    Estructura de un punto simple: SRID (4 bytes, 4326 = WGS84) + versión (1 byte)
    + propiedades (1 byte) + latitud (double) + longitud (double), little-endian.
    """
    if not hex_value:
        return (None, None)
    raw = bytes.fromhex(hex_value[2:] if hex_value.startswith("0x") else hex_value)
    srid = struct.unpack("<i", raw[0:4])[0]
    if srid != 4326 or len(raw) < 22:
        raise ValueError(f"Formato geography no esperado (SRID={srid}, {len(raw)} bytes)")
    lat, lon = struct.unpack("<dd", raw[6:22])
    return (lat, lon)


def parse_sql_dump(path: str | Path) -> dict[str, pd.DataFrame]:
    """Devuelve {nombre_tabla: DataFrame} a partir del script SQL."""
    rows: dict[str, list[dict]] = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = INSERT_RE.match(line.strip())
            if not m:
                continue
            cols = [c.strip(" []") for c in m.group("cols").split(",")]
            vals = [_parse_value(v) for v in _split_values(m.group("vals"))]
            rows.setdefault(m.group("table"), []).append(dict(zip(cols, vals)))

    tables = {t: pd.DataFrame(r) for t, r in rows.items()}
    # La columna Coordenadas (geography) NO coincide con Latitud/Longitud en ningún destino
    # (ver docs). No la descartamos: la guardamos descodificada en GeoLatitud/GeoLongitud
    # por si el profesor indica que es la buena. El cálculo de rutas usa Latitud/Longitud.
    if "Destinos" in tables and "Coordenadas" in tables["Destinos"]:
        geo = tables["Destinos"]["Coordenadas"].map(decode_geography_point)
        tables["Destinos"]["GeoLatitud"] = geo.str[0]
        tables["Destinos"]["GeoLongitud"] = geo.str[1]
        tables["Destinos"] = tables["Destinos"].drop(columns=["Coordenadas"])
    if "Pedidos" in tables:
        tables["Pedidos"]["FechaPedido"] = pd.to_datetime(tables["Pedidos"]["FechaPedido"])
    return tables


def export_csv(tables: dict[str, pd.DataFrame], out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
        print(f"  {name:<14} {len(df):>7} filas -> {out / (name + '.csv')}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/raw/BDIADelivery_script.sql"
    dst = sys.argv[2] if len(sys.argv) > 2 else "data/processed"
    print(f"Parseando {src} ...")
    export_csv(parse_sql_dump(src), dst)
