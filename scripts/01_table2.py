"""Reproduce la Tabla 2 (población flotante) y la compara con el paper.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/01_table2.py

Entrada: data/replication_package_v2/00_data/miercoles_rm.csv (datos confidenciales, no versionados)
Salida:  outputs/as_published/tables/table2.csv
Código:  src/lastmile_exposure/reporting/table2.py  (ver docs/paper_map.md)

Sale con código 1 si alguna celda difiere del paper más de su tolerancia de redondeo.
Wasserstein y ranking de movilidad no se calculan todavía (D10 en AGENTS.md).
"""

import sys

from lastmile_exposure import config
from lastmile_exposure.io.panel import load_panel
from lastmile_exposure.reporting.table2 import table2
from lastmile_exposure.validation.paper_tables import (
    TABLE2_TOLERANCES,
    compare_columns,
    load_table2,
)


def main() -> int:
    result = table2(load_panel())
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.round(4).to_csv(out_dir / "table2.csv", index=False)

    report = compare_columns(result, load_table2(), TABLE2_TOLERANCES)
    print(f"Tabla 2 escrita en {out_dir / 'table2.csv'}")
    print(
        f"Celdas comparadas con el paper: {len(report)}; dentro de tolerancia: {report['ok'].sum()}"
    )
    print(report.groupby("column")["abs_diff"].max().round(4).to_string())
    return 0 if report["ok"].all() else 1


if __name__ == "__main__":
    sys.exit(main())
