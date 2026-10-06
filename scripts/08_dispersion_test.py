"""Test de Cameron-Trivedi (dispersion 7,73) con nuestros datos, comparado con el paper.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/08_dispersion_test.py     # rápido: un Poisson de 178.304 filas por tabla

Entrada: data/replication_package/00_data/ (datos confidenciales, no versionados)
Salida:  outputs/as_published/tables/cameron_trivedi.csv
Código:  src/lastmile_exposure/inference/dispersion.py (docs/paper_map.md)

El estadistico principal es el del paper (Poisson dinamico con los 11 regresores; H0: dispersion
= 1). El Poisson estatico y la dispersion de Pearson son cifras secundarias que no se comparan con
el paper. Criterio: error relativo <= 1 % respecto de 7,73 (AGENTS.md D2), dispersion > 1 y
p < 0,001. Termina con codigo 1 si el dinamico no cumple.
"""

import sys

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.inference.dispersion import dispersion_report
from lastmile_exposure.panel import count_frame
from lastmile_exposure.validation.paper_tables import DISPERSION_TOLERANCE, load_paper_scalars


def main() -> int:
    paper = float(load_paper_scalars()["cameron_trivedi_dispersion"])
    limit = DISPERSION_TOLERANCE.limit(paper)
    rows = []
    for tag, static in (("dynamic", False), ("static", True)):
        report = dispersion_report(count_frame(static=static))
        test = report.test
        row = {
            "tabla": tag, "alpha": test.alpha, "dispersion": test.dispersion, "se": test.se,
            "statistic": test.statistic, "pvalue": test.pvalue, "pearson": report.pearson,
            "n_params": report.n_params, "nobs": test.nobs,
            "paper": paper if not static else float("nan"),
            "abs_diff": abs(test.dispersion - paper) if not static else float("nan"),
            "limit": limit if not static else float("nan"),
        }  # fmt: skip
        rows.append(row)
    table = pd.DataFrame(rows)
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    table.round(6).to_csv(out_dir / "cameron_trivedi.csv", index=False)

    dyn = table[table["tabla"] == "dynamic"].iloc[0]
    ok = bool(dyn["abs_diff"] <= limit and dyn["dispersion"] > 1 and dyn["pvalue"] < 0.001)
    print(
        table[["tabla", "dispersion", "statistic", "pvalue", "pearson"]]
        .round(4)
        .to_string(index=False)
    )
    print(
        f"\npaper: {paper}  | dinamico (principal): {dyn['dispersion']:.3f}  "
        f"dif = {dyn['abs_diff']:.3f}  (limite {limit:.3f}, {100 * dyn['abs_diff'] / paper:.2f} %)"
    )
    print("estatico y Pearson: cifras secundarias, no se comparan con el paper")
    print(f"-> {out_dir / 'cameron_trivedi.csv'}")
    print("REPRODUCE (dentro de la tolerancia)" if ok else "NO reproduce dentro de la tolerancia")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
