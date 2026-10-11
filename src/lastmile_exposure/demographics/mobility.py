"""Movilidad de cada grupo: distancia de Wasserstein mañana → tarde y su ranking (Tabla 2).

Paper: §3.1 y Tabla 2, columnas "Wasserstein Dist." y "Mobility Rank" (p.5 y p.7)
Código de los autores: 04_descriptives/people_summary_table.R (paquete v2, 2026-10-10); antes, solo
    las ventanas 10-12 y 20-22 de heatmaps_to_latex.R
Hallazgos (AGENTS.md §7): H15, H24, D10
Estado: dos métodos. (1) Lectura determinista del texto del paper (Fase 3): NO reproduce los
    valores publicados (error máx. 0,14; 12 de 15 rankings). (2) Método del script de los autores
    (2026-10-10): muestra aleatoria SIN semilla de 5.000 hexágonos, así que los valores publicados
    son una sola extracción y no se pueden reproducir exactamente; aquí se corre con muchas
    semillas y se compara contra la distribución (`mobility_over_seeds`, `summarize_seeds`).
    Validado: normalización por la mediana y ranking (contra la Tabla 2), la corrección del
    transporte óptimo (casos exactos y contraste con un programa lineal) y el costo geodésico
    (contra la elipsoide WGS84).

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

import os
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

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
    return _transport_cost(
        p,
        q,
        len(coords),
        lambda src, dst: ot.dist(coords[src], coords[dst], metric="euclidean"),
        max_iter,
    )


def _transport_cost(
    p: np.ndarray,
    q: np.ndarray,
    n_points: int,
    cost_between: Callable[[np.ndarray, np.ndarray], np.ndarray],
    max_iter: int,
) -> float:
    """Núcleo de `wasserstein_1`: transporte entre los excedentes de `p` y de `q`.

    `cost_between(src, dst)` devuelve la matriz de costos (len(src) × len(dst)) entre los puntos
    de índices `src` y `dst`; debe ser una distancia (si no, el atajo de transportar solo el
    exceso deja de ser exacto).
    """
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    if p.shape != q.shape or p.shape[0] != n_points:
        raise ValueError("`p`, `q` y `coords` deben tener el mismo número de puntos")
    if (p < 0).any() or (q < 0).any() or p.sum() <= 0 or q.sum() <= 0:
        raise ValueError("Las masas deben ser no negativas y sumar más que 0")
    diff = p / p.sum() - q / q.sum()
    surplus, deficit = np.clip(diff, 0, None), np.clip(-diff, 0, None)
    moved = float(surplus.sum())
    if moved == 0.0:
        return 0.0
    src, dst = np.flatnonzero(surplus > 0), np.flatnonzero(deficit > 0)
    cost = cost_between(src, dst)
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


# =========================================================================================
# Método del script de los autores (04_descriptives/people_summary_table.R, H24)
# =========================================================================================
# El script toma una muestra aleatoria de 5.000 de los 11.144 hexágonos SIN semilla
# (`set.seed` comentada), calcula con ellos una sola matriz de costos (distancia geodésica en km
# entre centroides H3, `geosphere::distm`) y, para cada grupo, la masa de la mañana y de la tarde
# (media de las 3 horas de `población × proporción del grupo`, normalizada a 1 DENTRO de la
# muestra); `transport::wasserstein(p = 1)`; y reporta W / mediana de su categoría. Como la
# muestra cambia en cada corrida, los valores publicados son UNA extracción: aquí se repite el
# cálculo con muchas semillas (`numpy`, no la secuencia de R) y se compara contra la distribución.

AUTHORS_SAMPLE_SIZE = 5_000
DEFAULT_SEEDS = tuple(range(200))
# Radio medio de la Tierra (km). El script usa la elipsoide WGS84 (`distm`); en Santiago la esfera
# difiere ≤ 0,3 % según la dirección, y esa escala se cancela al dividir por la mediana.
EARTH_RADIUS_KM = 6371.0088
BAND_LEVEL = 0.95


@dataclass(frozen=True)
class GroupMasses:
    """Masas de cada grupo de la Tabla 2 por hexágono, en la mañana y en la tarde."""

    labels: tuple[str, ...]  # etiquetas de `config.TABLE2_GROUPS`, en ese orden
    hexes: np.ndarray  # (n,) índices H3
    latlon: np.ndarray  # (n, 2) latitud y longitud del centroide, en radianes
    morning: np.ndarray  # (grupos, n) media de las horas 10-12 de población × proporción
    evening: np.ndarray  # (grupos, n) ídem para 20-22


def group_masses(panel: pd.DataFrame) -> GroupMasses:
    """Masa de cada grupo por hexágono: media de `poblacion_flotante × proporción` en la ventana.

    Como en el script de los autores, las ventanas son inclusivas (10-12 y 20-22) y el promedio
    es sobre las horas de la ventana; los hexágonos sin datos en la ventana valen 0.
    """
    hexes = panel["hex"].drop_duplicates().to_numpy()
    latlon = np.radians(np.array([h3.cell_to_latlng(h) for h in hexes]))
    labels, morning, evening = [], [], []
    for label, column, _ in config.TABLE2_GROUPS:
        labels.append(label)
        for hours, store in ((config.MORNING_HOURS, morning), (config.EVENING_HOURS, evening)):
            window = panel[panel["hour"].isin(list(hours))]
            mass = (window[column] * window["poblacion_flotante"]).groupby(window["hex"]).mean()
            store.append(mass.reindex(hexes).fillna(0.0).to_numpy())
    return GroupMasses(tuple(labels), hexes, latlon, np.array(morning), np.array(evening))


def haversine_km(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distancia (km, esfera de radio `EARTH_RADIUS_KM`) entre cada fila de `a` y de `b`.

    `a` (m, 2) y `b` (n, 2) traen (latitud, longitud) en radianes; devuelve la matriz (m, n).
    """
    dlat = b[None, :, 0] - a[:, None, 0]
    dlon = b[None, :, 1] - a[:, None, 1]
    cos_a, cos_b = np.cos(a[:, None, 0]), np.cos(b[None, :, 0])
    h = np.sin(dlat / 2) ** 2 + cos_a * cos_b * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def wasserstein_1_geodesic(
    p: np.ndarray, q: np.ndarray, latlon: np.ndarray, *, max_iter: int = 200_000_000
) -> float:
    """W1 exacto, en km, entre dos distribuciones sobre puntos dados por (lat, lon) en radianes."""
    return _transport_cost(
        p, q, len(latlon), lambda src, dst: haversine_km(latlon[src], latlon[dst]), max_iter
    )


