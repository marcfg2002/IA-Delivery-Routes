"""
Carga de la base de datos BDIADelivery a tablas de pandas / CSV.

Soporta los dos formatos que nos han dado los profesores:

- **MySQL** (BBDD final, `data/raw/BDIADelivery_MySQL.sql`): sentencias
  `INSERT INTO Tabla (...) VALUES` con una fila por línea y la columna
  `Coordenadas` como `ST_GeomFromText('POINT(lon lat)', 4326, ...)`.
- **SQL Server** (BBDD inicial, ya retirada del repositorio): sentencias
  `INSERT [dbo].[Tabla] (...) VALUES (...)` con la columna geography en binario.

El formato se detecta solo. Para no depender de tener MySQL o SQL Server
instalados, se parsean directamente los INSERT y se genera un CSV por tabla en
`data/processed/`. El script original solo se lee: nunca se modifica.

Uso:
    python -m ia_delivery.sql_loader data/raw/BDIADelivery_MySQL.sql data/processed
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

import pandas as pd

DEFAULT_SQL = "data/raw/BDIADelivery_MySQL.sql"

# --- SQL Server ------------------------------------------------------------
# INSERT [dbo].[Tabla] ([Col1], [Col2]) VALUES (v1, v2)
MSSQL_INSERT_RE = re.compile(
    r"^INSERT \[dbo\]\.\[(?P<table>\w+)\] \((?P<cols>.*?)\) VALUES \((?P<vals>.*)\)\s*$"
)
# CAST(N'2026-11-18T19:53:33.360' AS DateTime) / CAST(11.92 AS Decimal(10, 2))
CAST_RE = re.compile(r"^CAST\((?P<inner>.+?) AS [\w ]+(\(\s*\d+\s*(,\s*\d+\s*)?\))?\)$")

# --- MySQL -----------------------------------------------------------------
# INSERT INTO Tabla (Col1, Col2) VALUES      <- cabecera; las filas van en las líneas siguientes
MYSQL_INSERT_RE = re.compile(r"^INSERT INTO `?(?P<table>\w+)`? \((?P<cols>[^)]*)\) VALUES\s*$")
# ST_GeomFromText('POINT(-2.6415380 42.8480803)', 4326, 'axis-order=long-lat')
POINT_RE = re.compile(r"^ST_GeomFromText\('POINT\((?P<x>[-\d.]+) (?P<y>[-\d.]+)\)'(?P<rest>.*)\)$")


def _split_values(raw: str) -> list[str]:
    """Separa la lista de valores por comas, respetando comillas y paréntesis."""
    out, buf, depth, in_str = [], [], 0, False
    i = 0
    while i < len(raw):
        c = raw[i]
        if in_str:
            buf.append(c)
            if c == "\\" and i + 1 < len(raw):  # escape tipo MySQL (\')
                buf.append(raw[i + 1])
                i += 1
            elif c == "'":
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
    """Convierte un literal SQL (T-SQL o MySQL) a un valor Python."""
    if token.upper() == "NULL":
        return None
    m = CAST_RE.match(token)
    if m:
        token = m.group("inner").strip()
    m = POINT_RE.match(token)
    if m:  # MySQL: POINT(x y). Se devuelve tal cual y se interpreta en _decode_mysql_point
        return token
    if token.startswith("N'"):
        token = token[1:]
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'").replace("\\'", "'")
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


def decode_mysql_point(value: str | None) -> tuple[float, float] | tuple[None, None]:
    """
    Descodifica ST_GeomFromText('POINT(x y)', 4326, 'axis-order=...') de MySQL.

    Devuelve siempre (latitud, longitud). Con 'axis-order=long-lat' el punto se
    escribe como POINT(longitud latitud); si no se indica, MySQL usa lat-long
    para el SRID 4326.
    """
    if not value:
        return (None, None)
    m = POINT_RE.match(value)
    if not m:
        raise ValueError(f"Punto MySQL no reconocido: {value[:60]}")
    x, y = float(m.group("x")), float(m.group("y"))
    return (y, x) if "long-lat" in m.group("rest") else (x, y)


def _read_mssql(path: Path) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = MSSQL_INSERT_RE.match(line.strip())
            if not m:
                continue
            cols = [c.strip(" []") for c in m.group("cols").split(",")]
            vals = [_parse_value(v) for v in _split_values(m.group("vals"))]
            rows.setdefault(m.group("table"), []).append(dict(zip(cols, vals)))
    return rows


def _read_mysql(path: Path) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {}
    table, cols = None, None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            m = MYSQL_INSERT_RE.match(line)
            if m:
                table = m.group("table")
                cols = [c.strip(" `") for c in m.group("cols").split(",")]
                continue
            if table and line.startswith("("):
                body = line.rstrip(",;").strip()[1:-1]  # quitar coma/punto y coma final y paréntesis
                vals = [_parse_value(v) for v in _split_values(body)]
                if len(vals) != len(cols):
                    raise ValueError(f"{table}: {len(vals)} valores para {len(cols)} columnas: {line[:80]}")
                rows.setdefault(table, []).append(dict(zip(cols, vals)))
                if line.endswith(";"):
                    table = None
            elif table and not line.startswith("("):
                table = None
    return rows


def detect_format(path: str | Path) -> str:
    """'mysql' o 'mssql' según cómo están escritos los INSERT."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("INSERT [dbo]."):
                return "mssql"
            if line.startswith("INSERT INTO"):
                return "mysql"
    raise ValueError(f"No se reconoce el formato de {path}")


def parse_sql_dump(path: str | Path) -> dict[str, pd.DataFrame]:
    """Devuelve {nombre_tabla: DataFrame} a partir del script SQL (MySQL o SQL Server)."""
    path = Path(path)
    fmt = detect_format(path)
    rows = _read_mysql(path) if fmt == "mysql" else _read_mssql(path)
    tables = {t: pd.DataFrame(r) for t, r in rows.items()}

    # La columna Coordenadas se guarda descodificada en GeoLatitud/GeoLongitud para poder
    # comprobar que cuadra con Latitud/Longitud (en la BBDD inicial NO cuadraba; ver docs).
    # El cálculo de rutas usa Latitud/Longitud.
    if "Destinos" in tables and "Coordenadas" in tables["Destinos"]:
        decode = decode_mysql_point if fmt == "mysql" else decode_geography_point
        geo = tables["Destinos"]["Coordenadas"].map(decode)
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
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SQL
    dst = sys.argv[2] if len(sys.argv) > 2 else "data/processed"
    print(f"Parseando {src} ({detect_format(src)}) ...")
    export_csv(parse_sql_dump(src), dst)
