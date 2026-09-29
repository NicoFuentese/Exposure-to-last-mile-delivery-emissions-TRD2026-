"""Shares demográficos dinámicos y regresores del modelo.

Paper: §4.2, p.10 (categorías de referencia: Mujer, AB, 65+); p.12 (D y E combinados)
Código de los autores: `prep_data` y `model_vars` en 02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H8, H13
Estado: implementado (Fase 3).
"""

import pandas as pd

from lastmile_exposure import config


def add_gse_de(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una copia con `gse_de = gse_d + gse_e` (D y E se combinan en los modelos)."""
    out = df.copy()
    out["gse_de"] = out["gse_d"] + out["gse_e"]
    return out


def regressors(df: pd.DataFrame) -> pd.DataFrame:
    """Los 11 regresores del modelo (shares en [0, 1]), en el orden de `config.REGRESSORS`.

    Las categorías de referencia (Mujer, AB, 65+) quedan fuera para evitar colinealidad
    perfecta. Requiere `gse_de` (ver `add_gse_de`).
    """
    missing = [c for c in config.REGRESSORS if c not in df.columns]
    if missing:
        raise KeyError(f"Faltan regresores: {missing}")
    return df[list(config.REGRESSORS)].astype(float)
