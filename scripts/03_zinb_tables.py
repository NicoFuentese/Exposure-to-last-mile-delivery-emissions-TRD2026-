"""Reproduce la columna ZINB de las Tablas 4 (dinámico) y 5 (estático); completa las 4 columnas.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/03_zinb_tables.py        # ~2 minutos (dos ajustes ZINB de ~1 minuto)

Entradas (datos confidenciales, no versionados), en data/replication_package/00_data/:
    hexagon_model_median_wednesdays_RM.csv,
    hexagon_model_median_wednesday_alternative_metrics_RM.csv, datosxhexagono.csv
Salidas:  outputs/as_published/tables/table4_complete_no_stars.csv y table5_complete_no_stars.csv
Código:   src/lastmile_exposure/models/zinb.py y reporting/marginal_tables.py (docs/paper_map.md)

El ZINB usa vehicles = round(median_vehicles) con π constante. La columna `zinb` de la salida usa
la fórmula de efecto marginal del código de los autores ("authors"); el script imprime también la
distancia máxima al paper de las otras fórmulas (H10 en AGENTS.md). Las estrellas de significancia
se añaden en la Fase 4. Solo variante `as_published`.

Sale con código 1 si alguna celda de las cuatro columnas difiere del paper más de su tolerancia.
"""

import sys
import time

from lastmile_exposure import config
from lastmile_exposure.models.marginal_effects import ZINB_FORMULAS
from lastmile_exposure.models.zinb import fit_zinb
from lastmile_exposure.panel import count_frame, distance_frame
from lastmile_exposure.reporting.marginal_tables import (
    distance_marginal_table,
    zinb_marginal_column,
)
from lastmile_exposure.validation.paper_tables import (
    MARGINAL_TOLERANCE,
    ZINB_TOLERANCE,
    compare_columns,
    load_table4,
    load_table5,
)

TOLERANCES = {
    "zinb": ZINB_TOLERANCE,
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
        label = "estatico" if static else "dinamico"
        t0 = time.time()
        result = fit_zinb(count_frame(static=static))
        print(
            f"{name} ({label}): ZINB en {time.time() - t0:.0f} s, {result.n_iter} iteraciones, "
            f"loglike={result.llf:.3f}, max|score|/n={result.max_abs_score:.1e}, "
            f"pi={result.pi:.3e}, theta={result.theta:.4f}"
        )
        table = distance_marginal_table(distance_frame(static=static))
        for formula in ZINB_FORMULAS:
            col = table.assign(zinb=zinb_marginal_column(result, formula))
            diff = compare_columns(col, reference, {"zinb": ZINB_TOLERANCE})["abs_diff"].max()
            print(f"  formula {formula:<13} max|dif| vs paper (columna ZINB): {diff:.4f}")
        table = table.assign(zinb=zinb_marginal_column(result, "authors"))
        path = out_dir / f"{name}_complete_no_stars.csv"
        table.round(4).to_csv(path, index=False)

        report = compare_columns(table, reference, TOLERANCES)
        good = bool(report["ok"].all())
        ok &= good
        print(f"  -> {path}")
        print(
            f"  celdas comparadas: {len(report)}, dentro de tolerancia: {int(report['ok'].sum())}"
        )
        print("  max|dif| por columna:")
        print(report.groupby("column")["abs_diff"].max().round(6).to_string())
        if not good:
            bad = report[~report["ok"]]
            print("  celdas fuera de tolerancia:")
            print(bad.round(4).to_string(index=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
