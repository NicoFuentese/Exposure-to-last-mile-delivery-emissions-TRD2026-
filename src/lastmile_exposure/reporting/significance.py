"""Estrellas de significancia y tabla de inferencia de las Tablas 4 y 5.

Paper: Tablas 4 y 5 (`***` p<0,001, `**` p<0,01, `*` p<0,05, `.` p<0,1)
Código de los autores: `add_significance` y `p_values[i] <- 2 * (1 - pnorm(abs(...)))` en
    02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H11, H12, H25, H26, D3
Estado: implementado (Fase 4A): `stars`, `inference_table` (SE y p-valores de las cuatro columnas,
    con cluster por comuna o sin él) y `authors_script_inference_table` (la variante de los scripts
    de los autores, que en el ZINB estático no agrupa por un error de su código, H26). La
    comparación contra las estrellas publicadas vive en `validation.paper_tables.compare_stars`.

Qué z entra en cada columna (como el código de los autores):
- ZINB: `β/se(β)` del bloque de conteo (el factor del efecto marginal se cancela).
- OLS `K̃` y OLS `log K̃`: `β/se(β)` del OLS (en el log, el coeficiente crudo).
- "OLS K̃>0": `AME/se`, con el SE aproximado del modelo de dos partes (H12).
"""

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.inference.cluster import (
    OBSERVATION,
    Inference,
    nb_inference,
    ols_inference,
    two_part_inference,
)
from lastmile_exposure.inference.zinb_sandwich import zinb_inference
from lastmile_exposure.models.ols import fit_ols
from lastmile_exposure.models.two_part import fit_two_part
from lastmile_exposure.models.zinb import ZinbResult
from lastmile_exposure.reporting.marginal_tables import REFERENCE_VARIABLES

# Columnas de las Tablas 4 y 5 (en este orden)
COLUMNS = ("zinb", "ols_k", "ols_kpos", "ols_logk")
ZINB_METHODS = ("zinb", "nb")
SAME_CLUSTER = "same"  # `zinb_cluster`: usar el mismo cluster que los OLS
THRESHOLDS = ((0.001, "***"), (0.01, "**"), (0.05, "*"), (0.1, "."))


def stars(p: float) -> str:
    """Estrellas de un p-valor, con los umbrales del código de los autores (estrictos: `p < u`)."""
    if pd.isna(p):
        return ""
    for threshold, symbol in THRESHOLDS:
        if p < threshold:
            return symbol
    return ""


def nearest_threshold(p: float) -> float:
    """Umbral de significancia más cercano (escala log) a `p`; ubica las celdas al borde."""
    thresholds = np.array([t for t, _ in THRESHOLDS])
    return float(thresholds[np.argmin(np.abs(np.log(thresholds) - np.log(max(p, 1e-300))))])


def inference_table(
    distance_df: pd.DataFrame,
    count_df: pd.DataFrame,
    zinb: ZinbResult,
    *,
    cluster: str | None = "comuna",
    zinb_cluster: str | None = SAME_CLUSTER,
    zinb_method: str = "zinb",
) -> pd.DataFrame:
    """SE, p-valores y estrellas de las cuatro columnas de la Tabla 4 (o 5).

    `distance_df` y `count_df` son `panel.distance_frame()` y `panel.count_frame()` (con la misma
    demografía, dinámica o estática); `zinb` es `fit_zinb(count_df)`. `cluster` es la columna de
    agrupación (`"comuna"`), `None` para los errores sin cluster (variante `summary_results.R`) u
    `inference.cluster.OBSERVATION` (cada fila es su cluster: el `NULL` de R, sin agrupar).
    `zinb_cluster` fija el cluster de la columna ZINB por separado (por defecto, el mismo
    `cluster`): el script estático de los autores usa `OBSERVATION` solo en el ZINB (H26).
    `zinb_method`: `"zinb"` = sandwich del ZINB completo (lo que calcularon los autores, H25) o
    `"nb"` = sandwich de la NB equivalente (π = 0; sensibilidad).

    Devuelve una fila por `config.TABLE_ROWS` con `<col>_se`, `<col>_p` y `<col>_sig` para cada
    columna de `COLUMNS`; las categorías de referencia (65+, AB) quedan en NaN / "".
    """
    if zinb_method not in ZINB_METHODS:
        raise ValueError(f"`zinb_method` debe ser una de {ZINB_METHODS}, no {zinb_method!r}")
    zinb_se = zinb_inference if zinb_method == "zinb" else nb_inference
    zinb_group = cluster if zinb_cluster == SAME_CLUSTER else zinb_cluster
    positive = distance_df[distance_df[config.OUTCOME_DISTANCE] > 0]
    results: dict[str, Inference] = {
        "zinb": zinb_se(zinb, count_df, cluster=zinb_group),
        "ols_k": ols_inference(fit_ols(distance_df), distance_df, cluster=cluster),
        "ols_kpos": two_part_inference(fit_two_part(distance_df), positive, cluster=cluster),
        "ols_logk": ols_inference(
            fit_ols(distance_df, log_positive=True), positive, cluster=cluster
        ),
    }
    table = pd.DataFrame(
        {
            "variable": [v for v, _, _ in config.TABLE_ROWS],
            "label": [lab for _, lab, _ in config.TABLE_ROWS],
            "group": [g for _, _, g in config.TABLE_ROWS],
        }
    )
    is_reference = table["variable"].isin(REFERENCE_VARIABLES)
    for col in COLUMNS:
        inf = results[col]
        se = table["variable"].map(inf.se)
        p = table["variable"].map(inf.p)
        table[f"{col}_se"] = se.mask(is_reference)
        table[f"{col}_p"] = p.mask(is_reference)
        table[f"{col}_sig"] = table[f"{col}_p"].map(stars)
    return table


def authors_script_inference_table(
    distance_df: pd.DataFrame, count_df: pd.DataFrame, zinb: ZinbResult, *, static: bool
) -> pd.DataFrame:
    """Estrellas tal como las calculan los scripts de los autores (`summary_results*_cluster.R`).

    Cluster por comuna en los OLS y en el ZINB dinámico. En el ZINB ESTÁTICO, el script deja
    `cluster_var` en NULL (el marco de vehículos se reduce a `hex, hour, vehicles` y
    `datosxhexagono.csv` no trae `comuna`), así que `vcovCL(zinb, cluster = NULL)` toma cada
    observación como su propio cluster: errores robustos SIN agrupar (H26). Reproducir esto es
    replicar un error del código de los autores; NO es lo que dice el paper (cluster por comuna).
    """
    return inference_table(
        distance_df,
        count_df,
        zinb,
        cluster="comuna",
        zinb_cluster=OBSERVATION if static else SAME_CLUSTER,
    )
