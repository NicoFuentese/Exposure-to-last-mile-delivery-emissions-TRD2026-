"""Las columnas de distancia de las Tablas 4 y 5 coinciden con el paper (H7, H8). Requiere datos.

Cubre 3 columnas (`ols_k`, `ols_kpos` = modelo de dos partes, `ols_logk`) x 13 filas x 2 tablas.
La columna ZINB y las estrellas se validarán en las fases 3b y 4.
"""

import pytest

from lastmile_exposure.validation.paper_tables import (
    MARGINAL_TOLERANCE,
    compare_columns,
    load_table4,
    load_table5,
)

COLUMNS = dict.fromkeys(("ols_k", "ols_kpos", "ols_logk"), MARGINAL_TOLERANCE)


@pytest.mark.parametrize(
    ("key", "loader"), [("dynamic", load_table4), ("static", load_table5)], ids=["tabla4", "tabla5"]
)
def test_distance_columns_match_paper(distance_tables, key, loader):
    report = compare_columns(distance_tables[key], loader(), COLUMNS)
    assert len(report) == 3 * 13
    bad = report[~report["ok"]]
    assert bad.empty, f"Celdas fuera de tolerancia:\n{bad}"


def test_plain_ols_on_positives_is_not_the_paper_column(distance_tables):
    """Guardia de H7: la columna "OLS K̃>0" NO es un OLS simple sobre las filas positivas."""
    from lastmile_exposure.models.ols import fit_ols_positive
    from lastmile_exposure.panel import distance_frame

    plain = fit_ols_positive(distance_frame()).params["gse_c1b"]
    paper = distance_tables["dynamic"].set_index("variable").loc["gse_c1b", "ols_kpos"]
    assert plain == pytest.approx(474.78, abs=0.01)
    assert paper == pytest.approx(388.3212, abs=6e-5)
    assert abs(plain - paper) > 50
