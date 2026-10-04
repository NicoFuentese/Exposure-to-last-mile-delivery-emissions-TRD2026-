"""Movilidad de cada grupo: distancia de Wasserstein mañana → tarde y su ranking (Tabla 2).

Paper: §3.1 y Tabla 2, columnas "Wasserstein Dist." y "Mobility Rank" (p.5 y p.7)
Código de los autores: (no está en el paquete: ningún script calcula Wasserstein; solo las
    ventanas 10-12 y 20-22 de heatmaps_to_latex.R)
Hallazgos (AGENTS.md §7): H15, H24, D10
Estado: implementado (Fase 3) COMO LO DESCRIBE EL PAPER; NO reproduce los valores publicados.
    Validado: normalización por la mediana y ranking (contra la Tabla 2) y la corrección
    matemática del transporte óptimo (casos exactos y contraste con un programa lineal). Fidelidad:
    error máx. 0,14 en los valores normalizados y 12 de 15 rankings; el método exacto de los
    autores no está identificado (~30 hipótesis probadas, ver AGENTS.md H24).

El paper compara, para cada grupo sociodemográfico, su distribución espacial en la mañana
(10-12 h) con la de la tarde (20-22 h) mediante la distancia de Wasserstein (Earth Mover's):
"el desplazamiento geográfico medio mínimo para transformar la distribución de la mañana en la
de la tarde". Después ordena los grupos de más a menos móvil (1 = mayor movilidad).

Método implementado (la lectura directa del paper):
- Distribución de un grupo en una ventana: población del grupo por hexágono (`share × población`,
  sumada en las horas de la ventana, 10-12 y 20-22 inclusivas) normalizada a masa 1.
- Distancia: W1 (transporte óptimo exacto en 2D) con costo euclídeo entre los centros de los
  hexágonos, en metros (`config.METRIC_CRS`). Se calcula con `POT` (`ot.emd2`) sobre el
  exceso de masa de un lado (`(p-q)+`) hacia el otro (`(q-p)+`): para costos que son distancias
  mover la masa que ya coincide nunca conviene, así que el resultado es exactamente el mismo con
  una matriz 4 veces más pequeña.

Lo que muestran los valores publicados (`[Derivado]`, verificado sobre las 15 filas):
- **Normalización:** dentro de cada dimensión (sexo, edad, GSE) el valor publicado es
  `W_grupo / mediana de W en esa dimensión`: la mediana publicada vale exactamente 1,00000 en
  las tres (por eso C2 = 1 y Hombre + Mujer = 2). La escala absoluta (metros o km) desaparece.
- **Ranking:** orden descendente del valor, dentro de cada dimensión.
"""

from collections.abc import Callable, Sequence

import h3
import numpy as np
import ot
import pandas as pd
from pyproj import Transformer

from lastmile_exposure import config


def _dimension(index: pd.Index) -> pd.Index:
    unknown = [g for g in index if g not in config.DIMENSION_OF]
    if unknown:
        raise KeyError(f"Grupos que no son de la Tabla 2: {unknown}")
    return index.map(config.DIMENSION_OF)


def normalize_by_median(raw: pd.Series) -> pd.Series:
    """Normaliza las distancias de Wasserstein como la Tabla 2: `W / mediana(W)` por dimensión.

    `raw` es una serie indexada por la etiqueta del grupo (`"Male"`, `"25-34"`, `"AB"`, …; ver
    `config.TABLE2_GROUPS`). Cada valor se divide por la mediana de su dimensión (sexo, edad o
    GSE), de modo que la mediana de cada dimensión queda en 1. Es invariante a la escala de `raw`.
    """
    dimension = _dimension(raw.index)
    return raw / raw.groupby(dimension).transform("median")


def mobility_rank(values: pd.Series) -> pd.Series:
    """Ranking de movilidad dentro de cada dimensión: 1 = el grupo con mayor distancia.

    Los empates comparten el mejor puesto (`method="min"`). Devuelve enteros.
    """
    dimension = _dimension(values.index)
    return values.groupby(dimension).rank(ascending=False, method="min").astype(int)


