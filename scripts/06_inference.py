"""Errores estándar por comuna y estrellas de las Tablas 4 y 5, comparadas con el paper.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/06_inference.py          # ajusta el ZINB (~1,5 min por tabla) y todo lo demás

Entrada: data/replication_package/00_data/ (datos confidenciales, no versionados)
Salida:  outputs/as_published/tables/inference_<tabla>_<variante>.csv (SE, p y estrellas por celda)
         outputs/as_published/tables/stars_<tabla>_<variante>.csv (comparación celda a celda)
Código:  src/lastmile_exposure/inference/ y reporting/significance.py (docs/paper_map.md)

Calcula las estrellas con tres variantes de error estándar, todas sobre `00_data`:
- `paper_text`: cluster por comuna en todo, lo que dice el paper (§4.2.3).
- `authors_script`: lo que hace el script de los autores. Igual que la anterior, salvo el ZINB
  ESTÁTICO, donde su script deja el cluster en NULL por un error y no agrupa (cada fila es su
  propio cluster, AGENTS.md H26). Reproduce ese error a propósito; no es lo que dice el paper.
- `iid`: sin cluster (como `summary_results.R`); solo de referencia.
Cuenta cuántas de las 44 estrellas por tabla coinciden con el paper. Termina siempre con código 0:
no todas las estrellas publicadas se reproducen (H25, H26, D3), así que su código de salida no
mide la fidelidad.
"""

import sys

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.models.zinb import fit_zinb
from lastmile_exposure.panel import count_frame, distance_frame
from lastmile_exposure.reporting.significance import (
    authors_script_inference_table,
    inference_table,
)
from lastmile_exposure.validation.paper_tables import (
    compare_stars,
    load_table4,
    load_table5,
    stars_summary,
)

TABLES = (("dynamic", False, load_table4), ("static", True, load_table5))
VARIANTS = ("paper_text", "authors_script", "iid")
NOTES = {
    "paper_text": "cluster por comuna en todo (lo que dice el paper)",
    "authors_script": "como el script: ZINB estatico sin agrupar (error de los autores, H26)",
    "iid": "sin cluster (referencia)",
}


def build(variant, distance, counts, zinb, static):
    if variant == "paper_text":
        return inference_table(distance, counts, zinb, cluster="comuna")
    if variant == "authors_script":
        return authors_script_inference_table(distance, counts, zinb, static=static)
    return inference_table(distance, counts, zinb, cluster=None)


def main() -> int:
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for tag, static, load_reference in TABLES:
        counts, distance = count_frame(static=static), distance_frame(static=static)
        zinb = fit_zinb(counts)
        print(f"{tag}: ZINB ajustado (pi = {zinb.pi:.2e}, theta = {zinb.theta:.4f})", flush=True)
        reference = load_reference()
        for variant in VARIANTS:
            table = build(variant, distance, counts, zinb, static)
            table["variante"] = variant
            table.round(6).to_csv(out_dir / f"inference_{tag}_{variant}.csv", index=False)
            report = compare_stars(table, reference)
            report.to_csv(out_dir / f"stars_{tag}_{variant}.csv", index=False)
            summary[(tag, variant)] = stars_summary(report)["matches"]
            total = int(report["ok"].sum())
            print(f"  {variant:15s} estrellas iguales: {total}/{len(report)}  ({NOTES[variant]})")
    result = pd.DataFrame(summary).T
    result.index.names = ["tabla", "variante"]
    print("\nEstrellas iguales al paper, por columna (de 11 por columna):")
    print(result.to_string())
    print(f"\n-> {out_dir}")
    print("NO todas las estrellas publicadas se reproducen (AGENTS.md H25, H26 y D3).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