def authors_sample(n_hexes: int, seed: int, size: int = AUTHORS_SAMPLE_SIZE) -> np.ndarray:
    """Índices de la muestra aleatoria de `size` hexágonos (o todos, si hay menos) para `seed`."""
    return np.random.default_rng(seed).choice(n_hexes, size=min(size, n_hexes), replace=False)


def authors_seed_distances(
    masses: GroupMasses, seed: int, size: int = AUTHORS_SAMPLE_SIZE
) -> pd.Series:
    """W1 (km) de cada grupo mañana → tarde con la muestra de la semilla `seed`.

    Dentro de la muestra, cada distribución se normaliza a masa 1 (como el script).
    """
    idx = authors_sample(len(masses.hexes), seed, size)
    latlon = masses.latlon[idx]
    values = [
        wasserstein_1_geodesic(masses.morning[k][idx], masses.evening[k][idx], latlon)
        for k in range(len(masses.labels))
    ]
    return pd.Series(values, index=list(masses.labels), name=seed)


_WORKER: dict = {}


def _init_worker(masses: GroupMasses, size: int) -> None:
    _WORKER.update(masses=masses, size=size)


def _run_seed(seed: int) -> pd.Series:
    return authors_seed_distances(_WORKER["masses"], seed, _WORKER["size"])


