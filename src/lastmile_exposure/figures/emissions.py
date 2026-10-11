"""Fig. 7: gramos extra de NOx y PM por mes según el GSE (barras).

Paper: Fig. 7 (p.14, «Average monthly extra grams of pollutant by SEG»)
Código de los autores: (no está en el paquete: no hay script de la Fig. 7)
Hallazgos (AGENTS.md §7): §5.7, D10, H36
Estado: implementado (Fase 7). Réplica del dibujo con gramos DERIVADOS de las barras impresas
    (`reporting.emissions`): la figura reproduce la del paper, pero los factores de emisión de la
    fuente y el multiplicador mensual no se conocen.

NOx en naranja oscuro y PM en azul, barras agrupadas por GSE en el orden de las Figs. 6 y 9
(D+E, C3, C2, C1b, C1a, AB), con la cifra sobre cada barra (un decimal), leyenda en un recuadro
abajo a la derecha y tipografía serif como la de LaTeX. Solo contiene coeficientes por un
factor constante: se puede versionar (`docs/figures/`).
"""

import numpy as np
import pandas as pd
from matplotlib import rc_context
from matplotlib.figure import Figure

FIG7_NAME = "fig7_emissions_seg"
NOX_COLOR, PM_COLOR = "#CC6633", "#4D4DFF"
Y_LABEL = "Grams of Pollutant"
BAR_WIDTH = 0.34
FONT = {  # parecida a la de LaTeX; el signo menos sale de las matemáticas de matplotlib
    "font.family": "cmr10",
    "mathtext.fontset": "cm",
    "axes.formatter.use_mathtext": True,
}


def _label(value: float) -> str:
    """Cifra de la barra con un decimal y sin ceros finales; los negativos, en modo matemático.

    La fuente serif (`cmr10`) no trae el signo menos tipográfico, que sí dibuja `$-…$`.
    """
    text = f"{round(float(value), 1):g}"
    return f"${text}$" if text.startswith("-") else text


def plot_emissions(grams: pd.DataFrame) -> Figure:
    """Barras de NOx y PM por GSE a partir de `grams` (`label`, `nox_g`, `pm_g`)."""
    x = np.arange(len(grams))
    with rc_context(FONT):
        fig = Figure(figsize=(8, 5.6), facecolor="white")
        ax = fig.subplots()
        for offset, column, color in ((-0.19, "nox_g", NOX_COLOR), (0.19, "pm_g", PM_COLOR)):
            values = grams[column].to_numpy(dtype=float)
            ax.bar(x + offset, values, width=BAR_WIDTH, color=color, linewidth=0)
            for xi, value in zip(x + offset, values, strict=True):
                ax.annotate(
                    _label(value),
                    (xi, value),
                    xytext=(0, 4 if value >= 0 else -4),
                    textcoords="offset points",
                    ha="center",
                    va="bottom" if value >= 0 else "top",
                    fontsize=10,
                )
        ax.set_xticks(x, labels=grams["label"], fontsize=15)
        ax.set_ylabel(Y_LABEL, fontsize=16)
        ax.tick_params(axis="y", labelsize=14)
        ax.set_ylim(-26, 78)
        ax.set_yticks([-20, 0, 20, 40, 60])
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_bounds(-0.6, len(grams) - 0.4)
        ax.legend(
            handles=[
                ax.patches[0],  # primera barra de NOx
                ax.patches[len(grams)],  # primera barra de PM
            ],
            labels=["NOx", "PM"],
            loc="lower right",
            ncols=2,
            frameon=True,
            edgecolor="black",
            fancybox=False,
            fontsize=15,
        )
        fig.tight_layout()
    return fig
