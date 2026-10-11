# Figuras publicadas de la réplica

Esta es la **única carpeta de figuras que se versiona** (`outputs/` está en `.gitignore`). Lo que entra
aquí está autorizado de forma explícita y lo vigila `tests/test_published_figures.py`.

| Archivo | Figura del paper | Contenido |
|---|---|---|
| `fig1_seg_population.png` | Fig. 1 | Mapas de población de SEG AB y SEG C1b, 10–12 h y 20–22 h |
| `fig2_proxy_vehicles.png` | Fig. 2 (**sustituto**) | Vehículos (mediana) por hexágono; NO son puntos GPS |
| `fig6_seg_dynamic` | Fig. 6 | Efectos marginales por GSE, modelo dinámico |
| `fig7_emissions_seg` | Fig. 7 | Gramos de NOx y PM por GSE (coeficientes × una constante derivada, H36) |
| `fig8_age_dynamic` | Fig. 8 | Efectos marginales por edad, modelo dinámico |
| `fig9_seg_static` | Fig. 9 | Efectos marginales por GSE, modelo estático |
| `fig10_age_static` | Fig. 10 | Efectos marginales por edad, modelo estático |

**Figs. 6, 8, 9 y 10** (`.png` a 300 dpi y `.pdf`): solo **coeficientes**, los mismos números de las
Tablas 4 y 5 del paper, que ya están en `reference/paper_tables/`. Azul = ZINB (eje izquierdo,
vehículos); rojo = OLS `K̃>0` (eje derecho, metros). El eje derecho no es independiente: se reescala
para que el mínimo y el máximo de la serie roja caigan sobre los de la azul, igual que en el código de
los autores (`plot_dual_axis`; AGENTS.md H34). Sirven para comparar **formas**, no magnitudes.

**Fig. 1 y sustituto de la Fig. 2** (solo `.png`, 150 dpi): muestran valores **por hexágono**
derivados de los datos confidenciales. Se publican por decisión del usuario (2026-10-10 y
2026-10-11) porque el paper publica la misma Fig. 1 y la distribución espacial de la Fig. 2, y solo
como PNG de resolución moderada: el PDF vectorial guarda el color exacto de cada hexágono y se
queda en `outputs/`. Escala lineal de 0 al máximo de las dos ventanas de cada grupo (AB
1.511 y C1b 7.073, frente a los 1600 y 7000 que imprime el paper; AGENTS.md H35). El sustituto de la Fig. 2 **no es** la Fig. 2 del paper (que cuenta puntos GPS, y no hay GPS crudo):
muestra la mediana de vehículos por hexágono, promediada en las horas 7–22, con el mismo estilo
(`inferno`, `log1p`), y se rotula así en su título. Cualquier otra figura con valores por hexágono
**no** se sube.

**Fig. 7** (`.png` y `.pdf`): los gramos son el efecto OLS `K̃>0` por una constante por contaminante, **derivada de las
barras impresas del paper** (el paper no da los factores de emisión ni el multiplicador mensual); la
figura reproduce la del paper pero no es una estimación independiente (AGENTS.md H36).

**Regenerar:** `python scripts/03_zinb_tables.py`, luego `python scripts/14_figures.py --publish`
(Figs. 6, 7, 8, 9 y 10) y `python scripts/15_maps.py --publish` (Fig. 1). Es una réplica del dibujo, no de
los píxeles (misma serie, orden, ejes y colores; otra tipografía).
