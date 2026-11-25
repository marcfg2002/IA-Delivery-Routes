# IA-Delivery-Routes

**Proyecto 1 · Máster FP en Inteligencia Artificial y Big Data (Stucom)**
Plataforma de distribución de mercancías perecederas para **IA DELIVERY SL** (Mataró).

Herramienta que calcula las rutas de reparto óptimas desde Mataró a los centros
logísticos de los clientes (España, Portugal y Andorra) y determina la **flota mínima
de camiones propios** necesaria para servir los pedidos antes de que caduquen.

## Problema

- Cada pedido se entrega con **un único camión** y lo antes posible.
- Debe llegar antes de su **fecha de caducidad**:
  `Caducidad pedido = min(FechaPedido + 1 día + TiempoFabricación + DíasCaducidad)` de sus productos
  (la fabricación empieza el día siguiente a recibir el pedido).
- Si todos los productos se fabrican a la vez, **ningún pedido llega a tiempo** (todos mezclan productos de
  15 días de fabricación con Ensalada Preparada, que caduca a los 7). Por eso planificamos la fabricación
  *just in time*: cada producto termina el mismo día que el más lento y el pedido sale con 7 días de margen.
- Flota homogénea: coste/km, velocidad media y capacidad (nº de productos) constantes; un conductor por viaje (ida y vuelta).
- Objetivo: minimizar el nº de camiones y el coste/km respetando capacidad y caducidad
  → problema de rutas de vehículos con capacidad y ventanas de tiempo (**CVRPTW**).

## Datos

Base de datos `BDIADelivery` (SQL Server) entregada en clase: `data/raw/BDIADelivery_script.sql`.

| Tabla | Filas | Contenido |
|---|---:|---|
| Pedidos | 133 | Id, fecha, cliente, destino |
| LineasPedido | 17.689 | 133 líneas por pedido, 1–500 unidades por línea |
| Productos | 10.000 | Precio, tiempo de fabricación (1–15 días), caducidad (7–730 días) |
| Destinos | 1.500 | Dirección, provincia, país, Latitud/Longitud y Coordenadas (geography) |
| Clientes | 500 | Datos de contacto |
| Provincias | 47 | Provincias españolas |

Para trabajar sin SQL Server, el script se convierte a CSV. **El script original nunca se modifica**:
solo se lee, y un test comprueba que sigue siendo idéntico al que nos dieron (MD5).

### Instalación y ejecución

Requisitos: Python 3.10 o superior. Los comandos se ejecutan desde la raíz del proyecto.

**Windows (PowerShell)**

```powershell
# 1. Crear y activar el entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Indicar dónde está el código fuente (solo una vez por terminal)
$env:PYTHONPATH = "src"

# 4. Convertir el script SQL a CSV
python -m ia_delivery.sql_loader data/raw/BDIADelivery_script.sql data/processed

# 5. Ejecutar los tests
python -m pytest tests
```

> Si PowerShell bloquea la activación del entorno virtual, ejecuta una vez
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a intentarlo.

**Windows (CMD)**

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
set PYTHONPATH=src
python -m ia_delivery.sql_loader data/raw/BDIADelivery_script.sql data/processed
python -m pytest tests
```

**Linux / macOS (bash)**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m ia_delivery.sql_loader data/raw/BDIADelivery_script.sql data/processed
PYTHONPATH=src python -m pytest tests
```

### ⚠️ Aviso sobre los destinos    

Las coordenadas de la tabla `Destinos` son **aleatorias** dentro de un rectángulo de la península:

- El campo `Pais` no cuadra con la posición (67 de los 75 destinos de Portugal están en España;
  ninguno de los 45 de Andorra está en Andorra) y algunos puntos caen en el mar.
- `IdProvincia` sigue la misma numeración que `IdDestino`, sin relación con la posición.
- La columna `Coordenadas` (geography) **no coincide** con `Latitud`/`Longitud` en ningún destino.
  La guardamos descodificada en `GeoLatitud`/`GeoLongitud`.

De momento las rutas se calculan con `Latitud`/`Longitud` (distancia Haversine). Lo estamos consultando
con el profesor. Más detalle en `notebooks/01_analisis_exploratorio.ipynb`.

## Estructura

```
data/raw/          script SQL original
data/processed/    CSV generados desde el SQL
src/ia_delivery/   código del prototipo (carga, preprocesado, optimización)
app/               interfaz Streamlit (simulador)
notebooks/         estudio previo de la BBDD (gráficos en docs/img/eda)
tests/             pruebas unitarias, de integración y de aceptación
docs/              figuras y capturas para la documentación
tools/             utilidades (capturas de código para la memoria)
```

## Plan de trabajo

Sigue el «Calendario GOALS» del grupo. La memoria completa está en el Drive del grupo (P1G1).

| Fase | Goal | Contenido | Estado |
|---|---|---|---|
| 1. Arquitectura, entorno y datos | 1 | Requisitos, arquitectura y repositorio | 🟡 Repo y requisitos hechos; faltan diagramas |
| | 2 | Carga de la BBDD, estudio previo y generación de escenarios | 🟡 Carga y estudio previo hechos; faltan escenarios |
| 2. Prototipo IA y algoritmia | 3 | Enrutamiento base desde Mataró (OR-Tools) | ⏳ |
| | 4 | Restricciones de capacidad y caducidad, flota mínima | ⏳ |
| 3. Validación y rendimiento | 5 | Pruebas unitarias, de integración y de aceptación | 🟡 Primeros tests de la carga |
| | 6 | Análisis de rendimiento | ⏳ |
| 4. Documentación y cierre | 7–10 | Especificaciones, casos de uso, manual, vídeo y entrega (15/12/2026) | ⏳ |

## Autores

Marc Fernández González · Pol Carvajal García · Javier Givica Ferrer
