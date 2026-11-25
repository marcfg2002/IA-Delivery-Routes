"""
Simulador de rutas de IA DELIVERY SL (esqueleto).

De momento muestra los pedidos pendientes sobre el mapa y permite fijar los
parámetros de la flota. El cálculo de rutas se conectará cuando esté el
optimizador (src/ia_delivery/optimizador.py).

Ejecutar desde la raíz del proyecto:
    streamlit run app/app.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ia_delivery.data import MATARO_LAT, MATARO_LON, build_orders, load_tables  # noqa: E402

st.set_page_config(page_title="IA DELIVERY · Simulador de rutas", page_icon="🚚", layout="wide")


# --- Datos -----------------------------------------------------------------
@st.cache_data
def cargar_pedidos() -> pd.DataFrame:
    """Una fila por pedido con unidades, distancia a Mataró y margen de caducidad."""
    tablas = load_tables(ROOT / "data" / "processed")
    pedidos = build_orders(tablas)
    provincias = tablas["Provincias"].set_index("IdProvincia")["Nombre"]
    pedidos["Provincia"] = pedidos["IdProvincia"].map(provincias)
    return pedidos


def cota_inferior_camiones(unidades_totales: float, capacidad: float) -> int:
    """Mínimo de viajes por capacidad, sin tener en cuenta distancias ni caducidad."""
    return math.ceil(unidades_totales / capacidad)


def crear_mapa(pedidos: pd.DataFrame, velocidad: float) -> folium.Map:
    mapa = folium.Map(location=[40.3, -2.6], zoom_start=6, tiles="OpenStreetMap")
    folium.Marker(
        [MATARO_LAT, MATARO_LON],
        tooltip="IA DELIVERY SL · Mataró",
        icon=folium.Icon(color="red", icon="industry", prefix="fa"),
    ).add_to(mapa)
    for p in pedidos.itertuples():
        horas = p.DistanciaKm / velocidad
        folium.CircleMarker(
            [p.Latitud, p.Longitud],
            radius=5,
            color="#2a78d6",
            fill=True,
            fill_opacity=0.8,
            tooltip=(f"Pedido {p.IdPedido} · {p.Provincia}<br>"
                     f"{p.Unidades:,.0f} uds · {p.DistanciaKm:.0f} km · {horas:.1f} h de ida".replace(",", ".")),
        ).add_to(mapa)
    return mapa


# --- Barra lateral: parámetros de la flota ----------------------------------
st.sidebar.header("Parámetros de la flota")
capacidad = st.sidebar.number_input(
    "Capacidad del camión (unidades)", min_value=1000, max_value=100000, value=20000, step=1000,
    help="Número de productos que caben en un camión. Todos los camiones son iguales.")
velocidad = st.sidebar.number_input(
    "Velocidad media (km/h)", min_value=30, max_value=120, value=80, step=5)
coste_km = st.sidebar.number_input(
    "Coste por kilómetro (€)", min_value=0.10, max_value=10.0, value=1.20, step=0.05, format="%.2f")
calcular = st.sidebar.button("Calcular rutas", type="primary", use_container_width=True)

# --- Contenido -------------------------------------------------------------
st.title("🚚 IA DELIVERY · Simulador de rutas")
st.caption("Pedidos pendientes desde la sede de Mataró. Base de datos final (MySQL).")

pedidos = cargar_pedidos()

if calcular:
    st.info("El optimizador de rutas todavía no está conectado. De momento se muestran solo los pedidos.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pedidos", len(pedidos))
c2.metric("Destinos", pedidos["IdDestino"].nunique())
c3.metric("Unidades totales", f"{pedidos['Unidades'].sum():,.0f}".replace(",", "."))
c4.metric("Camiones (mínimo por capacidad)", cota_inferior_camiones(pedidos["Unidades"].sum(), capacidad),
          help="Cota inferior: unidades totales / capacidad. El número real será mayor por distancias y caducidad.")

col_mapa, col_tabla = st.columns([3, 2])
with col_mapa:
    st.subheader("Mapa de pedidos")
    st_folium(crear_mapa(pedidos, velocidad), height=520, use_container_width=True, returned_objects=[])
with col_tabla:
    st.subheader("Pedidos")
    tabla = pedidos.assign(
        HorasIda=(pedidos["DistanciaKm"] / velocidad).round(1),
        CosteIdaVuelta=(2 * pedidos["DistanciaKm"] * coste_km).round(0),
    )[["IdPedido", "Provincia", "Unidades", "DistanciaKm", "HorasIda", "CosteIdaVuelta", "MargenJITDias"]]
    st.dataframe(
        tabla, hide_index=True, height=520,
        column_config={
            "DistanciaKm": st.column_config.NumberColumn("Distancia (km)", format="%.0f"),
            "HorasIda": st.column_config.NumberColumn("Horas de ida"),
            "CosteIdaVuelta": st.column_config.NumberColumn("Coste ida y vuelta (€)", format="%.0f",
                                                            help="Si el pedido fuera solo en un camión"),
            "MargenJITDias": st.column_config.NumberColumn("Margen caducidad (días)"),
        },
    )
