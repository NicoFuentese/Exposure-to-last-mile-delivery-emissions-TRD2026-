"""Fusión hexágono-hora: variable resultado + regresores demográficos (Fig. 3).

Paper: §4, Fig. 3 ("Data fusion": matriz hexágono-hora con `Ỹ_hi`, `K̃_hi` y `D_hi`)
Código de los autores: 04_modeling_wedenesday.R (merge por `hex`, `hour`) y, para el enfoque
    estático, el `merge(..., by = "hex")` de summary_results_static*.R
Hallazgos (AGENTS.md §7): H8, H11, H13, H14
Estado: implementado (Fase 3) para las bases finales del paquete. La construcción desde el
    GPS crudo no es posible con los datos actuales (D7).

Cada función devuelve un DataFrame con una fila por (hex, hour) y las columnas: `hex`, `hour`,
`comuna`, la variable resultado y los 11 regresores de `config.REGRESSORS`. Con `static=True`
los regresores son los residenciales (iguales en todas las horas de un hexágono).
"""

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import add_gse_de
from lastmile_exposure.demographics.static import static_shares
from lastmile_exposure.io.panel import load_counts_dataset, load_distance_dataset
from lastmile_exposure.io.static import load_static_raw

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
    raw = load_counts_dataset()
    raw = raw.assign(vehicles=np.round(raw[config.OUTCOME_COUNT]))
    return attach_regressors(raw, "vehicles", static=static)
