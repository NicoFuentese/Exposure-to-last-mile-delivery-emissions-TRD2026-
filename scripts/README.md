# scripts/

Puntos de entrada del pipeline, **uno por fase**, numerados en el orden en que se ejecutan. Son delgados: leen argumentos, llaman a funciones de `src/lastmile_exposure/` y guardan resultados. **No contienen lógica** de la réplica (si hay una fórmula, está en el paquete).

Convención: `NN_descripcion.py`; si el resultado depende de la variante, se acepta `--variant as_published|local_time`. Los resultados se escriben en `outputs/<variante>/`. Cada script compara con el paper y termina con código 1 si algo difiere.

| Script | Qué reproduce |
|---|---|
| `01_table2.py` | Tabla 2 (población flotante) |
| `02_distance_tables.py` | Columnas de distancia de las Tablas 4 y 5 (solo `as_published`: la distancia no se puede convertir a hora local, H19) |
| `03_zinb_tables.py` | Columna ZINB de las Tablas 4 y 5 (~2 min) y tablas completas sin estrellas |
| `04_median_counts.py` | Reconstruye `median_vehicles` desde los 42 archivos diarios (igualdad exacta con la base del paper) y mide las variantes (días ausentes = 0; sin el feriado) |
| `05_mobility.py` | Wasserstein y ranking de movilidad de la Tabla 2 (~10 min; `--use-reference` es instantáneo). Informa la brecha con el paper y **termina siempre con código 0** (método no identificado, H24) |
| `06_inference.py` | SE por comuna y estrellas de las Tablas 4 y 5 sobre `00_data` en tres variantes (`paper_text`, `authors_script`, `iid`), comparadas con el paper (~8 min). **Termina siempre con código 0**: las estrellas publicadas no se reproducen todas (H25, H26, D3) |
| `07_stars_diagnosis.py` | **DIAGNÓSTICO, NO ES UNA RÉPLICA.** Calcula las estrellas con `00_out/data_base` (mediana de los 2 primeros miércoles, no la base del paper) solo para probar por qué las estrellas publicadas no coinciden (H26). Sus resultados no sirven como inferencia ni se usan en tablas o figuras; salida en `outputs/diagnostics/`. Termina siempre con código 0 |
| `08_dispersion_test.py` | Test de Cameron–Trivedi (dispersión 7,73) sobre el Poisson dinámico y estático; compara con el paper (error relativo ≤ 1 %). Rápido (segundos); código 1 si el dinámico no cumple |
| `r_oracle/cluster_se.R` | Contraste en R (`sandwich::vcovCL`) de los SE con cluster; ver `reference/r_oracle/README.md` |
| `r_oracle/zinb_pscl.R` | Contraste en R (`pscl`) del ZINB; ver `reference/r_oracle/README.md` |

Se crearán más a medida que avance cada fase (ver `AGENTS.md` §10).
