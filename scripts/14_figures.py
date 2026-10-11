"""Figuras del paper (Fase 7): Figs. 6, 8, 9 y 10 (efectos marginales) y Fig. 7 (gramos).

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/14_figures.py            # segundos; usa las tablas que deja 03_zinb_tables.py
    python scripts/14_figures.py --publish  # y copia las figuras de coeficientes a docs/figures/

Entrada: outputs/as_published/tables/table4_complete_no_stars.csv y table5_complete_no_stars.csv
         (las crea scripts/03_zinb_tables.py; contienen las cuatro columnas de las Tablas 4 y 5)
Salida:  outputs/as_published/figures/<figura>.png y .pdf, y <figura>_data.csv con los puntos
         dibujados (outputs/ está ignorado por git). Con --publish, también PNG y PDF en
         docs/figures/ (config.FIGURES_DIR), la única carpeta de figuras que se versiona.
Código:  src/lastmile_exposure/figures/marginal_effects.py (ver docs/paper_map.md)

Réplica del dibujo, no de los píxeles: ZINB en azul (eje izquierdo) y OLS `K̃>0` en rojo (eje
derecho, reescalado como en el código de los autores para que los rangos de las dos series
coincidan, AGENTS.md H34). Fig. 7: barras de NOx y PM = factor × efecto OLS `K̃>0`, con el factor
DERIVADO de las barras impresas del paper (los factores de emisión de la fuente no se conocen,
H36). Termina con código 1 si faltan las tablas.

Solo se publican (`--publish`) figuras que contienen COEFICIENTES (Figs. 6, 8, 9 y 10: los
mismos números de las Tablas 4 y 5 del paper). Cualquier figura con valores por hexágono (mapas)
se queda en outputs/, porque se deriva de los datos confidenciales; lo vigila
tests/test_published_figures.py.
"""

import argparse
import sys

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.figures.emissions import FIG7_NAME, plot_emissions
from lastmile_exposure.figures.marginal_effects import (
    FIGURES,
    figure_data,
    plot_effects,
    save_figure,
)
from lastmile_exposure.reporting.emissions import emission_factors, emission_grams
from lastmile_exposure.validation.paper_tables import load_fig7_bars, load_table4

TABLE_FILES = {"dynamic": "table4_complete_no_stars.csv", "static": "table5_complete_no_stars.csv"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--publish", action="store_true", help="copia las figuras de coeficientes a docs/figures"
    )
    args = parser.parse_args()
    variant = config.Variant.AS_PUBLISHED.value
    tables_dir = config.OUTPUTS_DIR / variant / "tables"
    out_dir = config.OUTPUTS_DIR / variant / "figures"
    tables = {}
    for tag, name in TABLE_FILES.items():
        path = tables_dir / name
        if not path.exists():
            print(f"Falta {path}: ejecuta antes scripts/03_zinb_tables.py")
            return 1
        tables[tag] = pd.read_csv(path)

    for name, (tag, group) in FIGURES.items():
        fig = plot_effects(tables[tag], group)
        paths = save_figure(fig, out_dir / name)
        if args.publish:
            save_figure(fig, config.FIGURES_DIR / name)
        figure_data(tables[tag], group).round(4).to_csv(out_dir / f"{name}_data.csv", index=False)
        print(f"{name}: {', '.join(p.name for p in paths)}")
    # Fig. 7: el factor se deriva de las barras impresas y de la Tabla 4 impresa, y se aplica al
    # efecto OLS K>0 reproducido
    printed = figure_data(load_table4(), "seg").set_index("label")["ols_kpos"]
    bars = load_fig7_bars()
    factors = emission_factors(printed, bars)
    ours = figure_data(tables["dynamic"], "seg").set_index("label")["ols_kpos"]
    grams = emission_grams(ours, factors)
    fig = plot_emissions(grams)
    paths = save_figure(fig, out_dir / FIG7_NAME)
    if args.publish:
        save_figure(fig, config.FIGURES_DIR / FIG7_NAME)
    grams.round(4).to_csv(out_dir / f"{FIG7_NAME}_data.csv", index=False)
    same = (
        grams[["nox_g", "pm_g"]].round(1).to_numpy() == bars[["nox_g", "pm_g"]].to_numpy()
    ).sum()
    print(f"{FIG7_NAME}: {', '.join(p.name for p in paths)}")
    print(
        f"  factor NOx {factors['nox'].value:.5f} g/m (intervalo {factors['nox'].low:.5f}-"
        f"{factors['nox'].high:.5f}), PM {factors['pm'].value:.5f} g/m "
        f"({factors['pm'].low:.5f}-{factors['pm'].high:.5f}); "
        f"etiquetas iguales a las impresas: {same}/12"
    )
    print(f"-> {out_dir}")
    if args.publish:
        print(f"-> {config.FIGURES_DIR}  (se versiona: solo coeficientes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
