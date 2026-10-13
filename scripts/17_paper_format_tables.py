"""Tablas 4 y 5 en el formato del paper, réplica y cifras impresas lado a lado.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/17_paper_format_tables.py      # segundos: no ajusta ningún modelo

Entrada: lo que dejan los scripts 03 y 06 en outputs/as_published/tables/
    table{4,5}_complete_no_stars.csv  (valores, script 03)
    inference_{dynamic,static}_<variante>.csv  (estrellas, script 06)
    y las cifras impresas de reference/paper_tables/
Salida:  outputs/as_published/tables/table{4,5}_vs_paper_<variante>.csv y .md
Código:  src/lastmile_exposure/reporting/paper_format.py (docs/paper_map.md)

Escribe tres tablas: la Tabla 4 con las estrellas `paper_text` (cluster por comuna) y la Tabla 5
con `paper_text` y con `authors_script` (D3, H26). Cada celda es `valor + estrellas`, con la
réplica junto a la impresa; el .md marca con `‡` los valores y con `†` las estrellas que difieren.
Solo presenta lo ya calculado: termina con 0, o con 2 si faltan las entradas (corre antes los
scripts 03 y 06).
"""

import sys

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.reporting.paper_format import agreement, side_by_side, to_markdown
from lastmile_exposure.validation.paper_tables import load_table4, load_table5

# (tabla, etiqueta de los archivos, titulo, referencia impresa, variantes de estrellas)
TABLES = (
    (
        "table4",
        "dynamic",
        "Tabla 4 (dinámico): réplica frente al paper",
        load_table4,
        ("paper_text",),
    ),
    (
        "table5",
        "static",
        "Tabla 5 (estático): réplica frente al paper",
        load_table5,
        ("paper_text", "authors_script"),
    ),
)


def main() -> int:
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    needed = [out_dir / f"{name}_complete_no_stars.csv" for name, *_ in TABLES]
    needed += [
        out_dir / f"inference_{tag}_{variant}.csv"
        for _, tag, _, _, variants in TABLES
        for variant in variants
    ]
    missing = [path.name for path in needed if not path.exists()]
    if missing:
        print("Faltan entradas; corre antes scripts/03_zinb_tables.py y scripts/06_inference.py:")
        print("  " + ", ".join(missing))
        return 2

    for name, tag, title, load_reference, variants in TABLES:
        values = pd.read_csv(out_dir / f"{name}_complete_no_stars.csv")
        reference = load_reference()
        for variant in variants:
            inference = pd.read_csv(out_dir / f"inference_{tag}_{variant}.csv")
            table = side_by_side(values, inference, reference)
            stem = f"{name}_vs_paper_{variant}"
            table.to_csv(out_dir / f"{stem}.csv", index=False)
            (out_dir / f"{stem}.md").write_text(
                to_markdown(table, title, variant), encoding="utf-8"
            )
            total = agreement(table).sum(numeric_only=True)
            print(
                f"{stem}: valores iguales {total['values_ok']}/{total['values']}, "
                f"estrellas iguales a las impresas {total['stars_ok']}/{total['stars']}"
            )
    print(f"\n-> {out_dir}")
    print("Las estrellas impresas no salen del metodo correcto (AGENTS.md H31, H32).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
