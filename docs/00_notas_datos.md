# Notas sobre los datos (Fase 0)

Primeras observaciones al convertir `BDIADelivery_script.sql` a CSV. Se profundizarán en la Fase 1.

- **Pedidos**: 133 (el enunciado habla de ~500 simultáneos con ~100 líneas). Todos tienen la misma
  fecha (`2026-11-18 19:53`) y exactamente 133 líneas cada uno. 126 destinos distintos.
- **Cantidad por línea**: 1–500 unidades (mediana 21), coherente con el enunciado.
- **Productos**: fabricación 1–15 días; caducidad 7–730 días.
- **Destinos: los datos son sintéticos y no son coherentes geográficamente.**
  - Las coordenadas están repartidas al azar en un rectángulo (lat 36–43, lon −8–2), por lo que
    algunas caen en el mar.
  - `Pais` e `IdProvincia` no cuadran con las coordenadas (p. ej. destinos "Portugal" en coordenadas de
    Aragón o Andalucía; `IdProvincia` = `IdDestino` en los primeros registros).
  - Ciudad y dirección son genéricas ("Ciudad 1", "Calle 1").
- **Provincias**: 47 (faltan, p. ej., las insulares, que no aplican al reparto peninsular).

**Decisión pendiente (Fase 1):** tomar las coordenadas GPS como fuente de verdad (lo que permite el
enunciado como alternativa a la distancia en km) y documentar la incoherencia de país/provincia, o
reasignar coordenadas a cada destino según su provincia/país.
