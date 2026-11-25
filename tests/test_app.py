"""Prueba de integración del simulador: la app arranca y muestra los datos sin errores."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "app.py"


def test_app_arranca_sin_errores():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    assert at.title[0].value.startswith("🚚 IA DELIVERY")
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Pedidos"] == "133"


def test_boton_calcular_avisa_que_falta_el_optimizador():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert "todavía no está conectado" in at.info[0].value


def test_cota_inferior_cambia_con_la_capacidad():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    antes = next(m.value for m in at.metric if m.label.startswith("Camiones"))
    at.sidebar.number_input[0].set_value(10000).run()
    despues = next(m.value for m in at.metric if m.label.startswith("Camiones"))
    assert int(despues) > int(antes)
