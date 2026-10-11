# Figuras publicadas de la réplica

Esta es la **única carpeta de figuras que se versiona** (`outputs/` está en `.gitignore`). Contiene solo
figuras de **coeficientes**: los mismos números de las Tablas 4 y 5 del paper, que ya están en
`reference/paper_tables/`. Los mapas (Figs. 1 y 2) muestran valores por hexágono derivados de los datos
confidenciales y **no se suben**; se generan solo en `outputs/`.

| Archivo | Figura del paper | Contenido |
|---|---|---|
| `fig6_seg_dynamic` | Fig. 6 | Efectos marginales por GSE, modelo dinámico |
| `fig8_age_dynamic` | Fig. 8 | Efectos marginales por edad, modelo dinámico |
| `fig9_seg_static` | Fig. 9 | Efectos marginales por GSE, modelo estático |
| `fig10_age_static` | Fig. 10 | Efectos marginales por edad, modelo estático |

Cada una en `.png` (300 dpi) y `.pdf`. Azul = ZINB (eje izquierdo, vehículos); rojo = OLS `K̃>0` (eje
derecho, metros).

**Cómo leerlas.** El eje derecho no es independiente: se reescala para que el mínimo y el máximo de la
serie roja caigan sobre los de la azul, igual que en el código de los autores (`plot_dual_axis`; AGENTS.md
H34). Sirven para comparar **formas** entre las dos series, no sus magnitudes.

**Regenerar:** `python scripts/03_zinb_tables.py` y luego `python scripts/14_figures.py --publish`.
Es una réplica del dibujo, no de los píxeles (misma serie, orden, ejes y colores; otra tipografía).
