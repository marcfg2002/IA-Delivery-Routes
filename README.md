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
| Destinos | 1.500 | Dirección, provincia, país, lat/lon |
| Clientes | 500 | Datos de contacto |
| Provincias | 47 | Provincias españolas |

Para trabajar sin SQL Server, el script se convierte a CSV:

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m ia_delivery.sql_loader data/raw/BDIADelivery_script.sql data/processed
```

## Estructura

```
data/raw/          script SQL original
data/processed/    CSV generados desde el SQL
src/ia_delivery/   código del prototipo (carga, preprocesado, optimización)
app/               interfaz Streamlit (simulador)
notebooks/         exploración y análisis
tests/             pruebas unitarias, de integración y de aceptación
docs/              documentación (requisitos, casos de uso, arquitectura, manual)
```

## Plan por fases

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Repositorio, estructura y carga de la BBDD a CSV | ✅ |
| 1 | Análisis exploratorio y calidad de datos | ⏳ |
| 2 | Requisitos funcionales / no funcionales y casos de uso | ⏳ |
| 3 | Preprocesado: caducidad por pedido, volumen, matriz de distancias | ⏳ |
| 4 | Motor de optimización de rutas (CVRPTW) y flota mínima | ⏳ |
| 5 | Simulador Streamlit (+ despliegue en Render) | ⏳ |
| 6 | Pruebas y análisis de rendimiento | ⏳ |
| 7 | Arquitectura, especificaciones técnicas, manual de usuario y vídeo | ⏳ |

## Autores

Marc Fernández González · Pol Carvajal García · Javier Givica Ferrer
