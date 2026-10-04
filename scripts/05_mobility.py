"""Distancia de Wasserstein y ranking de movilidad de la Tabla 2, y su comparación con el paper.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/05_mobility.py                  # calcula los 15 transportes (~10 minutos)
    python scripts/05_mobility.py --use-reference  # usa los valores guardados en reference/mobility

Entrada: data/replication_package/00_data/miercoles_rm.csv (datos confidenciales, no versionados)
Salida:  outputs/as_published/tables/table2_with_mobility.csv
Código:  src/lastmile_exposure/demographics/mobility.py y reporting/table2.py (docs/paper_map.md)

Implementa el método DESCRITO en el paper (W1 exacto en 2D, costo euclídeo en metros, masa del
grupo = share x población en 10-12 h y 20-22 h). NO reproduce los valores publicados (error máx.
~0,14 sobre los normalizados; 12 de 15 rankings; AGENTS.md H24): el script informa la brecha y
termina con código 0 aunque no coincidan, porque no es un fallo del cálculo sino un método no
identificado. A diferencia de los scripts 01 a 04, su código de salida no mide la fidelidad.
"""

import argparse
import sys

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import (
    mobility_distances,
    mobility_rank,
    normalize_by_median,
)
from lastmile_exposure.io.panel import load_panel
from lastmile_exposure.reporting.table2 import table2
from lastmile_exposure.validation.paper_tables import load_mobility_reference, load_table2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--use-reference", action="store_true", help="no recalcula (rápido)")
    args = parser.parse_args()

    panel = load_panel()
    if args.use_reference:
        raw = load_mobility_reference()
    else:
        raw = mobility_distances(
            panel, progress=lambda label, w: print(f"  {label:9s} W1 = {w:10.3f} m", flush=True)
        )
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = table2(panel, mobility_raw=raw)
    result.round(5).to_csv(out_dir / "table2_with_mobility.csv", index=False)

    published = load_table2().set_index("variable")
    labels = [label for label, _, _ in config.TABLE2_GROUPS]
    pub_value = published.loc[labels, "wasserstein"].astype(float)
    pub_rank = published.loc[labels, "mobility_rank"].astype(int)
    norm = normalize_by_median(raw.reindex(labels))
    ranks = mobility_rank(norm)
    report = pd.DataFrame(
        {"publicado": pub_value, "calculado": norm, "dif": norm - pub_value,
         "rank_pub": pub_rank, "rank_calc": ranks}
    )  # fmt: skip
    print(report.round(5).to_string())
    same = int((ranks == pub_rank).sum())
    sex_age = [g[0] for g in config.TABLE2_GROUPS if g[2] != "seg"]
    sex_age_ok = int((ranks == pub_rank)[sex_age].sum())
    print(
        f"\nmax|dif| = {report['dif'].abs().max():.4f}; rankings iguales: {same}/15 "
        f"(sexo y edad: {sex_age_ok}/8)"
    )
    print(
        "NO reproduce la Tabla 2 publicada (método de los autores no identificado, H24)."
        if same < 15 or report["dif"].abs().max() > 1e-5
        else "Reproduce la Tabla 2 publicada."
    )
    print(f"-> {out_dir / 'table2_with_mobility.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
