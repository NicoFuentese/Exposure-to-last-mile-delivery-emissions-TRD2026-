# Mapa paper → código

Índice para encontrar rápido dónde está cada fórmula, variable o paso del paper. Los hallazgos (`H…`) y decisiones (`D…`) remiten a [`AGENTS.md`](../AGENTS.md) §7. Paquete: `src/lastmile_exposure/`.

**Estado:** ✅ implementado y validado contra el paper · 🟡 parcial · ⏳ pendiente · 🚫 no reconstruible con los datos actuales.

## Datos y construcción de variables

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| §3.1, Tabla 2 | Panel de población flotante hexágono‑hora, shares, EF | `io/panel.py` | ✅ (H15) |
| §3.1 (EF_c) | Factor de expansión por comuna | (viene aplicado en el panel; no se recalcula) | 🚫 |
| §5.2 | Demografía estática (`datosxhexagono.csv`) | `io/static.py`, `demographics/static.py` | ✅ (H8) |
| §3.2, Tabla 3 | GPS de vehículos | `io/gps.py` | ⏳ (solo 1 día) |
| §4.1.1, Fig. 4 | Conteo `Y_hi` y mediana `Ỹ_hi` | `exposure/vehicles_counts.py`, `exposure/aggregate.py` | ✅ la mediana desde los 42 archivos diarios es **idéntica** a la del paper (H2); `scripts/04_median_counts.py`. `Y_hi` por día desde el GPS crudo: 🚫 |
| §4.1.2 | Distancia y tiempo diarios por hexágono-hora (41 miércoles) | `io/daily_metrics.py` | ✅ (H30) |
| §4.1.2, Fig. 5 | Distancia `K_hi` y mediana `K̃_hi` | `exposure/vehicles_distance.py` | ✅ las 178.304 medianas (distancia, tiempo y `count_wednesdays`) se reconstruyen exactamente desde los 41 archivos diarios del paquete v2 (H30; `scripts/11_median_distance.py`); `K_hi` por día desde el GPS crudo: 🚫 (H4, D7) |
| §4, Fig. 3 | Fusión hexágono‑hora | `panel.py` | ✅ sobre las bases finales del paquete; 🚫 desde el GPS crudo (D7) |
| §3.2 / H1 | UTC → `America/Santiago` | `timeutils/local_time.py` | ✅ `timeutils/local_time.py`, `panel.py` (Fase 5; H18, H33) |
| §4.2 | Regresores `D_hi`, referencias, D+E | `demographics/shares.py`, `config.py` | ✅ |

## Modelos

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| Ec. (1)–(3) | ZINB, inflación constante, NB2 | `models/zinb.py` | ✅ `fit_zinb_mle` (máximo en la frontera π = 0, la NB) reproduce la col. ZINB a la precisión impresa (H21–H23, H29) |
| Ec. (4) | Efecto marginal del ZINB | `models/marginal_effects.py` | ✅ tres fórmulas; `authors` = `eq4` porque π̂ ≈ 0 (H10, H21); `authors` es un error del código de los autores y la sensibilidad usa `eq4` |
| Ec. (5)–(6) | OLS de `K̃` y `log K̃` | `models/ols.py` | ✅ Tablas 4–5, cols. 2 y 4 (H8) |
| Tablas 4–5, col. 3 | "OLS `K̃>0`" = logit + OLS | `models/two_part.py` | ✅ (H7) |

## Inferencia

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| §4.2.3 | Errores estándar agrupados por comuna (51) | `inference/cluster.py`, `inference/zinb_sandwich.py` | ✅ SE validados contra R (≤ 1,5 %; H25); `scripts/06_inference.py` |
| §4.2.3 | I de Moran (0,4694 / 0,4756) | `inference/moran.py` | 🟡 la lectura literal (0,419 / 0,430) **no reproduce**; las alternativas se acercan a ~1–2 % pero la especificación no está identificada (H28); `scripts/09_moran.py` |
| §4.2.1 | Cameron–Trivedi (7,73) | `inference/dispersion.py` | ✅ 7,750 (0,26 %, H27); `scripts/08_dispersion_test.py` |
| §4.2.1 | π (probabilidad de cero estructural) | `inference/zero_inflation.py` | ℹ️ diagnóstico (el paper no reporta π): máximo del perfil en π = 0, IC 95 % [0, ~10⁻⁴] (H29); `scripts/10_zero_inflation.py` |
| Tablas 4–5 | Estrellas de significancia | `reporting/significance.py` | ✅ **88/88 contra las tablas regeneradas por los autores** (Tabla 4 con `paper_text`, Tabla 5 con `authors_script`; H31, D3); contra las estrellas impresas en el paper no coinciden (50/88 y 61/88; la propia referencia de los autores, 23/44 y 38/44). Diagnóstico aislado con el `data_base` de 2 miércoles (**no es réplica**): `validation/stars_diagnosis.py`, `scripts/07_stars_diagnosis.py` |

