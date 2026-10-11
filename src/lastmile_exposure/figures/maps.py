"""Mapas hexagonales: Fig. 1 (población por GSE) y un SUSTITUTO rotulado de la Fig. 2.

Paper: Fig. 1 (p.6: población de SEG AB y SEG C1b, 10-12 h y 20-22 h) y Fig. 2 (p.8)
Código de los autores: 03_heatmaps/heatmaps_to_latex.R (`create_demographic_heatmap`)
Hallazgos (AGENTS.md §7): H24, H35
Estado: Fig. 1 implementada (Fase 7). Réplica del dibujo, no de los píxeles. La Fig. 2 («GPS
    Points per Hexagon») NO se puede reproducir: necesita el GPS crudo de todos los días. Lo que
    hay es un sustituto, `plot_vehicle_proxy`: vehículos (mediana) por hexágono, con el estilo de
    la Fig. 2 (`inferno`, `log1p`), claramente rotulado como tal.

Valor de cada hexágono: la media de las 3 horas de la ventana de `poblacion_flotante × share`, que
es lo que da el script de los autores (media de la población × proporción ponderada por población)
y es la misma masa que usa el Wasserstein (`demographics.mobility.group_masses`, H24). Escala de
color LINEAL y común a las dos ventanas de cada grupo (límite = máximo de ambas), paleta `turbo`,
como en el paper. Ojo (H35): el script de mapas del paquete dibuja con `inferno` y `log1p`, que no
es lo que muestra la Fig. 1 del paper (esa estética coincide con la Fig. 2).

Los mapas muestran valores por hexágono, derivados de los datos confidenciales: se guardan SOLO en
`outputs/` (ignorado por git) y nunca en `docs/figures/` (`tests/test_published_figures.py`).

Se usa la API orientada a objetos de matplotlib (`Figure`), sin `pyplot` ni ventana gráfica.
"""

from collections.abc import Sequence

import h3
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from pyproj import Geod

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import GroupMasses

# Límites del script de los autores (`coord_sf` y el filtro por centroide):
# (lon_min, lon_max, lat_min, lat_max)
BOUNDS = (-70.85, -70.4, -33.7, -33.3)
LON_TICKS = (-70.8, -70.7, -70.6, -70.5, -70.4)
LAT_TICKS = (-33.3, -33.4, -33.5, -33.6, -33.7)
SCALE_KM = 10.0
CMAP = "turbo"  # paleta de la Fig. 1 (azul oscuro → verde → rojo oscuro)
FIG1_GROUPS = ("AB", "C1b")
FIG1_NAME = "fig1_seg_population"
# Copia versionada de la Fig. 1 (decisión del usuario, 2026-10-10) y del sustituto de la Fig. 2
# (2026-10-11): solo PNG y a resolución moderada, comparable a la que publica el paper. El PDF
# vectorial guarda el color exacto de cada hexágono y se queda en outputs/.
PUBLISH_DPI = 150
PUBLISH_MAX_PIXELS = 2000  # ancho máximo del PNG versionado
FIG2_PROXY_NAME = "fig2_proxy_vehicles"  # versionable solo como PNG moderado (como la Fig. 1)
PROXY_HOURS = config.HOURS  # horas 7-22 de la base publicada (etiqueta UTC de los camiones)
PROXY_CMAP = "inferno"  # estilo de la Fig. 2 y del script de los autores
WINDOWS = (
    ("morning", config.MORNING_HOURS),
    ("evening", config.EVENING_HOURS),
)
_GEOD = Geod(ellps="WGS84")


# ------------------------------------------------------------------ geometría
def hex_vertices(hexes: Sequence[str]) -> np.ndarray:
    """Vértices (lon, lat) de cada hexágono H3: arreglo `(n, 6, 2)`."""
    return np.array(
        [[(lng, lat) for lat, lng in h3.cell_to_boundary(cell)] for cell in hexes], dtype=float
    )


def in_bounds(latlon_rad: np.ndarray, bounds: tuple[float, ...] = BOUNDS) -> np.ndarray:
    """Máscara de los hexágonos cuyo centroide (lat, lon en radianes) cae dentro de `bounds`."""
    lat, lon = np.degrees(latlon_rad[:, 0]), np.degrees(latlon_rad[:, 1])
    lon_min, lon_max, lat_min, lat_max = bounds
    return (lon >= lon_min) & (lon <= lon_max) & (lat >= lat_min) & (lat <= lat_max)


def km_to_lon_degrees(km: float, lat: float, lon: float = -70.6) -> float:
    """Grados de longitud que miden `km` kilómetros hacia el este a la latitud `lat` (WGS 84)."""
    lon_east, _, _ = _GEOD.fwd(lon, lat, 90.0, km * 1000.0)
    return float(lon_east - lon)


def _format_lon(x: float) -> str:
    return f"{abs(x):.1f}°{'W' if x < 0 else 'E'}"


