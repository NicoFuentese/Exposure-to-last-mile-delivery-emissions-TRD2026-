# scripts/

Puntos de entrada del pipeline, **uno por fase**, numerados en el orden en que se ejecutan. Son delgados: leen argumentos, llaman a funciones de `src/lastmile_exposure/` y guardan resultados. **No contienen lógica** de la réplica (si hay una fórmula, está en el paquete).

Convención: `NN_descripcion.py`; si el resultado depende de la variante, se acepta `--variant as_published|local_time`. Los resultados se escriben en `outputs/<variante>/`. Cada script compara con el paper y termina con código 1 si algo difiere.

| Script | Qué reproduce |
|---|---|
| `01_table2.py` | Tabla 2 (población flotante) |
| `02_distance_tables.py` | Columnas de distancia de las Tablas 4 y 5 (solo `as_published`: la distancia no se puede convertir a hora local, H19) |
| `03_zinb_tables.py` | Columna ZINB de las Tablas 4 y 5 (~2 min) y tablas completas sin estrellas |
| `04_median_counts.py` | Reconstruye `median_vehicles` desde los 42 archivos diarios (igualdad exacta con la base del paper) y mide las variantes (días ausentes = 0; sin el feriado) |
| `r_oracle/zinb_pscl.R` | Contraste en R (`pscl`) del ZINB; ver `reference/r_oracle/README.md` |

Se crearán más a medida que avance cada fase (ver `AGENTS.md` §10).