## Resultados y figuras

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| Tabla 2 | Descriptivos de la población flotante | `reporting/table2.py` | ✅ Mean/Std/% (H15); `scripts/01_table2.py` |
| Tabla 2, Wasserstein y ranking | Movilidad mañana→tarde por grupo | `demographics/mobility.py` | 🟡 lectura determinista del texto (error máx. 0,14; 12/15 rankings). Método de los autores **identificado** (muestra aleatoria de 5.000 hexágonos sin semilla): los valores publicados no son reproducibles exactamente; con 200 semillas, 13/15 caen en la banda del 95 % y los extremos son estables. Cálculo con semillas: `demographics/mobility.py` (`mobility_over_seeds`, `summarize_seeds`) y `scripts/12_mobility_seeds.py` (H24, D10); lectura determinista: `scripts/05_mobility.py` |
| Tablas 4 y 5 | Efectos marginales (4 columnas) | `reporting/marginal_tables.py` | ✅ 4 de 4 columnas con valores a la precisión impresa y estrellas 88/88 contra las tablas regeneradas por los autores (H23, H31); `scripts/02_distance_tables.py`, `03_zinb_tables.py` y `06_inference.py` |
| Figs. 1, 2 | Mapas de población por GSE y de pings | `figures/maps.py` | ⏳ |
| Figs. 6, 8, 9, 10 | Efectos marginales por GSE/edad | `figures/marginal_effects.py` | ⏳ |
| Fig. 7 | Gramos de NOx/PM | `reporting/emissions.py` | ⏳ (D10) |
| Extensión | Métrica de ruido | `exposure/noise.py` | ⏳ (Fase 8) |

## Validación contra el paper

Las cifras publicadas están en [`reference/paper_tables/`](../reference/paper_tables/) y las carga y compara `validation/paper_tables.py`. Las pruebas viven en `tests/validation/` (se saltan solas si los datos confidenciales no están).

| Comprobación | Cómo se ejecuta | Resultado |
|---|---|---|
| Tabla 2 (62 celdas) | `python scripts/01_table2.py` | ✅ todas dentro del redondeo del paper |
| Tablas 4 y 5, columnas de distancia (39 + 39 celdas) | `python scripts/02_distance_tables.py` | ✅ diferencia máxima 5·10⁻⁵ (4 decimales) |
| Mediana de conteos (178.304 filas × 2 columnas) | `python scripts/04_median_counts.py` (~1 min) | ✅ igualdad exacta con la base del paper |
| Tablas 4 y 5, columna ZINB (13 + 13 celdas) | `python scripts/03_zinb_tables.py` (~2 min) | ✅ dif. máx. 5,7·10⁻⁵ (T4) y 4,4·10⁻⁵ (T5); tolerancia = precisión impresa, 6·10⁻⁵ (D2, acordado 2026-10-10) |
| Mediana de distancia y tiempo (178.304 filas × 3 columnas) | `python scripts/11_median_distance.py` (~30 s) | ✅ igualdad exacta con la base del paper (H30) |
| Wasserstein de la Tabla 2 con 200 semillas del método de los autores | `python scripts/12_mobility_seeds.py --use-reference` | 🟡 13/15 valores publicados dentro de la banda del 95 %, extremos estables; no es reproducción exacta (muestra sin semilla, H24) |
| Sensibilidad en hora local (Tablas 4 y 5, horas 7–19) | `python scripts/13_local_time_sensitivity.py` (~2 min) | 🟡 sensibilidad, sin objetivo del paper: las cuatro conclusiones se mantienen y los coeficientes cambian ~8–12 % en mediana (H33) |
| Estrellas contra las Tablas 4 y 5 regeneradas por los autores (44 + 44 celdas) | `pytest tests/validation/test_authors_reference.py` | ✅ 44/44 (Tabla 4, cluster por comuna) y 44/44 (Tabla 5, variante del script de los autores, H31) |

## Convención de documentación

Todo módulo abre con un docstring con estas cuatro líneas (lo comprueba `tests/test_structure.py`):

```
Paper: <sección / ecuación / tabla / figura y página>
Código de los autores: <script R y función, o "(no está en el paquete)">
Hallazgos (AGENTS.md §7): <H… / D… relacionados>
Estado: <pendiente (Fase N) | reproducido | …>
```

Cada función que implemente una fórmula cita la ecuación (`Ec. (4), p.11`) y, si el código de los autores difiere del texto, lo indica con su hallazgo. Los docstrings van en español; los identificadores, en inglés.