def _empty_seeds(labels: Sequence[str]) -> pd.DataFrame:
    return pd.DataFrame(
        columns=list(labels), index=pd.Index([], dtype="int64", name="seed"), dtype=float
    )


def _read_checkpoint(path: Path, labels: Sequence[str]) -> pd.DataFrame:
    """Semillas ya calculadas en `path` (vacío si no existe); exige las mismas 15 columnas."""
    if not path.exists() or path.stat().st_size == 0:
        return _empty_seeds(labels)
    saved = pd.read_csv(path, index_col="seed")
    if list(saved.columns) != list(labels):
        raise ValueError(f"{path} no tiene las columnas de los grupos de la Tabla 2")
    return saved


def _append_checkpoint(path: Path, row: pd.Series) -> None:
    """Agrega la fila de una semilla al archivo parcial (con encabezado si está vacío)."""
    new_file = not path.exists() or path.stat().st_size == 0
    row.to_frame().T.rename_axis("seed").to_csv(
        path, mode="a", header=new_file, float_format="%.10g"
    )


def mobility_over_seeds(
    masses: GroupMasses,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    *,
    size: int = AUTHORS_SAMPLE_SIZE,
    workers: int | None = None,
    progress: Callable[[int, int], None] | None = None,
    checkpoint: Path | None = None,
    resume: bool = False,
) -> pd.DataFrame:
    """W1 (km) de los 15 grupos para cada semilla: marco con una fila por semilla.

    Cada semilla toma ~1 minuto por núcleo con 5.000 hexágonos. `workers=None` usa los núcleos
    menos dos; `workers=1` corre en el mismo proceso. `progress(hechas, total)` se llama al
    terminar cada semilla. El resultado no depende de `workers`.

    Con `checkpoint` cada semilla terminada se agrega a ese CSV, de modo que una interrupción no
    pierda lo avanzado. Sin `resume` el archivo se parte de cero; con `resume=True` se retoman
    las semillas que ya están en él (sus valores se leen con 10 cifras significativas; el
    llamador es responsable de que el archivo venga de los mismos datos y del mismo `size`).
    """
    seeds = list(seeds)
    kept = _empty_seeds(masses.labels)
    if checkpoint is not None:
        if resume:
            kept = _read_checkpoint(checkpoint, masses.labels)
        elif checkpoint.exists():
            checkpoint.unlink()
    pending = [s for s in seeds if s not in kept.index]
    already = len(seeds) - len(pending)
    if workers is None:
        workers = max(1, (os.cpu_count() or 2) - 2)
    workers = max(1, min(workers, len(pending)))
    rows = []

    def finished(row: pd.Series) -> None:
        rows.append(row)
        if checkpoint is not None:
            _append_checkpoint(checkpoint, row)
        if progress is not None:
            progress(already + len(rows), len(seeds))

    if not pending:
        pass
    elif workers <= 1:
        for seed in pending:
            finished(authors_seed_distances(masses, seed, size))
    else:
        with ProcessPoolExecutor(
            max_workers=workers, initializer=_init_worker, initargs=(masses, size)
        ) as pool:
            for row in pool.map(_run_seed, pending):
                finished(row)
    new = pd.DataFrame(rows)
    parts = [part for part in (kept, new) if len(part)]
    out = pd.concat(parts).loc[seeds]
    out.index.name = "seed"
    return out


def normalized_seeds(raw: pd.DataFrame) -> pd.DataFrame:
    """Valores normalizados por la mediana de su categoría (como la Tabla 2), por semilla."""
    return raw.apply(normalize_by_median, axis=1)


def seed_ranks(raw: pd.DataFrame) -> pd.DataFrame:
    """Ranking de movilidad dentro de cada categoría (1 = más móvil), por semilla."""
    return raw.apply(mobility_rank, axis=1)


