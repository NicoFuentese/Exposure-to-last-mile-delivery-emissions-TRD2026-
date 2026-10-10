"""Probabilidad de cero estructural (pi) del ZINB con nuestros datos: DIAGNOSTICO, no replica.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/10_zero_inflation.py     # ~4 min: 2 ZINB + sus verosimilitudes perfiladas

Entrada: data/replication_package_v2/00_data/ (datos confidenciales, no versionados)
Salida:  outputs/as_published/tables/zero_inflation.csv          (una fila por tabla)
         outputs/as_published/tables/zero_inflation_profile.csv  (verosimilitud perfilada en pi)
Código:  src/lastmile_exposure/inference/zero_inflation.py (docs/paper_map.md)

El paper NO reporta ningun valor de pi (solo dice que es constante y la interpreta como la
probabilidad de un cero estructural): no hay cifra contra la cual comparar y nada se declara
"reproducido". Se documenta lo que los datos dicen de pi dentro del modelo del paper (pi constante,
mismos regresores): pi estimado, test de razon de verosimilitudes de H0: pi = 0 con p-valor de
frontera (mezcla 0,5*chi2_0 + 0,5*chi2_1) e intervalo de confianza del 95 % por inversion de la
verosimilitud perfilada. Se contrasta con el ZINB de statsmodels y con pscl (R). Termina siempre
con codigo 0: no hay objetivo que cumplir (H29).
"""

import sys

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.inference.zero_inflation import report_from_design
from lastmile_exposure.inference.zinb_sandwich import zinb_design
from lastmile_exposure.models.zinb import INFLATE, fit_zinb
from lastmile_exposure.panel import count_frame
from lastmile_exposure.validation.paper_tables import load_pscl_oracle

BANNER = (
    "DIAGNOSTICO: el paper no reporta pi; no hay nada que reproducir. Resultado sobre nuestros "
    "datos, dentro del modelo del paper (pi constante)."
)


def _logistic(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def main() -> int:
    print(BANNER, "\n")
    rows, profiles = [], []
    for tag, static in (("dynamic", False), ("static", True)):
        df = count_frame(static=static)
        y, x = zinb_design(df)
        report = report_from_design(y, x)
        sm_fit = fit_zinb(df)  # el MLE de statsmodels, como contraste independiente
        pi_pscl = _logistic(float(load_pscl_oracle(tag)[INFLATE]))
        rows.append(
            {
                "tabla": tag, "nobs": report.nobs, "pi_hat": report.pi_hat,
                "en_frontera": report.on_boundary, "loglik_nb": report.loglik_nb,
                "loglik_zinb": report.loglik_zinb, "lr": report.lr,
                "pvalue_frontera": report.pvalue, "nivel": report.level,
                "ic_inferior": report.ci_lower, "ic_superior": report.ci_upper,
                "pi_statsmodels": sm_fit.pi, "loglik_statsmodels": sm_fit.llf,
                "pi_pscl": pi_pscl,
                "pscl_dentro_del_ic": bool(report.ci_lower <= pi_pscl <= report.ci_upper),
            }
        )  # fmt: skip
        profiles.append(report.profile.assign(tabla=tag))

    table = pd.DataFrame(rows)
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_dir / "zero_inflation.csv", index=False, float_format="%.10g")
    pd.concat(profiles)[["tabla", "pi", "loglik", "lr"]].to_csv(
        out_dir / "zero_inflation_profile.csv", index=False, float_format="%.10g"
    )

    for row in rows:
        print(f"[{row['tabla']}]  n = {row['nobs']}")
        note = (
            " (en la frontera: la verosimilitud es maxima en la NB)" if row["en_frontera"] else ""
        )
        print(f"  pi estimado = {row['pi_hat']:.3g}{note}")
        print(
            f"  loglik NB = {row['loglik_nb']:.3f} | "
            f"loglik ZINB (maximo) = {row['loglik_zinb']:.3f}"
        )
        print(f"  LR = {row['lr']:.3f} | p-valor de frontera = {row['pvalue_frontera']:.3g}")
        print(
            f"  IC {100 * row['nivel']:.0f} % de pi = [{row['ic_inferior']:.3g}, "
            f"{row['ic_superior']:.3g}]"
        )
        print(
            f"  statsmodels: pi = {row['pi_statsmodels']:.3g}, loglik = "
            f"{row['loglik_statsmodels']:.3f} | pscl: pi = {row['pi_pscl']:.3g} "
            f"(dentro del IC: {row['pscl_dentro_del_ic']})\n"
        )
    print("Lectura: con pi constante y los mismos regresores, los datos no sostienen ceros")
    print("estructurales; los ceros los explica la NB. No cubre la variante con covariables en la")
    print("inflacion que el paper dice haber probado (no se muestra ni se replica aqui).")
    print(f"-> {out_dir / 'zero_inflation.csv'}")
    print(f"-> {out_dir / 'zero_inflation_profile.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
