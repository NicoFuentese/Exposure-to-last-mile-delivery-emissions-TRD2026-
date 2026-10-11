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

## `wasserstein_authors_seeds_km.csv`

W1 en **kilómetros** de cada grupo de la Tabla 2 (mañana 10-12 h → tarde 20-22 h) para **200 semillas** (`seed` = 0…199), con el método del script de los autores (`04_descriptives/people_summary_table.R`): muestra aleatoria de 5.000 de los 11.144 hexágonos, masa = media de las 3 horas de cada ventana de `población × proporción`, costo geodésico (haversine con R = 6371,0088 km; la elipsoide difiere ≤ 0,3 %), W1 exacto (`demographics/mobility.py`). Los valores de la Tabla 2 se obtienen dividiendo cada fila por la mediana de su categoría.

Los autores no fijaron semilla, así que los valores publicados son **una extracción**; ver `AGENTS.md` H24. No son cifras del paper. Son 200 × 15 números agregados (sin filas individuales). Regenerar: `python scripts/12_mobility_seeds.py --seeds 200 --workers 8 --write-reference` (~40 min; el archivo se escribió así el 2026-10-10).
