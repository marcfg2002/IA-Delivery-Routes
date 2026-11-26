"""Prueba de integración del simulador: la app arranca y muestra los datos sin errores."""
import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "app.py"


def _html(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _minimo_camiones(at) -> int:
    return int(re.search(r'parada final"><div class="punto"></div><div class="valor">(\d+)<', _html(at)).group(1))


def test_app_arranca_sin_errores():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    html = _html(at)
    assert "Planificador de rutas" in html
    assert '<div class="valor">133</div>' in html  # pedidos pendientes


def test_boton_calcular_avisa_que_falta_el_optimizador():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert "todavía no está conectado" in at.info[0].value


def test_minimo_de_camiones_cambia_con_la_capacidad():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    antes = _minimo_camiones(at)
    at.sidebar.number_input[0].set_value(10000).run()
    assert _minimo_camiones(at) > antes