def _format_lat(y: float) -> str:
    return f"{abs(y):.1f}°{'S' if y < 0 else 'N'}"


def _scale_bar(ax, bounds, *, segments: int = 4) -> None:
    """Barra de escala de `SCALE_KM` km (segmentos alternados) abajo a la derecha."""
    lon_min, lon_max, lat_min, lat_max = bounds
    lat_mid = (lat_min + lat_max) / 2
    length = km_to_lon_degrees(SCALE_KM, lat_mid, (lon_min + lon_max) / 2)
    x0, y0, height = lon_max - 0.03 - length, lat_min + 0.03, 0.012
    for k in range(segments):
        ax.add_patch(
            Rectangle(
                (x0 + k * length / segments, y0),
                length / segments,
                height,
                facecolor="black" if k % 2 == 0 else "white",
                edgecolor="black",
                linewidth=0.8,
                zorder=5,
            )
        )
    ax.text(x0 - 0.01, y0 + height / 2, f"{SCALE_KM:g} km", ha="right", va="center", fontsize=8)


def _north_arrow(ax, bounds) -> None:
    lon_min, lon_max, lat_min, lat_max = bounds
    x, y_top = lon_max - 0.03, lat_max - 0.02
    ax.annotate(
        "",
        xy=(x, y_top),
        xytext=(x, y_top - 0.07),
        arrowprops={"arrowstyle": "-|>", "color": "black", "linewidth": 1.4},
        zorder=5,
    )
    ax.text(x, y_top - 0.08, "N", ha="center", va="top", fontsize=8, fontweight="bold")


# ------------------------------------------------------------------ un mapa
def plot_hex_map(
    fig: Figure,
    ax,
    vertices: np.ndarray,
    values: np.ndarray,
    *,
    vmin: float,
    vmax: float,
    title: str,
    colorbar_label: str = "Population",
    cmap: str = CMAP,
    bounds: tuple[float, ...] = BOUNDS,
    ticks: Sequence[float] | None = None,
    tick_labels: Sequence[str] | None = None,
) -> PolyCollection:
    """Dibuja `values` (uno por hexágono, mismo orden que `vertices`) en `ax` con su barra de color.

    Escala lineal entre `vmin` y `vmax`; la barra horizontal marca solo los dos extremos, como la
    Fig. 1 del paper, salvo que se pasen `ticks` (y sus `tick_labels`, p. ej. los `exp(x) − 1` de
    una escala log).
    """
    collection = PolyCollection(
        vertices, array=np.asarray(values, dtype=float), cmap=cmap, edgecolors="none"
    )
    collection.set_clim(vmin, vmax)
    ax.add_collection(collection)
    lon_min, lon_max, lat_min, lat_max = bounds
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    # Proporción real (1° de longitud mide cos(lat) de 1° de latitud), fijada en la caja del eje.
    ax.set_aspect("auto")
    ax.set_box_aspect(
        (lat_max - lat_min) / ((lon_max - lon_min) * np.cos(np.radians((lat_min + lat_max) / 2)))
    )
    ax.set_xticks(LON_TICKS, labels=[_format_lon(x) for x in LON_TICKS])
    ax.set_yticks(LAT_TICKS, labels=[_format_lat(y) for y in LAT_TICKS])
    ax.tick_params(labelsize=7, length=2)
    ax.grid(True, color="#CCCCCC", linewidth=0.4)
    ax.set_axisbelow(False)
    ax.set_title(title, fontsize=10, fontweight="bold")
    _scale_bar(ax, bounds)
    _north_arrow(ax, bounds)
    # La barra es un eje insertado en el propio mapa (coordenadas del eje): queda siempre pegada
    # a él, sin depender de la maquetación automática.
    colorbar_axes = ax.inset_axes([0.27, -0.155, 0.46, 0.022])
    colorbar = fig.colorbar(
        collection,
        cax=colorbar_axes,
        orientation="horizontal",
        ticks=[vmin, vmax] if ticks is None else list(ticks),
    )
    labels = [f"{vmin:.0f}", f"{vmax:.0f}"] if tick_labels is None else list(tick_labels)
    colorbar.ax.set_xticklabels(labels, fontsize=8)
    colorbar.ax.set_title(colorbar_label, fontsize=9, pad=3)
    colorbar.outline.set_visible(False)
    return collection