def hex_coordinates(hexes: Sequence[str]) -> np.ndarray:
    """Centros de los hexágonos H3 en metros (`config.METRIC_CRS`), array `(n, 2)` = (x, y)."""
    lat, lon = zip(*(h3.cell_to_latlng(h) for h in hexes), strict=True)
    x, y = Transformer.from_crs("EPSG:4326", config.METRIC_CRS, always_xy=True).transform(
        np.array(lon), np.array(lat)
    )
    return np.column_stack([x, y])


def wasserstein_1(
    p: np.ndarray, q: np.ndarray, coords: np.ndarray, *, max_iter: int = 200_000_000
) -> float:
    """Distancia de Wasserstein-1 (Earth Mover's) exacta entre dos distribuciones sobre `coords`.

    `p` y `q` son masas no negativas sobre los mismos puntos (se normalizan a suma 1) y `coords`
    un array `(n, 2)`; el costo es la distancia euclídea, en las unidades de `coords`. Resuelve el
    transporte solo entre `(p-q)+` y `(q-p)+`, lo que es exacto para costos que son distancias.
    Lanza `RuntimeError` si el solver no converge.
    """
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    if p.shape != q.shape or p.shape[0] != len(coords):
        raise ValueError("`p`, `q` y `coords` deben tener el mismo número de puntos")
    if (p < 0).any() or (q < 0).any() or p.sum() <= 0 or q.sum() <= 0:
        raise ValueError("Las masas deben ser no negativas y sumar más que 0")
    diff = p / p.sum() - q / q.sum()
    surplus, deficit = np.clip(diff, 0, None), np.clip(-diff, 0, None)
    moved = float(surplus.sum())
    if moved == 0.0:
        return 0.0
    src, dst = np.flatnonzero(surplus > 0), np.flatnonzero(deficit > 0)
    cost = ot.dist(coords[src], coords[dst], metric="euclidean")
    value, log = ot.emd2(
        surplus[src] / moved, deficit[dst] / moved, cost, numItermax=max_iter, log=True
    )
    if log["warning"] is not None:
        raise RuntimeError(f"El transporte óptimo no convergió: {log['warning']}")
    return float(value) * moved


def group_distribution(
    panel: pd.DataFrame, column: str, hours: Sequence[int], hexes: Sequence[str]
) -> np.ndarray:
    """Masa del grupo por hexágono en la ventana `hours`, normalizada a suma 1.

    `column` es la proporción del grupo en el panel (p. ej. `gse_ab`); la masa de un hexágono es
    la suma, sobre las horas de la ventana, de `proporción × poblacion_flotante`. El resultado
    sigue el orden de `hexes`.
    """
    window = panel[panel["hour"].isin(list(hours))]
    mass = (window[column] * window["poblacion_flotante"]).groupby(window["hex"]).sum()
    values = mass.reindex(list(hexes)).fillna(0.0).to_numpy()
    if values.sum() <= 0:
        raise ValueError(f"El grupo {column!r} no tiene población en las horas {tuple(hours)}")
    return values / values.sum()


def mobility_distances(
    panel: pd.DataFrame, progress: Callable[[str, float], None] | None = None
) -> pd.Series:
    """W1 en metros de cada grupo de la Tabla 2 entre la mañana (10-12) y la tarde (20-22).

    Devuelve una serie indexada por la etiqueta del grupo. Con el panel completo tarda ~10
    minutos (15 transportes óptimos de ~6.000 × 7.000 puntos). `progress(etiqueta, W1)` se llama
    al terminar cada grupo.
    """
    hexes = panel["hex"].drop_duplicates().to_numpy()
    coords = hex_coordinates(hexes)
    out = {}
    for label, column, _ in config.TABLE2_GROUPS:
        morning = group_distribution(panel, column, config.MORNING_HOURS, hexes)
        evening = group_distribution(panel, column, config.EVENING_HOURS, hexes)
        out[label] = wasserstein_1(morning, evening, coords)
        if progress is not None:
            progress(label, out[label])
    return pd.Series(out, name="w1_m")
