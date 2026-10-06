"""Modelo de dos partes (logit + OLS): la columna real "OLS K̃>0" de las Tablas 4 y 5.

Paper: Tablas 4-5, columna 3 (el paper la describe como "OLS con K̃>0"); Figs. 6-10 ("OLS no zero")
Código de los autores: rama `ziols` de `get_marginal_effects` en 02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H7, H12
Estado: implementado (Fase 3). Estimación puntual reproducida (22 celdas no nulas, diferencia
    máxima ≤ 5·10⁻⁵, el redondeo a 4 decimales del paper). El SE del AME del código original es
    una aproximación burda; se replica tal cual en `inference/cluster.py` (Fase 4A).
"""

from dataclasses import dataclass

import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import BinaryResultsWrapper
from statsmodels.regression.linear_model import RegressionResultsWrapper

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors
from lastmile_exposure.models.marginal_effects import two_part_ame
from lastmile_exposure.models.ols import fit_ols_positive


@dataclass(frozen=True)
class TwoPartResult:
    """Resultado del modelo de dos partes."""

    logit: BinaryResultsWrapper  # P(K̃ > 0 | D), todas las filas
    ols: RegressionResultsWrapper  # K̃ | K̃ > 0, filas positivas
    pr_nonzero: float  # media de las probabilidades ajustadas del logit
    mean_nonzero: float  # media de los valores ajustados del OLS (filas positivas)
    ame: pd.Series  # efecto marginal promedio por regresor


def fit_two_part(df: pd.DataFrame, outcome: str = config.OUTCOME_DISTANCE) -> TwoPartResult:
    """Ajusta el modelo de dos partes y calcula el AME de cada regresor."""
    x = sm.add_constant(regressors(df), has_constant="add")
    logit = sm.Logit((df[outcome] > 0).astype(float), x).fit(disp=0, maxiter=200)
    if not logit.mle_retvals["converged"]:
        raise RuntimeError("El logit del modelo de dos partes no convergió")
    ols = fit_ols_positive(df, outcome)
    pr = float(logit.predict(x).mean())
    mean_nonzero = float(ols.fittedvalues.mean())
    ame = two_part_ame(
        logit.params.drop("const"),
        ols.params.drop("const"),
        pr_nonzero=pr,
        mean_nonzero=mean_nonzero,
    )
    return TwoPartResult(logit, ols, pr, mean_nonzero, ame)