# ------------------------------------------------------------------ Fig. 1
def fig1_data(masses: GroupMasses, groups: Sequence[str] = FIG1_GROUPS) -> dict:
    """Valores de la Fig. 1: por grupo y ventana, la masa de cada hexágono dentro de los límites.

    Devuelve `{"hexes", "vertices", "values": {(grupo, ventana): arreglo}, "vmax": {grupo: máximo}}`
    con la ventana `"morning"` (10-12 h) o `"evening"` (20-22 h). `vmax[grupo]` es el máximo de las
    dos ventanas: la escala de color es común a las dos columnas, como en el paper.
    """
    keep = in_bounds(masses.latlon)
    hexes = np.asarray(masses.hexes)[keep]
    values = {}
    for label in groups:
        k = list(masses.labels).index(label)
        for window in ("morning", "evening"):
            values[(label, window)] = np.asarray(getattr(masses, window)[k])[keep]
    vmax = {
        label: max(values[(label, w)].max() for w in ("morning", "evening")) for label in groups
    }
    return {
        "hexes": hexes,
        "vertices": hex_vertices(hexes),
        "values": values,
        "vmax": vmax,
    }


def plot_fig1(masses: GroupMasses, groups: Sequence[str] = FIG1_GROUPS) -> Figure:
    """Fig. 1: población de cada grupo (filas) en la mañana y en la tarde (columnas).

    Cuatro mapas: SEG AB y SEG C1b, de 10:00 a 12:00 y de 20:00 a 22:00. Escala lineal de 0 al
    máximo de las dos ventanas del grupo, como en el paper (H35).
    """
    data = fig1_data(masses, groups)
    fig = Figure(figsize=(12, 13.2), facecolor="white")
    axes = fig.subplots(
        len(groups),
        len(WINDOWS),
        squeeze=False,
        gridspec_kw={"left": 0.07, "right": 0.97, "top": 0.965, "bottom": 0.09, "hspace": 0.33},
    )
    for row, label in enumerate(groups):
        for col, (window, hours) in enumerate(WINDOWS):
            plot_hex_map(
                fig,
                axes[row, col],
                data["vertices"],
                data["values"][(label, window)],
                vmin=0.0,
                vmax=float(data["vmax"][label]),
                title=f"SEG {label.upper()} Daytime Population "
                f"({hours[0]:02d}:00-{hours[-1]:02d}:00)",
            )
    return fig


# ------------------------------------------------------------------ sustituto de la Fig. 2
def vehicle_means(counts: pd.DataFrame, hours: Sequence[int] = PROXY_HOURS) -> pd.DataFrame:
    """Vehículos (mediana) por hexágono: promedio de `median_vehicles` en las horas `hours`.

    `counts` es la base de conteos del paper (`io.panel.load_counts_dataset()`, con `hex`, `hour` y
    `median_vehicles`). Es lo que dibuja el script de los autores para «vehicles» (media de la
    ventana por hexágono); NO son puntos GPS. Devuelve `hex` y `mean_vehicles`.
    """
    window = counts[counts["hour"].isin(list(hours))]
    means = window.groupby("hex")["median_vehicles"].mean()
    return means.rename("mean_vehicles").reset_index()


def log_colorbar_ticks(vmax: float) -> tuple[list[float], list[str]]:
    """Marcas de la barra de la Fig. 2: 0, 1/3, 2/3 y el máximo del rango `log1p`, con `exp(x) − 1`.

    Es la regla que reproduce las etiquetas 0, 11, 147 y 1807 de la Fig. 2 del paper
    (`log1p(1807) = 7,5`; `exp(2,5) − 1 = 11`; `exp(5) − 1 = 147`).
    """
    ticks = [0.0, vmax / 3, 2 * vmax / 3, vmax]
    return ticks, [f"{np.expm1(t):.0f}" for t in ticks]


def plot_vehicle_proxy(means: pd.DataFrame) -> Figure:
    """SUSTITUTO de la Fig. 2: mapa de vehículos por hexágono (`hex`, `mean_vehicles`).

    NO es la Fig. 2 del paper (puntos GPS por hexágono, que requieren el GPS crudo): muestra la
    mediana de vehículos promediada en las horas 7-22 con el mismo estilo (`inferno`, escala
    `log1p`, barra con las marcas de la Fig. 2). Se rotula como sustituto en el propio título.
    """
    hexes = means["hex"].to_numpy()
    latlon = np.radians([h3.cell_to_latlng(cell) for cell in hexes])
    keep = in_bounds(latlon)
    values = np.log1p(means["mean_vehicles"].to_numpy(dtype=float)[keep])
    vmax = float(values.max())
    ticks, tick_labels = log_colorbar_ticks(vmax)
    fig = Figure(figsize=(8, 8.4), facecolor="white")
    ax = fig.subplots(gridspec_kw={"left": 0.1, "right": 0.95, "top": 0.9, "bottom": 0.14})
    plot_hex_map(
        fig,
        ax,
        hex_vertices(hexes[keep]),
        values,
        vmin=0.0,
        vmax=vmax,
        title="PROXY, NOT Fig. 2 (GPS points): median vehicles per hexagon, mean of hours 7-22",
        colorbar_label="Vehicles",
        cmap=PROXY_CMAP,
        ticks=ticks,
        tick_labels=tick_labels,
    )
    ax.title.set_fontsize(9)
    return fig
