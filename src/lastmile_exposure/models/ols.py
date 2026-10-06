"""OLS de distancia: K̃ (todas las filas) y log K̃ (solo K̃ > 0).

Paper: Ec. (5)-(6), §4.2.2, p.11
Código de los autores: `feols(distance ~ model_vars)` y `feols(log_distance ~ model_vars)` en
    02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H8, H12
Estado: implementado (Fase 3). Estimaciones puntuales reproducidas exactamente (Tablas 4 y 5,
    columnas OLS `K̃` y `log K̃`). Errores estándar con cluster por comuna:
    `inference/cluster.py` (Fase 4A).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import RegressionResultsWrapper

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors


def fit_ols(
    df: pd.DataFrame, outcome: str = config.OUTCOME_DISTANCE, *, log_positive: bool = False
) -> RegressionResultsWrapper:
    """Ajusta `outcome ~ 1 + regresores` por MCO.

    - `log_positive=False`: todas las filas (columna "OLS K̃" de las Tablas 4-5). El efecto
      marginal de cada regresor es su coeficiente (Ec. 6).
    - `log_positive=True`: `log(outcome)` solo con `outcome > 0` (columna "OLS log K̃").
      Se reporta el coeficiente crudo, no `coef × distancia media` (H9).
    """
    data = df
    y = data[outcome].astype(float)
    if log_positive:
        data = data[y > 0]
        y = np.log(data[outcome].astype(float))
    x = sm.add_constant(regressors(data), has_constant="add")
    return sm.OLS(y, x).fit()


def fit_ols_positive(
    df: pd.DataFrame, outcome: str = config.OUTCOME_DISTANCE
) -> RegressionResultsWrapper:
    """OLS de `outcome` sobre las filas con `outcome > 0`. Es la parte 2 del modelo de dos partes.

    OJO: NO es la columna "OLS K̃>0" de las Tablas 4-5; esa columna es el efecto marginal del
    modelo de dos partes (H7, `models/two_part.py`).
    """
    data = df[df[outcome] > 0]
    x = sm.add_constant(regressors(data), has_constant="add")
    return sm.OLS(data[outcome].astype(float), x).fit()
