"""
Carga de las tablas procesadas y cálculo de las magnitudes básicas de cada pedido.

Funciones principales:
    load_tables()          -> dict con los DataFrames de data/processed
    haversine_km()         -> distancia en línea recta entre coordenadas GPS
    build_orders()         -> una fila por pedido con unidades, fechas y distancia a Mataró
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"

# Sede central de IA DELIVERY SL (Mataró, Barcelona)
MATARO_LAT, MATARO_LON = 41.5381, 2.4445

# "Partimos de la base de que al día siguiente de recibir un pedido se empieza a fabricar"
DIAS_HASTA_INICIO_FABRICACION = 1

TABLES = ["Clientes", "Destinos", "LineasPedido", "Pedidos", "Productos", "Provincias"]


def load_tables(data_dir: str | Path = PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Lee los CSV generados por sql_loader."""
    data_dir = Path(data_dir)
    tables = {t: pd.read_csv(data_dir / f"{t}.csv") for t in TABLES}
    tables["Pedidos"]["FechaPedido"] = pd.to_datetime(tables["Pedidos"]["FechaPedido"])
    return tables


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia ortodrómica (línea recta sobre la esfera) en km. Acepta escalares o arrays."""
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def build_orders(
    tables: dict[str, pd.DataFrame],
    dias_inicio_fabricacion: int = DIAS_HASTA_INICIO_FABRICACION,
) -> pd.DataFrame:
    """
    Devuelve una fila por pedido con:
      - NumLineas, Unidades                      tamaño del pedido (capacidad del camión)
      - FechaListo                               cuando está fabricado el último producto
                                                 = FechaPedido + inicio + max(TiempoFabricacion)
      - FechaCaducidad                           min por producto de
                                                 FechaPedido + inicio + TiempoFabricacion + CaducidadDias
      - MargenDias                               FechaCaducidad - FechaListo: tiempo máximo de reparto
                                                 (interpretación literal del enunciado)
      - MargenJITDias                            tiempo máximo de reparto si la fabricación se
                                                 planifica para que todo termine a la vez
      - DistanciaKm                              línea recta Mataró -> destino
    """
    lineas = tables["LineasPedido"].merge(tables["Productos"], on="IdProducto", how="left")
    pedidos = tables["Pedidos"].set_index("IdPedido")

    lineas = lineas.join(pedidos["FechaPedido"], on="IdPedido")
    inicio = lineas["FechaPedido"] + pd.to_timedelta(dias_inicio_fabricacion, unit="D")
    lineas["FechaListo"] = inicio + pd.to_timedelta(lineas["TiempoFabricacionMedioDias"], unit="D")
    lineas["FechaCaducidad"] = lineas["FechaListo"] + pd.to_timedelta(lineas["CaducidadDias"], unit="D")
    lineas["Importe"] = lineas["Cantidad"] * lineas["PrecioVenta"]

    agg = lineas.groupby("IdPedido").agg(
        NumLineas=("NumeroLinea", "count"),
        Unidades=("Cantidad", "sum"),
        Importe=("Importe", "sum"),
        FechaListo=("FechaListo", "max"),
        FechaCaducidad=("FechaCaducidad", "min"),
        CaducidadMinDias=("CaducidadDias", "min"),
    )
    orders = pedidos.join(agg)
    # Interpretación literal: todo se empieza a fabricar a la vez y el camión sale cuando acaba el último
    orders["MargenDias"] = (orders["FechaCaducidad"] - orders["FechaListo"]).dt.total_seconds() / 86400
    # Interpretación "just in time": cada producto se fabrica para terminar a la vez que el más lento,
    # así que al salir ningún producto ha empezado a caducar -> margen = caducidad más corta del pedido
    orders["MargenJITDias"] = orders["CaducidadMinDias"].astype(float)

    dest = tables["Destinos"].set_index("IdDestino")
    orders = orders.join(dest[["Ciudad", "Pais", "IdProvincia", "Latitud", "Longitud"]], on="IdDestino")
    orders["DistanciaKm"] = haversine_km(MATARO_LAT, MATARO_LON, orders["Latitud"], orders["Longitud"])
    return orders.reset_index()
