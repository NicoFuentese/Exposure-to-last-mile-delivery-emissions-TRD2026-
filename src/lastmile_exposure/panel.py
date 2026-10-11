"""Fusión hexágono-hora: variable resultado + regresores demográficos (Fig. 3).

Paper: §4, Fig. 3 ("Data fusion": matriz hexágono-hora con `Ỹ_hi`, `K̃_hi` y `D_hi`)
Código de los autores: 04_modeling_wedenesday.R (merge por `hex`, `hour`) y, para el enfoque
    estático, el `merge(..., by = "hex")` de summary_results_static*.R
Hallazgos (AGENTS.md §7): H8, H11, H13, H14
Estado: implementado (Fase 3) para las bases finales del paquete y (Fase 5) reconstrucción
    desde los archivos diarios, en hora UTC (`rebuild_*_frame` con `local=False`, que reproduce las
    bases publicadas) o en hora local (`local_*_frame`, sensibilidad). La construcción desde el
    GPS crudo no es posible con los datos actuales (D7).

Cada función devuelve un DataFrame con una fila por (hex, hour) y las columnas: `hex`, `hour`,
`comuna`, la variable resultado y los 11 regresores de `config.REGRESSORS`. Con `static=True`
los regresores son los residenciales (iguales en todas las horas de un hexágono).

Los marcos reconstruidos desde los archivos diarios usan como esqueleto la base publicada
(mismo orden de filas, misma demografía y comuna) y solo reemplazan la variable resultado.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import add_gse_de
from lastmile_exposure.demographics.static import static_shares
from lastmile_exposure.exposure.vehicles_counts import median_vehicles
from lastmile_exposure.exposure.vehicles_distance import median_distance
from lastmile_exposure.io.daily_counts import load_daily_counts
from lastmile_exposure.io.daily_metrics import load_daily_metrics
from lastmile_exposure.io.panel import load_counts_dataset, load_distance_dataset
from lastmile_exposure.io.static import load_static_raw
from lastmile_exposure.timeutils.local_time import local_wednesdays

_ID_COLUMNS = ["hex", "hour", "comuna"]


def attach_regressors(outcome_df: pd.DataFrame, outcome: str, *, static: bool) -> pd.DataFrame:
    """Marco de modelación: `hex`, `hour`, `comuna`, `outcome` y los 11 regresores.

    `outcome_df` trae `hex`, `hour`, `comuna`, `outcome` y, para el enfoque dinámico, la
    demografía por hora (`gse_d` y `gse_e`, que se combinan en `gse_de`). Con `static=True` los
    regresores se toman de `datosxhexagono.csv` (H8).
    """
    if not static:
        df = add_gse_de(outcome_df)
        return df[[*_ID_COLUMNS, outcome, *config.REGRESSORS]].copy()
    shares = static_shares(load_static_raw())
    merged = outcome_df[[*_ID_COLUMNS, outcome]].merge(
        shares[["hex", *config.REGRESSORS]], on="hex", how="left"
    )
    if merged[list(config.REGRESSORS)].isna().any().any():
        raise ValueError("Hexágonos sin demografía estática")
    return merged


def distance_frame(*, static: bool = False) -> pd.DataFrame:
    """Marco de modelación de distancia: `median_distance` (K̃, metros) y regresores."""
    return attach_regressors(load_distance_dataset(), config.OUTCOME_DISTANCE, static=static)


def count_frame(*, static: bool = False) -> pd.DataFrame:
    """Marco de modelación de conteos: `vehicles` = `round(median_vehicles)` y regresores.

    El código de los autores redondea con `round()` de R (mitades al par: 0,5 → 0; 1,5 → 2),
    que coincide con `numpy.round` (H11). El 3,3 % de las filas tiene medianas x,5.
    """
    return _count_frame_from_raw(load_counts_dataset(), static=static)


def _count_frame_from_raw(raw: pd.DataFrame, *, static: bool) -> pd.DataFrame:
    raw = raw.assign(vehicles=np.round(raw[config.OUTCOME_COUNT]))
    return attach_regressors(raw, "vehicles", static=static)


def restrict_hours(frame: pd.DataFrame, hours: Iterable[int]) -> pd.DataFrame:
    """Filas de `frame` en las horas `hours` (mismo orden); p. ej. la base publicada en 7-19."""
    return frame[frame["hour"].isin(list(hours))].reset_index(drop=True)


# --- Reconstrucción desde los archivos diarios (Fase 5) -----------------------------------
def _daily_in_hours(daily: pd.DataFrame, hours: Iterable[int], *, local: bool) -> pd.DataFrame:
    """Marco diario con las horas `hours`: en hora local (miércoles locales) o con etiqueta UTC."""
    if local:
        return local_wednesdays(daily, hours)
    return daily[daily["hour"].isin(list(hours))].reset_index(drop=True)


def rebuild_count_frame(
    daily: pd.DataFrame,
    *,
    static: bool = False,
    hours: Iterable[int] = config.HOURS,
    local: bool = False,
) -> pd.DataFrame:
    """Marco de conteos rehecho desde los conteos diarios (`io.daily_counts`, con `hours=None`).

    Con `local=False` y `hours=config.HOURS` reproduce exactamente `count_frame` (la base
    publicada, hora UTC); con `local=True` convierte a hora y miércoles locales
    (`timeutils.local_time`) y deja las horas `hours`. La mediana sigue la regla de los autores
    (solo días presentes) y el esqueleto es la base publicada restringida a esas horas.
    """
    hours = list(hours)
    skeleton = restrict_hours(load_counts_dataset(), hours)
    medians = median_vehicles(_daily_in_hours(daily, hours, local=local), skeleton[["hex", "hour"]])
    raw = skeleton.drop(columns=[config.OUTCOME_COUNT, "count_wednesdays"]).merge(
        medians, on=["hex", "hour"], how="left", validate="one_to_one"
    )
    return _count_frame_from_raw(raw, static=static)


def rebuild_distance_frame(
    daily: pd.DataFrame,
    *,
    static: bool = False,
    hours: Iterable[int] = config.HOURS,
    local: bool = False,
) -> pd.DataFrame:
    """Marco de distancia rehecho desde las métricas diarias (`io.daily_metrics`, `hours=None`).

    Igual que `rebuild_count_frame`: con `local=False` y `hours=config.HOURS` reproduce
    `distance_frame`; con `local=True` usa hora y miércoles locales.
    """
    hours = list(hours)
    skeleton = restrict_hours(load_distance_dataset(), hours)
    medians = median_distance(_daily_in_hours(daily, hours, local=local), skeleton[["hex", "hour"]])
    raw = skeleton.drop(columns=["median_distance", "median_time", "count_wednesdays"]).merge(
        medians, on=["hex", "hour"], how="left", validate="one_to_one"
    )
    return attach_regressors(raw, config.OUTCOME_DISTANCE, static=static)


def local_count_frame(
    *, static: bool = False, daily: pd.DataFrame | None = None, hours=config.LOCAL_COMPLETE_HOURS
) -> pd.DataFrame:
    """Marco de conteos en hora local `America/Santiago` (variante `local_time`), horas 7-19.

    `daily` son los conteos diarios con las 24 horas UTC (`load_daily_counts(hours=None)`); si no
    se pasa, se leen. Pasarlos evita releer los 42 archivos al hacer el dinámico y el estático.
    """
    daily = load_daily_counts(hours=None) if daily is None else daily
    return rebuild_count_frame(daily, static=static, hours=hours, local=True)


def local_distance_frame(
    *, static: bool = False, daily: pd.DataFrame | None = None, hours=config.LOCAL_COMPLETE_HOURS
) -> pd.DataFrame:
    """Marco de distancia en hora local `America/Santiago` (variante `local_time`), horas 7-19.

    `daily` son las métricas diarias con las 24 horas UTC (`load_daily_metrics(hours=None)`).
    """
    daily = load_daily_metrics(hours=None) if daily is None else daily
    return rebuild_distance_frame(daily, static=static, hours=hours, local=True)
