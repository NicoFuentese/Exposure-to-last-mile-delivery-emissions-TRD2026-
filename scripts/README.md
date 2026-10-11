# scripts/

Puntos de entrada del pipeline, **uno por fase**, numerados en el orden en que se ejecutan. Son delgados: leen argumentos, llaman a funciones de `src/lastmile_exposure/` y guardan resultados. **No contienen lógica** de la réplica (si hay una fórmula, está en el paquete).

Convención: `NN_descripcion.py`; si el resultado depende de la variante, se acepta `--variant as_published|local_time`. Los resultados se escriben en `outputs/<variante>/`. Cada script compara con el paper y termina con código 1 si algo difiere.

| Script | Qué reproduce |
|---|---|
| `01_table2.py` | Tabla 2 (población flotante) |
| `02_distance_tables.py` | Columnas de distancia de las Tablas 4 y 5 (solo `as_published`; la hora local está en `13_local_time_sensitivity.py`) |
| `03_zinb_tables.py` | Columna ZINB de las Tablas 4 y 5 (~2 min) y tablas completas sin estrellas |
| `04_median_counts.py` | Reconstruye `median_vehicles` desde los 42 archivos diarios (igualdad exacta con la base del paper) y mide las variantes (días ausentes = 0; sin el feriado) |
| `05_mobility.py` | Wasserstein y ranking de movilidad de la Tabla 2 (~10 min; `--use-reference` es instantáneo). Informa la brecha con el paper y **termina siempre con código 0** (método no identificado, H24) |
| `06_inference.py` | SE por comuna y estrellas de las Tablas 4 y 5 sobre `00_data` en tres variantes (`paper_text`, `authors_script`, `iid`), comparadas con el paper (~8 min). **Termina siempre con código 0**: las estrellas publicadas no se reproducen todas (H25, H26, D3) |
| `07_stars_diagnosis.py` | **DIAGNÓSTICO, NO ES UNA RÉPLICA.** Calcula las estrellas con `00_out/data_base` (mediana de los 2 primeros miércoles, no la base del paper) solo para probar por qué las estrellas publicadas no coinciden (H26). Sus resultados no sirven como inferencia ni se usan en tablas o figuras; salida en `outputs/diagnostics/`. Termina siempre con código 0 |
| `08_dispersion_test.py` | Test de Cameron–Trivedi (dispersión 7,73) sobre el Poisson dinámico y estático; compara con el paper (error relativo ≤ 1 %). Rápido (segundos); código 1 si el dinámico no cumple |
| `09_moran.py` | I de Moran de la distancia y los vehículos (anillo 1 de H3, pesos `W`/`B`, 3 agregaciones del tiempo) frente a 0,4694 / 0,4756 (segundos). Rotula cada lectura exacto / aproximado / no reproduce y **termina siempre con código 0**: la especificación del paper no está identificada (H28, D8) |
| `10_zero_inflation.py` | π del ZINB (probabilidad de cero estructural): verosimilitud perfilada en π, test de razón de verosimilitudes de H0: π = 0 con p-valor de frontera e IC del 95 % (~4 min). **Diagnóstico, no réplica** (el paper no reporta π) y **termina siempre con código 0** (H29) |
| `11_median_distance.py` | Reconstruye `median_distance`, `median_time` y `count_wednesdays` desde los 41 archivos diarios de distancia (igualdad exacta con la base del paper, ~30 s) y mide la variante de días ausentes = 0 |
| `12_mobility_seeds.py` | Wasserstein de la Tabla 2 con el método del script de los autores (muestra aleatoria de 5.000 hexágonos) repetido con 200 semillas (~40 min con 8 procesos; una corrida con 14 procesos y la suite de pruebas a la vez fue detenida por falta de memoria; cada semilla terminada se guarda en un parcial y `--resume` retoma; `--use-reference` es instantáneo): compara los valores publicados con la mediana y la banda del 95 % de las semillas. **Termina siempre con código 0** (los valores publicados son una extracción sin semilla, H24) |
| `13_local_time_sensitivity.py` | Sensibilidad en hora local (Fase 5): Tablas 4 y 5 con los camiones convertidos a `America/Santiago` (horas 7–19) frente a la publicada restringida a las mismas horas, y las cuatro conclusiones del paper (~2 min). Escribe en `outputs/local_time/`. **Termina siempre con código 0** (no hay objetivo del paper) |
| `14_figures.py` | Figs. 6, 8, 9 y 10 (efectos marginales con eje doble reescalado como en el código de los autores, H34) y Fig. 7 (gramos de NOx y PM con factores derivados de las barras impresas, H36). Segundos; usa las tablas de `03_zinb_tables.py`. Escribe en `outputs/`; con `--publish` copia las figuras de coeficientes a `docs/figures/` |
| `15_maps.py` | Fig. 1 (mapas de población de AB y C1b, mañana y tarde; ~30 s) y un **sustituto rotulado** de la Fig. 2 (vehículos por hexágono; no es la Fig. 2). Escribe en `outputs/`; con `--publish` copia solo los PNG de ambas (150 dpi) a `docs/figures/`. Termina siempre con código 0 (H35) |
| `r_oracle/cluster_se.R` | Contraste en R (`sandwich::vcovCL`) de los SE con cluster; ver `reference/r_oracle/README.md` |
| `r_oracle/zinb_pscl.R` | Contraste en R (`pscl`) del ZINB; ver `reference/r_oracle/README.md` |

Se crearán más a medida que avance cada fase (ver `AGENTS.md` §10).
