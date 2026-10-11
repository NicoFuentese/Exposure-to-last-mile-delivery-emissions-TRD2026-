# Informe de reproducción

- **Generado:** 2026-10-11 08:46
- **Versión del código:** c1fa8c3
- **Modo de la ejecución:** standard
- **Python y librerías:** Python 3.12.3 · numpy 2.5.3 · pandas 3.0.6 · scipy 1.18.1 · statsmodels 0.15.0 · h3 4.5.0 · matplotlib 3.11.2

**Resultado:** sin fallas: 10 ✅ · 3 🟡 · 3 ℹ️ · 0 ❌ · 0 ⏭️.

✅ coincide con el paper (exacto o al redondeo/tolerancia acordada) · 🟡 no coincide y la causa está documentada (se vigila que no cambie) · ℹ️ resultado propio sin objetivo del paper · ❌ falla · ⏭️ omitido (falta la salida)

## Tablas

| Ítem | Objetivo | Resultado | Estado | Ref. |
|---|---|---|---|---|
| Tabla 2: media, desviación y porcentajes | al redondeo impreso | 62/62 celdas; dif. máx. 0.04992 | ✅ dentro de la tolerancia | H15 |
| Tabla 4 (dinámica): 4 columnas (ZINB y 3 OLS) | al redondeo impreso (≤ 6e-05) | 52/52 celdas; dif. máx. 5.7e-05 (ZINB 5.7e-05) | ✅ dentro de la tolerancia | H8, H23 |
| Tabla 5 (estática): 4 columnas (ZINB y 3 OLS) | al redondeo impreso (≤ 6e-05) | 52/52 celdas; dif. máx. 4.9e-05 (ZINB 4.4e-05) | ✅ dentro de la tolerancia | H8, H23 |

## Medianas

| Ítem | Objetivo | Resultado | Estado | Ref. |
|---|---|---|---|---|
| Mediana de conteos (42 miércoles) | idénticas a la base del paper | 178,304 filas; dif. máx. 0 | ✅ exacto | H2 |
| Mediana de distancia y tiempo (41 miércoles) | idénticas a la base del paper | 178,304 filas; dif. máx. 3.1e-11 | ✅ exacto | H30 |

## Inferencia

| Ítem | Objetivo | Resultado | Estado | Ref. |
|---|---|---|---|---|
| Estrellas de la Tabla 4 contra las tablas de los autores | 44/44 | 44/44 (variante paper_text) | ✅ exacto | H31 |
| Estrellas de la Tabla 5 contra las tablas de los autores | 44/44 | 44/44 (variante authors_script) | ✅ exacto | H31 |
| Estrellas impresas en el paper (no son objetivo) | — | 23/44 (Tabla 4) y 38/44 (Tabla 5) *(los autores reconocen que no salen del método correcto)* | ℹ️ informativo | H31, H32 |
| Test de Cameron–Trivedi (dispersión 7,73) | 7.73 (±1 %) | 7.750 (dif. 0.26 %) | ✅ dentro de la tolerancia | H27 |
| I de Moran (0,4694 y 0,4756) | 0,4694 / 0,4756 | 0.419 / 0.430 (lectura literal) *(la especificación no está identificada)* | 🟡 desviación documentada | H28 |

## Movilidad

| Ítem | Objetivo | Resultado | Estado | Ref. |
|---|---|---|---|---|
| Wasserstein de la Tabla 2 (200 semillas) | valores publicados | 13/15 dentro de la banda del 95 % (fuera: D, E) *(los autores muestrearon sin semilla: no es reproducible exactamente)* | 🟡 desviación documentada | H24 |

## Diagnóstico

| Ítem | Objetivo | Resultado | Estado | Ref. |
|---|---|---|---|---|
| π del ZINB (el paper no lo reporta) | — | π̂ = 0 en la frontera; IC 95 % [0, 7.7e-05] y [0, 4.4e-05] (dinámica y estática) | ℹ️ informativo | H29 |

## Sensibilidad

| Ítem | Objetivo | Resultado | Estado | Ref. |
|---|---|---|---|---|
| Conclusiones del paper con la hora local corregida | — | 4/4 conclusiones se mantienen | ℹ️ informativo | H33 |

## Figuras

| Ítem | Objetivo | Resultado | Estado | Ref. |
|---|---|---|---|---|
| Figs. 6, 8, 9 y 10 (efectos marginales) | mismos puntos que las Tablas 4 y 5 | dif. máx. 0.0001 *(el eje derecho está reescalado: comparan formas)* | ✅ dentro de la tolerancia | H34 |
| Fig. 7 (gramos de NOx y PM) | 12 etiquetas impresas | 12/12 etiquetas iguales *(el factor se deriva de las propias barras: no es una estimación independiente)* | ✅ dentro de la tolerancia | H36 |
| Fig. 1: escalas de color de los mapas | 1600 (AB) y 7000 (C1b) | AB 1511 frente a 1600; C1b 7073 frente a 7000 *(el patrón se reproduce; la causa de la diferencia de escala no se conoce)* | 🟡 desviación documentada | H35 |

## Pasos de la ejecución

| Paso | Script | Estado | Duración | Salida | Motivo |
|---|---|---|---|---|---|
| 01 | `scripts/01_table2.py` | ok | 6 s | 0 | — |
| 02 | `scripts/02_distance_tables.py` | ok | 9 s | 0 | — |
| 03 | `scripts/03_zinb_tables.py` | ok | 37 s | 0 | — |
| 04 | `scripts/04_median_counts.py` | ok | 26 s | 0 | — |
| 11 | `scripts/11_median_distance.py` | ok | 24 s | 0 | — |
| 05 | `scripts/05_mobility.py --use-reference` | ok | 6 s | 0 | — |
| 06 | `scripts/06_inference.py` | ok | 53 s | 0 | — |
| 08 | `scripts/08_dispersion_test.py` | ok | 10 s | 0 | — |
| 09 | `scripts/09_moran.py` | ok | 6 s | 0 | — |
| 10 | `scripts/10_zero_inflation.py` | ok | 224 s | 0 | — |
| 12 | `scripts/12_mobility_seeds.py --use-reference` | ok | 7 s | 0 | — |
| 13 | `scripts/13_local_time_sensitivity.py` | ok | 99 s | 0 | — |
| 14 | `scripts/14_figures.py` | ok | 7 s | 0 | — |
| 15 | `scripts/15_maps.py` | ok | 22 s | 0 | — |
