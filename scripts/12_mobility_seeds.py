"""Wasserstein de la Tabla 2 con el método del script de los autores, repetido con muchas semillas.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/12_mobility_seeds.py                     # 200 semillas (~25 min en 14 núcleos)
    python scripts/12_mobility_seeds.py --seeds 20 --workers 8
    python scripts/12_mobility_seeds.py --use-reference     # usa reference/mobility (rápido)
    python scripts/12_mobility_seeds.py --write-reference   # y guarda las semillas en reference/
    python scripts/12_mobility_seeds.py --resume            # retoma las semillas ya guardadas

Entrada: data/replication_package_v2/00_data/miercoles_rm.csv (datos confidenciales, no versionados)
Salida:  outputs/as_published/tables/mobility_seeds_raw_km.csv (W1 en km por semilla y grupo) y
         outputs/as_published/tables/table2_mobility_seeds.csv (publicado frente a la mediana y la
         banda del 95 % de las semillas, por grupo); mientras corre, cada semilla terminada se
         agrega a mobility_seeds_partial_km.csv (misma carpeta), que --resume retoma
Código:  src/lastmile_exposure/demographics/mobility.py (ver docs/paper_map.md)

Replica el script de los autores (04_descriptives/people_summary_table.R): muestra aleatoria de
5.000 de los 11.144 hexágonos, masa = media de las 3 horas de cada ventana (10-12 y 20-22) de
población × proporción del grupo, costo geodésico en km, W1 exacto, y valor = W / mediana de su
categoría. Su
muestra no tiene semilla, así que los valores publicados son UNA extracción y no se pueden
reproducir exactamente (AGENTS.md H24): el script informa qué tan compatibles son con la
distribución de las semillas y termina SIEMPRE con código 0; su código de salida no mide la
fidelidad (como `05_mobility.py`).
"""

import argparse
import sys
import time

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import (
    DEFAULT_SEEDS,
    group_masses,
    mobility_over_seeds,
    seed_agreement,
    summarize_seeds,
)
from lastmile_exposure.io.panel import load_panel
from lastmile_exposure.validation.paper_tables import (
    MOBILITY_SEEDS_FILE,
    load_mobility_seeds_reference,
    load_table2,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", type=int, default=len(DEFAULT_SEEDS), help="nº de semillas")
    parser.add_argument(
        "--workers", type=int, default=None, help="procesos (por defecto, núcleos-2)"
    )
    parser.add_argument("--use-reference", action="store_true", help="no recalcula (rápido)")
    parser.add_argument(
        "--resume", action="store_true", help="retoma las semillas del archivo parcial"
    )
    parser.add_argument(
        "--write-reference", action="store_true", help="guarda las semillas en reference/mobility"
    )
    args = parser.parse_args()

    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.use_reference:
        raw = load_mobility_seeds_reference()
    else:
        masses = group_masses(load_panel())
        started = time.time()

        def progress(done: int, total: int) -> None:
            if done in (1, total) or done % 10 == 0:
                print(f"  {done}/{total} semillas ({time.time() - started:.0f} s)", flush=True)

        raw = mobility_over_seeds(
            masses,
            range(args.seeds),
            workers=args.workers,
            progress=progress,
            checkpoint=out_dir / "mobility_seeds_partial_km.csv",
            resume=args.resume,
        )

    raw.to_csv(out_dir / "mobility_seeds_raw_km.csv", float_format="%.10g")

    published = load_table2().set_index("variable").loc[list(raw.columns)]
    summary = summarize_seeds(
        raw, published["wasserstein"].astype(float), published["mobility_rank"].astype(int)
    )
    summary.index.name = "group"
    summary.round(5).to_csv(out_dir / "table2_mobility_seeds.csv")
    pd.set_option("display.width", 200)
    print(summary.round(4).to_string())

    agreement = seed_agreement(
        raw, published["wasserstein"].astype(float), published["mobility_rank"].astype(int)
    )
    print(
        f"\n{agreement['n_seeds']} semillas: {agreement['n_inside_band']}/{agreement['n_groups']} "
        f"valores publicados dentro de la banda del 95 %; |z| > 2 en {agreement['n_abs_z_gt_2']}."
    )
    print(
        f"Los 15 rankings iguales al publicado en el {agreement['p_all_ranks']:.1%} de las "
        f"semillas; por dimension: "
        + ", ".join(f"{d} {p:.0%}" for d, p in agreement["p_ranks_by_dimension"].items())
    )
    for dim, e in agreement["p_extremes"].items():
        print(
            f"  {dim}: mas movil publicado {e['top']} ({e['p_top']:.0%} de las semillas), "
            f"menos movil {e['bottom']} ({e['p_bottom']:.0%})"
        )
    print(
        f"Error maximo |normalizado - publicado| por semilla: min {agreement['error_min']:.3f}, "
        f"mediana {agreement['error_median']:.3f}, max {agreement['error_max']:.3f}"
    )
    print("Los valores publicados son una extraccion de un muestreo sin semilla (H24).")

    if args.write_reference and not args.use_reference:
        path = config.MOBILITY_DIR / MOBILITY_SEEDS_FILE
        raw.to_csv(path, float_format="%.10g")
        print(f"-> {path}")
    print(f"-> {out_dir / 'table2_mobility_seeds.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
