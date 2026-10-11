# ¿Llegamos a las conclusiones del paper?

Síntesis de la réplica (estado al 2026-10-11). El detalle y las fuentes de cada cifra están en `AGENTS.md` (se citan los hallazgos H* y decisiones D*).

## Respuesta corta

**Sí en lo esencial, con matices.** Las figuras reproducen los resultados del paper con los mismos valores (Figs. 6, 8, 9 y 10: diferencia ≤ 1·10⁻⁴ frente a las Tablas 4 y 5 impresas) y confirman sus conclusiones **cualitativas** principales, que además se mantienen al corregir la zona horaria. No se confirman la magnitud del 24 % para hombres ni la significancia estadística de varios efectos que el paper imprime.

Dos precisiones para leerlo bien:

- **Las desviaciones no son de nuestra implementación.** Se replicó «tal cual el paquete» y los coeficientes coinciden con los publicados. Las desviaciones son del original: hora UTC en los camiones frente a hora local en la población (H1), estrellas impresas calculadas con una base de 2 miércoles (H26), cluster `NULL` en el ZINB estático (H26) y (1−π) aplicado dos veces en el efecto marginal (H10).
- **Las figuras muestran puntos, no incertidumbre.** Respaldan patrones; la significancia hay que sostenerla con las tablas.

## Qué conclusión sostiene cada cosa

| Conclusión del paper | Figuras (mismos valores) | Con la hora corregida (H33) | Respaldo estadístico, con el método declarado (cluster por comuna) |
|---|---|---|---|
| **U invertida por GSE** (modelo dinámico) | ✅ | ✅ se mantiene | ✅ La clase media es significativa: `***` en OLS `K̃>0` para C1a, C1b, C2 y C3, y en el ZINB `***` en C1a, C2 y C3 y `*` en C1b |
| **Pico en 25–34 años** | ✅ | ✅ | ✅ `***` en el ZINB y en OLS `K̃>0` |
| **C1b: de lo más expuesto en distancia (dinámico) a negativo en conteo (estático)** | ✅ en los puntos (ZINB: +2,67 → −14,28) | ✅ | ⚠️ **Débil.** En el estático, C1b no es significativo con cluster por comuna. El paper lo imprime con `***` porque su script no agrupa (cluster `NULL`, H26) |
| **Hombres ~24 % más expuestos** | no aparece en las figuras | — | ❌ **No se sostiene.** Viene del modelo log y deja de ser significativo (p = 0,116); los autores lo reconocen (H31, H32). En conteo, hombre dinámico sí es `***`, pero el cambio de signo en el estático no es significativo |

Con el método declarado (cluster por comuna), el ZINB estático tiene solo 4 de 11 celdas con alguna estrella y ninguna con `***` (Tabla 5; `scripts/06_inference.py`, variante `paper_text`). Las estrellas impresas del paper no se reproducen con ningún método y los autores reconocen que no salen del método correcto (H31, H32): el objetivo de validación de las estrellas son sus tablas regeneradas, que sí se reproducen 88/88.

## Cautelas

- **Reproducibilidad computacional, no réplica independiente.** Se parte de los datos intermedios de los autores; no se tiene el GPS crudo ni los datos de Entel.
- **Eje derecho reescalado** en las Figs. 6, 8, 9 y 10 (H34): comparan formas, no magnitudes entre series.
- **Fig. 1:** escalas de color 1.511 y 7.073 frente a 1600 y 7000 del paper; el patrón se reproduce (H35). **Fig. 7:** factores derivados de sus propias barras, no una estimación independiente de emisiones (H36). **Fig. 2:** no reproducible sin el GPS crudo; hay un sustituto rotulado (H35).
- **Sensibilidad a la hora local:** corregirla cambia los coeficientes alrededor de 8–12 % en mediana (el modelo log, 32 %) y ningún cambio de signo ocurre en un efecto significativo (H33).

## Cómo decirlo

> Las figuras reproducen exactamente los resultados del paper y confirman sus conclusiones cualitativas principales: la U invertida por GSE, el pico en 25–34 y el cambio de C1b entre el enfoque dinámico y el estático. Estas se mantienen al corregir la zona horaria. No se confirman la magnitud del 24 % para hombres ni la significancia de varios efectos que el paper imprime, algo que los propios autores reconocen. La diferencia dinámico–estático de C1b solo es significativa con el cluster que su script omite por error.

## Dónde se comprueba

- Figuras: `python scripts/14_figures.py` y `python scripts/15_maps.py` (salidas en `docs/figures/`, ver su README).
- Estrellas: `python scripts/06_inference.py` (variantes `paper_text` y `authors_script`).
- Sensibilidad a la hora y las cuatro conclusiones: `python scripts/13_local_time_sensitivity.py` (`reporting/sensitivity.py`, `robustness_checks`).
- Todo lo anterior está respaldado por pruebas: `pytest` (ver `AGENTS.md` §12).
