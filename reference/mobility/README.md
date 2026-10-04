# Distancias de Wasserstein calculadas por nosotros (Tabla 2)

`wasserstein_w1_utm_pooled.csv`: W1 en **metros** de cada grupo de la Tabla 2 entre la distribución
espacial de la mañana (horas 10-12) y la de la tarde (20-22), con el método descrito en el paper:
transporte óptimo exacto en 2D, costo euclídeo entre centros de hexágono en EPSG:32719, masa del
grupo = `share × población` sumada en la ventana (`demographics/mobility.py`).

**No son cifras del paper** y **no reproducen** los valores publicados de la Tabla 2 (error máximo
0,14 sobre los valores normalizados; 12 de 15 rankings): ver `AGENTS.md` H24. Son 15 números
agregados calculados sobre los datos confidenciales (sin filas individuales). Se guardan para poder
probar la integración con la Tabla 2 sin recalcular (el cálculo completo tarda ~10 minutos).

Regenerar: `python scripts/05_mobility.py` (calcula y compara con la tabla publicada).
