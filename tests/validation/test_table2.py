"""La Tabla 2 calculada desde los datos coincide con la publicada (H15). Requiere los datos."""

from lastmile_exposure.reporting.table2 import table2
from lastmile_exposure.validation.paper_tables import (
    TABLE2_TOLERANCES,
    compare_columns,
    load_table2,
)


def test_table2_matches_paper(panel):
    report = compare_columns(table2(panel), load_table2(), TABLE2_TOLERANCES)
    assert len(report) == 15 * 4 + 2  # 15 grupos x 4 columnas + media y std de la fila total
    bad = report[~report["ok"]]
    assert bad.empty, f"Celdas fuera de tolerancia:\n{bad}"
