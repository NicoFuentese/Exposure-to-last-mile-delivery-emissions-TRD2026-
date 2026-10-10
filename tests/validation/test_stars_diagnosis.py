"""DIAGNÓSTICO con `data_base` (AGENTS.md H26). NO ES UNA RÉPLICA.

Estas pruebas fijan el resultado del diagnóstico para que cualquier cambio avise. No validan la
réplica: `data_base` es la mediana de solo los dos primeros miércoles y sus estrellas no son una
inferencia válida. Con `data_base` y la lógica del script coinciden 78 de 88 estrellas (frente a
61 de 88 con `00_data`); quedan 10 celdas distintas.
"""

import pytest

from lastmile_exposure.validation import stars_diagnosis as diag
from lastmile_exposure.validation.paper_tables import stars_summary

EXPECTED = {
    "dynamic": {"zinb": 10, "ols_k": 7, "ols_kpos": 10, "ols_logk": 9},  # 36/44
    "static": {"zinb": 11, "ols_k": 10, "ols_kpos": 11, "ols_logk": 10},  # 42/44
}
RESIDUAL = {  # las 10 celdas que siguen distintas del paper
    ("dynamic", "zinb", "gse_c1b"),
    ("dynamic", "ols_k", "edad_menor_25"),
    ("dynamic", "ols_k", "edad_35_44"),
    ("dynamic", "ols_k", "edad_55_64"),
    ("dynamic", "ols_k", "gse_c1a"),
    ("dynamic", "ols_kpos", "edad_35_44"),
    ("dynamic", "ols_logk", "edad_35_44"),
    ("dynamic", "ols_logk", "edad_45_54"),
    ("static", "ols_k", "gse_c1a"),
    ("static", "ols_logk", "edad_45_54"),
}


@pytest.fixture(scope="module")
def diagnosis(panel, legacy_data_base):
    return diag.run_diagnosis(write=False)  # ajusta 2 ZINB sobre data_base (~3 min)


@pytest.mark.slow
def test_data_base_diagnostic_is_the_documented_one(diagnosis):
    for tag, (table, report) in diagnosis.items():
        assert stars_summary(report)["matches"].to_dict() == EXPECTED[tag]
        assert (table["fuente"] == diag.SOURCE_LABEL).all()  # cada fila rotulada como diagnóstico
        assert (report["fuente"] == diag.SOURCE_LABEL).all()
    total = sum(int(report["ok"].sum()) for _, report in diagnosis.values())
    assert total == 78


@pytest.mark.slow
def test_data_base_diagnostic_residual_cells(diagnosis):
    cells = set()
    for tag, (_, report) in diagnosis.items():
        bad = diag.residual_cells(report)
        cells |= {(tag, r["column"], r["variable"]) for _, r in bad.iterrows()}
    assert cells == RESIDUAL
