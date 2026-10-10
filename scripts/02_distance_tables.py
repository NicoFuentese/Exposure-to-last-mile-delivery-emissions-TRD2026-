"""Reproduce las tres columnas de distancia de las Tablas 4 (dinámico) y 5 (estático).

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/02_distance_tables.py

Entradas (datos confidenciales, no versionados), en data/replication_package_v2/00_data/:
    hexagon_model_median_wednesday_alternative_metrics_RM.csv, datosxhexagono.csv
Salidas:  outputs/as_published/tables/table4_distance_columns.csv y table5_distance_columns.csv
Código:   src/lastmile_exposure/reporting/marginal_tables.py  (ver docs/paper_map.md)

Columnas: `ols_k` (OLS con todas las filas), `ols_kpos` (modelo de dos partes, H7) y
`ols_logk` (log de K̃ sobre K̃>0, coeficiente crudo, H8). La columna ZINB y las estrellas de
significancia se añaden en fases posteriores. Solo variante `as_published`: la distancia no se
puede convertir a hora local con los datos disponibles (H19).

Sale con código 1 si alguna celda difiere del paper más de su redondeo (4 decimales).
"""

import sys

from lastmile_exposure import config
from lastmile_exposure.panel import distance_frame
from lastmile_exposure.reporting.marginal_tables import distance_marginal_table
from lastmile_exposure.validation.paper_tables import (
    MARGINAL_TOLERANCE,
    compare_columns,
    load_table4,
    load_table5,
)

COLUMNS = {
    "ols_k": MARGINAL_TOLERANCE,
    "ols_kpos": MARGINAL_TOLERANCE,
    "ols_logk": MARGINAL_TOLERANCE,
}


def main() -> int:
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = True
    for name, static, reference in (
        ("table4", False, load_table4()),
        ("table5", True, load_table5()),
    ):
        table = distance_marginal_table(distance_frame(static=static))
        path = out_dir / f"{name}_distance_columns.csv"
        table.round(4).to_csv(path, index=False)
        report = compare_columns(table, reference, COLUMNS)
        good = bool(report["ok"].all())
        ok &= good
        print(f"{name} ({'estático' if static else 'dinámico'}) -> {path}")
        print(f"  celdas comparadas: {len(report)}, dentro de tolerancia: {report['ok'].sum()}")
        print("  máx. |diferencia| por columna:")
        print(report.groupby("column")["abs_diff"].max().round(6).to_string())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
