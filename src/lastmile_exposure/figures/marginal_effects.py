"""Efectos marginales por GSE y edad (ZINB azul, OLS 'no zero' rojo): Figs. 6, 8, 9 y 10.

Paper: Fig. 6 (GSE, dinámico), Fig. 8 (edad, dinámico), Fig. 9 (GSE, estático) y Fig. 10 (edad,
    estático); pp.13-16
Código de los autores: `plot_dual_axis` en 02_estimation/summary_results*.R (lee la tabla impresa y
    le quita las estrellas)
Hallazgos (AGENTS.md §7): H7, H34
Estado: implementado (Fase 7). Réplica del dibujo, no de los píxeles: mismas series, mismo orden
    de categorías, mismo eje doble y mismos colores y marcadores, con matplotlib en vez de ggplot.

Eje doble (H34): el eje derecho NO es un eje independiente. El script de los autores reescala la
serie roja (OLS `K̃>0`, metros) con `scale_factor = diff(range(azul)) / diff(range(rojo))` y
`offset = min(azul) − min(rojo) · scale_factor`, de modo que el mínimo y el máximo de la serie roja
caen exactamente sobre los de la azul. Las dos curvas siempre tienen sus picos a la misma altura:
la figura solo permite comparar **formas**, no magnitudes. `dual_axis_scaling` lo reproduce.

Las figuras se construyen con la API orientada a objetos (`matplotlib.figure.Figure`), sin
`pyplot`, así que no dependen de ninguna ventana gráfica.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

SEG_ORDER = ("D+E", "C3", "C2", "C1b", "C1a", "AB")  # orden del eje x de los autores
AGE_ORDER = ("Under 25", "25-34", "35-44", "45-54", "55-64", "65+")
GROUPS = {"seg": SEG_ORDER, "age": AGE_ORDER}
X_LABELS = {"seg": "Socioeconomic Group", "age": "Age Group"}
BLUE_LABEL = "Marginal Effect (Vehicles, ZINB)"
RED_LABEL = "Marginal Effect (Distance, OLS, no zero)"
BLUE_COLUMN, RED_COLUMN = "zinb", "ols_kpos"  # columnas de las Tablas 4 y 5
BLUE, RED = "blue", "red"
TICKS = {"nbins": 5, "steps": [1, 2, 5, 10]}  # ~5 marcas por eje, como los cortes de ggplot
FIGURES = {  # figura del paper → (tabla, grupo)
    "fig6_seg_dynamic": ("dynamic", "seg"),
    "fig8_age_dynamic": ("dynamic", "age"),
    "fig9_seg_static": ("static", "seg"),
    "fig10_age_static": ("static", "age"),
}


def figure_data(table: pd.DataFrame, group: str) -> pd.DataFrame:
    """Puntos de una figura: `label`, `zinb` (azul) y `ols_kpos` (rojo), en el orden de los autores.

    `table` trae `label`, `zinb` y `ols_kpos` (las Tablas 4/5 reproducidas, o las impresas). Las
    categorías de referencia (65+ y AB) valen 0, como en la tabla.
    """
    if group not in GROUPS:
        raise ValueError(f"`group` debe ser una de {tuple(GROUPS)}, no {group!r}")
    order = list(GROUPS[group])
    indexed = table.set_index("label")
    missing = [label for label in order if label not in indexed.index]
    if missing:
        raise KeyError(f"Faltan categorías en la tabla: {missing}")
    data = indexed.loc[order, [BLUE_COLUMN, RED_COLUMN]].astype(float).reset_index()
    if data[[BLUE_COLUMN, RED_COLUMN]].isna().any().any():
        raise ValueError("La tabla tiene valores vacíos en las columnas de la figura")
    return data


def dual_axis_scaling(blue: np.ndarray, red: np.ndarray) -> tuple[float, float]:
    """`(scale_factor, offset)` que llevan el rango de `red` sobre el de `blue` (H34).

    Es el cálculo de `plot_dual_axis` de los autores: la serie roja se dibuja como
    `red · scale_factor + offset`. Falla si la serie roja es constante (rango cero).
    """
    blue, red = np.asarray(blue, dtype=float), np.asarray(red, dtype=float)
    span_red = float(red.max() - red.min())
    if span_red == 0:
        raise ValueError("La serie roja es constante: no se puede reescalar el eje derecho")
    scale = float(blue.max() - blue.min()) / span_red
    return scale, float(blue.min() - red.min() * scale)


def plot_effects(table: pd.DataFrame, group: str, *, title: str | None = None) -> Figure:
    """Figura de efectos marginales por `group` (`"seg"` o `"age"`) con eje doble.

    Azul continuo con círculos: ZINB, eje izquierdo (vehículos). Rojo discontinuo con triángulos:
    OLS `K̃>0`, eje derecho (metros), reescalado como en el código de los autores (H34). Sin título
    por defecto: en el paper la información va en la leyenda de la figura.
    """
    data = figure_data(table, group)
    blue, red = data[BLUE_COLUMN].to_numpy(), data[RED_COLUMN].to_numpy()
    scale, offset = dual_axis_scaling(blue, red)
    x = np.arange(len(data))

    fig = Figure(figsize=(10, 7), facecolor="white")
    ax = fig.subplots()
    ax.plot(x, blue, color=BLUE, marker="o", markersize=10, linewidth=3, solid_capstyle="round")
    ax.plot(
        x, red * scale + offset, color=RED, marker="^", markersize=10, linewidth=3, linestyle="--"
    )
    ax.set_xticks(x, labels=data["label"])
    ax.set_xlabel(X_LABELS[group], fontsize=16)
    ax.set_ylabel(BLUE_LABEL, color=BLUE, fontsize=16)
    secondary = ax.secondary_yaxis(
        "right", functions=(lambda y: (y - offset) / scale, lambda m: m * scale + offset)
    )
    secondary.set_ylabel(RED_LABEL, color=RED, fontsize=16)

    ax.yaxis.set_major_locator(MaxNLocator(**TICKS))
    secondary.yaxis.set_major_locator(MaxNLocator(**TICKS))
    # Estilo de `theme_minimal`: sin marco ni marcas, cuadrícula gris tenue
    ax.tick_params(axis="x", labelsize=14, length=0)
    ax.tick_params(axis="y", labelsize=14, labelcolor=BLUE, length=0)
    secondary.tick_params(labelsize=14, labelcolor=RED, length=0)
    for spine in (*ax.spines.values(), *secondary.spines.values()):
        spine.set_visible(False)
    ax.grid(True, color="#EBEBEB", linewidth=1.0)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=18)
    fig.tight_layout()
    return fig


def save_figure(
    fig: Figure, base_path: Path, *, dpi: int = 300, suffixes: tuple[str, ...] = (".png", ".pdf")
) -> list[Path]:
    """Guarda `fig` como PNG y PDF (o los `suffixes` pedidos); devuelve las rutas escritas.

    `base_path` va sin extensión.
    """
    base_path.parent.mkdir(parents=True, exist_ok=True)
    paths = []
    for suffix in suffixes:
        path = base_path.with_suffix(suffix)
        fig.savefig(path, dpi=dpi, facecolor="white")
        paths.append(path)
    return paths
