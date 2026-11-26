"""
Simulador de rutas de IA DELIVERY SL.

Muestra los pedidos pendientes sobre el mapa y permite fijar los parámetros de
la flota. El cálculo de rutas se conectará cuando esté el optimizador
(src/ia_delivery/optimizador.py).

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

st.set_page_config(page_title="Planificador de rutas · IA DELIVERY", page_icon="🚚", layout="wide")

# --- Paleta (cadena de frío) ---------------------------------------------------
PETROLEO = "#12343B"   # texto
RUTA = "#0E7C86"       # color principal
HIELO = "#F3F6F7"      # fondo
LINEA = "#D5DEE0"      # bordes y líneas
CADUCIDAD = "#D99A00"  # solo para lo relacionado con caducidad
# Escala de distancia a Mataró (de cerca a lejos), del turquesa claro al petróleo
ESCALA_DISTANCIA = [(250, "#7FD1D6"), (500, "#2FA7B0"), (750, "#0E7C86"), (10_000, "#0B4F58")]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=Public+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, p, label, input, button {{
    font-family: 'Public Sans', sans-serif;
}}
h1, h2, h3, h4, .titular {{ font-family: 'Archivo', sans-serif; letter-spacing: -0.01em; }}
.block-container {{ padding-top: 2.2rem; max-width: 1280px; }}

/* Cabecera */
.cabecera {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }}
.cabecera h1 {{ font-size: 2.6rem; font-weight: 800; color: {PETROLEO}; margin: 0; padding: 0; line-height: 1.05; }}
.cabecera p {{ color: #4E6A70; margin: .35rem 0 0; font-size: 1rem; }}
.sello {{ border: 1.5px solid {PETROLEO}; border-radius: 999px; padding: .3rem .8rem;
          font-size: .85rem; color: {PETROLEO}; white-space: nowrap; }}

/* Tira de expedición: las cifras como paradas de una ruta */
.tira {{ position: relative; display: grid; grid-template-columns: repeat(5, 1fr);
         margin: 2rem 0 1.6rem; }}
.tira::before {{ content: ""; position: absolute; left: 10%; right: 10%; top: 13px;
                 border-top: 3px dashed {RUTA}; }}
.parada {{ position: relative; text-align: center; padding: 0 .5rem; }}
.parada .punto {{ width: 22px; height: 22px; border-radius: 50%; margin: 3px auto .7rem;
                  background: {HIELO}; border: 4px solid {RUTA}; position: relative; z-index: 1; box-sizing: border-box; }}
.parada.origen .punto {{ background: {PETROLEO}; border-color: {PETROLEO}; width: 28px; height: 28px; margin-top: 0;
                         border-radius: 4px; transform: rotate(45deg) scale(.8); }}
.parada .valor {{ font-family: 'Archivo', sans-serif; font-weight: 800; font-size: 2rem;
                  color: {PETROLEO}; line-height: 1; }}
.parada .que {{ color: #4E6A70; font-size: .9rem; margin-top: .3rem; }}
.parada.final .valor {{ color: {RUTA}; }}
.parada.final .punto {{ background: {RUTA}; }}
.parada .nota {{ color: #7A9196; font-size: .78rem; margin-top: .15rem; }}
@media (max-width: 760px) {{
  .tira {{ grid-template-columns: repeat(2, 1fr); row-gap: 1.4rem; }}
  .tira::before {{ display: none; }}
}}

/* Barra lateral */
section[data-testid="stSidebar"] {{ background: {PETROLEO}; }}
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .lateral-titulo, section[data-testid="stSidebar"] .lateral-texto {{ color: #E8F1F2; }}
section[data-testid="stSidebar"] .stButton button {{
    background: {RUTA}; border: none; color: white; font-weight: 600; padding: .65rem 1rem; }}
section[data-testid="stSidebar"] .stButton button:hover {{ background: #0B6870; color: white; }}
section[data-testid="stSidebar"] .stButton button p {{ color: white; }}
.lateral-titulo {{ font-family: 'Archivo', sans-serif; font-weight: 700; font-size: 1.3rem; margin-bottom: .2rem; }}
.lateral-texto {{ font-size: .88rem; opacity: .8; margin-bottom: 1.2rem; }}

/* Pestañas */
.stTabs [data-baseweb="tab-list"] {{ gap: 1.6rem; border-bottom: 1px solid {LINEA}; }}
.stTabs [data-baseweb="tab"] p {{ font-family: 'Archivo', sans-serif; font-weight: 700; font-size: 1rem; }}

/* Leyenda del mapa */
.leyenda {{ display: flex; gap: 1.2rem; flex-wrap: wrap; font-size: .85rem; color: #4E6A70; margin: .2rem 0 .8rem; }}
.leyenda span {{ display: inline-flex; align-items: center; gap: .4rem; }}
.leyenda i {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}

/* Aviso de caducidad */
.caducidad {{ border-left: 4px solid {CADUCIDAD}; background: #FFF8E6; padding: .8rem 1rem;
              border-radius: 0 6px 6px 0; font-size: .92rem; color: #5A4300; margin-top: 1rem; max-width: 70ch; }}
.como {{ max-width: 70ch; }}

:focus-visible {{ outline: 2px solid {CADUCIDAD} !important; outline-offset: 2px; }}
</style>
"""


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