def summarize_seeds(
    raw: pd.DataFrame,
    published: pd.Series,
    published_rank: pd.Series,
    *,
    level: float = BAND_LEVEL,
) -> pd.DataFrame:
    """Un renglón por grupo: valor publicado frente a la distribución de las semillas.

    `raw` es la salida de `mobility_over_seeds`; `published` y `published_rank` son el valor y el
    ranking de la Tabla 2, indexados por la etiqueta del grupo. Columnas: `published`,
    `seed_median`, `seed_mean`, `seed_sd`, `band_low` y `band_high` (banda central de `level`),
    `z` (publicado frente a la media y desviación de las semillas), `inside_band`,
    `rank_published`, `rank_mode` (el ranking más frecuente) y `p_rank_published` (fracción de
    semillas con el ranking publicado).
    """
    labels = list(raw.columns)
    norm, ranks = normalized_seeds(raw), seed_ranks(raw)
    low, high = (1 - level) / 2, 1 - (1 - level) / 2
    pub = published.reindex(labels).astype(float)
    pub_rank = published_rank.reindex(labels).astype(int)
    out = pd.DataFrame(
        {
            "published": pub,
            "seed_median": norm.median(),
            "seed_mean": norm.mean(),
            "seed_sd": norm.std(),
            "band_low": norm.quantile(low),
            "band_high": norm.quantile(high),
        }
    )
    out["z"] = (out["published"] - out["seed_mean"]) / out["seed_sd"]
    out["inside_band"] = (out["published"] >= out["band_low"]) & (
        out["published"] <= out["band_high"]
    )
    out["rank_published"] = pub_rank
    out["rank_mode"] = ranks.mode().iloc[0].astype(int)
    out["p_rank_published"] = [(ranks[c] == pub_rank[c]).mean() for c in labels]
    return out


def seed_agreement(
    raw: pd.DataFrame,
    published: pd.Series,
    published_rank: pd.Series,
    *,
    level: float = BAND_LEVEL,
) -> dict:
    """Resumen global de qué tan compatible es la Tabla 2 publicada con las semillas.

    Devuelve: `n_seeds`, `n_groups`, `n_inside_band`, `n_abs_z_gt_2`, `p_all_ranks` (fracción de
    semillas con los 15 rankings iguales a los publicados), `p_ranks_by_dimension`,
    `p_extremes` (por dimensión, la fracción de semillas con el mismo grupo más móvil y el mismo
    menos móvil que el publicado) y `error_min/median/max` (máx. |normalizado − publicado| por
    semilla).
    """
    summary = summarize_seeds(raw, published, published_rank, level=level)
    norm, ranks = normalized_seeds(raw), seed_ranks(raw)
    labels = list(raw.columns)
    pub, pub_rank = summary["published"], summary["rank_published"]
    dims = pd.Series({g: config.DIMENSION_OF[g] for g in labels})
    by_dimension, extremes = {}, {}
    for dim in ("sex", "age", "seg"):
        cols = list(dims[dims == dim].index)
        by_dimension[dim] = float((ranks[cols] == pub_rank[cols]).all(axis=1).mean())
        top, bottom = pub[cols].idxmax(), pub[cols].idxmin()
        extremes[dim] = {
            "top": top,
            "p_top": float((norm[cols].idxmax(axis=1) == top).mean()),
            "bottom": bottom,
            "p_bottom": float((norm[cols].idxmin(axis=1) == bottom).mean()),
        }
    error = (norm - pub).abs().max(axis=1)
    return {
        "n_seeds": len(raw),
        "n_groups": len(labels),
        "n_inside_band": int(summary["inside_band"].sum()),
        "n_abs_z_gt_2": int((summary["z"].abs() > 2).sum()),
        "p_all_ranks": float((ranks == pub_rank).all(axis=1).mean()),
        "p_ranks_by_dimension": by_dimension,
        "p_extremes": extremes,
        "error_min": float(error.min()),
        "error_median": float(error.median()),
        "error_max": float(error.max()),
    }
