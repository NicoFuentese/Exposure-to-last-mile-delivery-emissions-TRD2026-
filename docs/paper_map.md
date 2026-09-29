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
| §4.1.1, Fig. 4 | Conteo `Y_hi` y mediana `Ỹ_hi` | `exposure/vehicles_counts.py`, `exposure/aggregate.py` | ⏳ verificado en exploración (la mediana sobre días presentes reproduce el 100 %, H2), **sin código todavía**; hoy se usan las medianas ya calculadas del paquete |
| §4.1.2, Fig. 5 | Distancia `K_hi` y mediana `K̃_hi` | `exposure/vehicles_distance.py` | 🚫 faltan distancias diarias (H4, D7) |
| §4, Fig. 3 | Fusión hexágono‑hora | `panel.py` | ✅ sobre las bases finales del paquete; 🚫 desde el GPS crudo (D7) |
| §3.2 / H1 | UTC → `America/Santiago` | `timeutils/local_time.py` | ⏳ verificada en exploración (H18), **sin código todavía** (Fase 5) |
| §4.2 | Regresores `D_hi`, referencias, D+E | `demographics/shares.py`, `config.py` | ✅ |

## Modelos

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| Ec. (1)–(3) | ZINB, inflación constante, NB2 | `models/zinb.py` | ⏳ |
| Ec. (4) | Efecto marginal del ZINB | `models/marginal_effects.py` | ⏳ (H10) |
| Ec. (5)–(6) | OLS de `K̃` y `log K̃` | `models/ols.py` | ✅ Tablas 4–5, cols. 2 y 4 (H8) |
| Tablas 4–5, col. 3 | "OLS `K̃>0`" = logit + OLS | `models/two_part.py` | ✅ (H7) |

## Inferencia

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| §4.2.3 | Errores estándar agrupados por comuna (51) | `inference/cluster.py` | ⏳ |
| §4.2.3 | I de Moran (0,4694 / 0,4756) | `inference/moran.py` | ⏳ |
| §4.2.1 | Cameron–Trivedi (7,73), π | `inference/dispersion.py` | ⏳ |
| Tablas 4–5 | Estrellas de significancia | `reporting/significance.py` | ⏳ |

## Resultados y figuras

| Paper | Qué es | Módulo | Estado |
|---|---|---|---|
| Tabla 2 | Descriptivos de la población flotante | `reporting/table2.py` | ✅ (H15); `scripts/01_table2.py`. Wasserstein pendiente (D10) |
| Tablas 4 y 5 | Efectos marginales (4 columnas) | `reporting/marginal_tables.py` | 🟡 3 de 4 columnas (falta ZINB) y sin estrellas; `scripts/02_distance_tables.py` |
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

## Convención de documentación

Todo módulo abre con un docstring con estas cuatro líneas (lo comprueba `tests/test_structure.py`):

```
Paper: <sección / ecuación / tabla / figura y página>
Código de los autores: <script R y función, o "(no está en el paquete)">
Hallazgos (AGENTS.md §7): <H… / D… relacionados>
Estado: <pendiente (Fase N) | reproducido | …>
```

Cada función que implemente una fórmula cita la ecuación (`Ec. (4), p.11`) y, si el código de los autores difiere del texto, lo indica con su hallazgo. Los docstrings van en español; los identificadores, en inglés.