def miles(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def color_distancia(km: float) -> str:
    return next(color for limite, color in ESCALA_DISTANCIA if km < limite)


def crear_mapa(pedidos: pd.DataFrame, velocidad: float) -> folium.Map:
    mapa = folium.Map(location=[40.3, -2.6], zoom_start=6, tiles=None)
    folium.TileLayer("OpenStreetMap", name="Mapa").add_to(mapa)
    # Fondo en grises para que destaquen los pedidos
    mapa.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tile-pane{filter:grayscale(1) brightness(1.08) contrast(.85) opacity(.8);}</style>"))

    # Mataró: un rombo petróleo, distinto de los pedidos
    folium.Marker(
        [MATARO_LAT, MATARO_LON],
        tooltip="Sede de IA DELIVERY SL (Mataró)",
        icon=folium.DivIcon(
            icon_size=(22, 22), icon_anchor=(11, 11),
            html=(f'<div style="width:16px;height:16px;background:{PETROLEO};transform:rotate(45deg);'
                  f'border:3px solid white;box-shadow:0 0 0 2px {PETROLEO};"></div>'),
        ),
    ).add_to(mapa)

    u_min, u_max = pedidos["Unidades"].min(), pedidos["Unidades"].max()
    for p in pedidos.sort_values("DistanciaKm", ascending=False).itertuples():
        radio = 5 + 7 * (p.Unidades - u_min) / (u_max - u_min)  # tamaño según unidades
        folium.CircleMarker(
            [p.Latitud, p.Longitud], radius=radio, color="white", weight=1.5,
            fill=True, fill_color=color_distancia(p.DistanciaKm), fill_opacity=0.9,
            tooltip=folium.Tooltip(
                f"<b>Pedido {p.IdPedido}</b>, {p.Provincia}<br>"
                f"{miles(p.Unidades)} unidades<br>"
                f"{p.DistanciaKm:.0f} km, {p.DistanciaKm / velocidad:.1f} h de ida"),
        ).add_to(mapa)
    return mapa


st.markdown(CSS, unsafe_allow_html=True)

# --- Barra lateral: la flota ---------------------------------------------------
with st.sidebar:
    st.markdown('<div class="lateral-titulo">Tu flota</div>'
                '<div class="lateral-texto">Todos los camiones son iguales. Cambia los valores y '
                'el resto de la página se recalcula.</div>', unsafe_allow_html=True)
    capacidad = st.number_input("Capacidad por camión (unidades)", min_value=1000, max_value=100000,
                                value=20000, step=1000,
                                help="Número de productos que caben en un camión.")
    velocidad = st.number_input("Velocidad media (km/h)", min_value=30, max_value=120, value=80, step=5)
    coste_km = st.number_input("Coste por kilómetro (€)", min_value=0.10, max_value=10.0, value=1.20,
                               step=0.05, format="%.2f")
    st.write("")
    calcular = st.button("Calcular rutas", type="primary", use_container_width=True)

# --- Cabecera y tira de expedición --------------------------------------------
pedidos = cargar_pedidos()
unidades = pedidos["Unidades"].sum()
minimo = cota_inferior_camiones(unidades, capacidad)

st.markdown(
    '<div class="cabecera"><div><h1>Planificador de rutas</h1>'
    '<p>Reparto de los pedidos pendientes de IA DELIVERY desde Mataró, antes de que caduquen.</p></div>'
    f'<div class="sello">{len(pedidos)} pedidos del {pedidos["FechaPedido"].min():%d/%m/%Y}</div></div>',
    unsafe_allow_html=True)

st.markdown(
    '<div class="tira">'
    '<div class="parada origen"><div class="punto"></div><div class="valor">Mataró</div>'
    '<div class="que">salida de todos los camiones</div></div>'
    f'<div class="parada"><div class="punto"></div><div class="valor">{len(pedidos)}</div>'
    '<div class="que">pedidos pendientes</div></div>'
    f'<div class="parada"><div class="punto"></div><div class="valor">{pedidos["IdDestino"].nunique()}</div>'
    '<div class="que">destinos en España</div></div>'
    f'<div class="parada"><div class="punto"></div><div class="valor">{miles(unidades)}</div>'
    '<div class="que">unidades a repartir</div></div>'
    f'<div class="parada final"><div class="punto"></div><div class="valor">{minimo}</div>'
    '<div class="que">camiones como mínimo</div>'
    f'<div class="nota">con {miles(capacidad)} unidades por camión</div></div>'
    '</div>',
    unsafe_allow_html=True)

if calcular:
    st.info("El cálculo de rutas todavía no está conectado. Cuando lo esté, aquí verás la ruta de cada camión.")

# --- Pestañas ------------------------------------------------------------------
tab_mapa, tab_pedidos, tab_como = st.tabs(["Mapa", "Pedidos", "Cómo funciona"])

with tab_mapa:
    leyenda = "".join(
        f'<span><i style="background:{c}"></i>{txt}</span>'
        for txt, c in [("menos de 250 km", ESCALA_DISTANCIA[0][1]), ("de 250 a 500 km", ESCALA_DISTANCIA[1][1]),
                       ("de 500 a 750 km", ESCALA_DISTANCIA[2][1]), ("más de 750 km", ESCALA_DISTANCIA[3][1])])
    st.markdown(f'<div class="leyenda">{leyenda}<span>El tamaño del punto indica las unidades del pedido.'
                '</span></div>', unsafe_allow_html=True)
    st_folium(crear_mapa(pedidos, velocidad), height=560, use_container_width=True, returned_objects=[])

with tab_pedidos:
    tabla = pedidos.assign(
        HorasIda=(pedidos["DistanciaKm"] / velocidad).round(1),
        CosteIdaVuelta=(2 * pedidos["DistanciaKm"] * coste_km).round(0),
    )[["IdPedido", "Provincia", "Unidades", "DistanciaKm", "HorasIda", "CosteIdaVuelta", "MargenJITDias"]]
    st.dataframe(
        tabla.sort_values("DistanciaKm", ascending=False), hide_index=True, height=560,
        use_container_width=True,
        column_config={
            "IdPedido": st.column_config.NumberColumn("Pedido", format="%d"),
            "Unidades": st.column_config.ProgressColumn(
                "Unidades", format="%d", min_value=0, max_value=int(tabla["Unidades"].max())),
            "DistanciaKm": st.column_config.ProgressColumn(
                "Distancia a Mataró (km)", format="%.0f", min_value=0,
                max_value=float(tabla["DistanciaKm"].max())),
            "HorasIda": st.column_config.NumberColumn("Horas de ida", format="%.1f h"),
            "CosteIdaVuelta": st.column_config.NumberColumn("Ida y vuelta (€)", format="%.0f €",
                                                            help="Si el pedido fuera solo en un camión"),
            "MargenJITDias": st.column_config.NumberColumn("Días hasta caducar", format="%d días"),
        },
    )

with tab_como:
    st.markdown(
        '<div class="como">\n\n'
        "#### Qué estás viendo\n"
        "Cada punto del mapa es un destino con pedidos pendientes. Todos salen de la sede de Mataró, "
        "y cada pedido tiene que ir entero en un solo camión.\n\n"
        "#### El mínimo de camiones\n"
        "Es la cuenta más sencilla: las unidades de todos los pedidos entre la capacidad de un camión. "
        "El número real será mayor, porque además hay que respetar las distancias y la caducidad.\n\n"
        "#### Qué falta\n"
        "El botón *Calcular rutas* conectará con el optimizador, que agrupará los pedidos en rutas y "
        "dirá cuántos camiones hacen falta de verdad.\n\n</div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="caducidad">Todos los pedidos llevan productos que caducan a los 7 días. '
        'Por eso la fabricación se planifica para que todo termine a la vez y el camión salga con '
        '7 días de margen para llegar a su destino.</div>', unsafe_allow_html=True)
