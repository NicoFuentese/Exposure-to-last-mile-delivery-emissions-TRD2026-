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
| §4.1.2, Fig. 5 | Distancia `K_hi` y mediana `K̃_hi` | `exposure/vehicles_distance.py` | 🚫 faltan distancias diarias (H4, D7) |
| §4, Fig. 3 | Fusión hexágono‑hora | `panel.py` | ✅ sobre las bases finales del paquete; 🚫 desde el GPS crudo (D7) |
| §3.2 / H1 | UTC → `America/Santiago` | `timeutils/local_time.py` | ⏳ verificada en exploración (H18), **sin código todavía** (Fase 5) |
| §4.2 | Regresores `D_hi`, referencias, D+E | `demographics/shares.py`, `config.py` | ✅ |

## Modelos

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| Ec. (1)–(3) | ZINB, inflación constante, NB2 | `models/zinb.py` | ✅ reproduce la col. ZINB dentro de la tolerancia del optimizador (H21–H23) |
| Ec. (4) | Efecto marginal del ZINB | `models/marginal_effects.py` | ✅ tres fórmulas; `authors` = `eq4` porque π̂ ≈ 0 (H10, H21) |
| Ec. (5)–(6) | OLS de `K̃` y `log K̃` | `models/ols.py` | ✅ Tablas 4–5, cols. 2 y 4 (H8) |
| Tablas 4–5, col. 3 | "OLS `K̃>0`" = logit + OLS | `models/two_part.py` | ✅ (H7) |

## Inferencia

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| §4.2.3 | Errores estándar agrupados por comuna (51) | `inference/cluster.py`, `inference/zinb_sandwich.py` | ✅ SE validados contra R (≤ 1,5 %; H25); `scripts/06_inference.py` |
| §4.2.3 | I de Moran (0,4694 / 0,4756) | `inference/moran.py` | ⏳ |
| §4.2.1 | Cameron–Trivedi (7,73) | `inference/dispersion.py` | ✅ 7,750 (0,26 %, H27); `scripts/08_dispersion_test.py` |
| §4.2.1 | π (probabilidad de cero estructural) | `inference/dispersion.py` | ⏳ (Fase 4D) |
| Tablas 4–5 | Estrellas de significancia | `reporting/significance.py` | 🟡 calculadas con 3 variantes sobre `00_data` (`paper_text` 50/88, `authors_script` 61/88, `iid`); **no todas coinciden** (H25, H26, D3). Diagnóstico aislado con `data_base` (**no es réplica**): `validation/stars_diagnosis.py`, `scripts/07_stars_diagnosis.py` |

## Resultados y figuras

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| Tabla 2 | Descriptivos de la población flotante | `reporting/table2.py` | ✅ Mean/Std/% (H15); `scripts/01_table2.py` |
| Tabla 2, Wasserstein y ranking | Movilidad mañana→tarde por grupo | `demographics/mobility.py` | 🟡 implementado como describe el paper; **no reproduce** los valores (error máx. 0,14; 12/15 rankings; H24); `scripts/05_mobility.py` |
| Tablas 4 y 5 | Efectos marginales (4 columnas) | `reporting/marginal_tables.py` | 🟡 4 de 4 columnas con valores; estrellas calculadas pero no todas coinciden (H25); `scripts/02_distance_tables.py`, `03_zinb_tables.py` y `06_inference.py` |
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
| Tablas 4 y 5, columna ZINB (13 + 13 celdas) | `python scripts/03_zinb_tables.py` (~2 min) | ✅ dif. máx. 0,0032 (T4) y 0,0321 (T5); mismos signos; criterio relativo 1 % con piso 0,005 (D2, acordado) |

## Convención de documentación

Todo módulo abre con un docstring con estas cuatro líneas (lo comprueba `tests/test_structure.py`):

```
Paper: <sección / ecuación / tabla / figura y página>
Código de los autores: <script R y función, o "(no está en el paquete)">
Hallazgos (AGENTS.md §7): <H… / D… relacionados>
Estado: <pendiente (Fase N) | reproducido | …>
```

Cada función que implemente una fórmula cita la ecuación (`Ec. (4), p.11`) y, si el código de los autores difiere del texto, lo indica con su hallazgo. Los docstrings van en español; los identificadores, en inglés.
