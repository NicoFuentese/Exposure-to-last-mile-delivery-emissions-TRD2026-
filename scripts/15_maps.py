"""Mapas hexagonales del paper (Fase 7): Fig. 1 y un sustituto rotulado de la Fig. 2.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/15_maps.py               # ~20 s; escribe solo en outputs/
    python scripts/15_maps.py --publish     # y copia los PNG (150 dpi) a docs/figures/

Entrada: data/replication_package_v2/00_data/ (datos confidenciales, no versionados):
         miercoles_rm.csv (Fig. 1) y hexagon_model_median_wednesdays_RM.csv (sustituto de la Fig. 2)
Salida:  outputs/as_published/figures/fig1_seg_population.png (200 dpi) y .pdf (vectorial)
         outputs/as_published/tables/fig1_scales.csv (máximos de la escala de la Fig. 1 frente
         a los del paper: agregados, sin valores por hexágono; lo lee el informe de 16_run_all.py)
         outputs/as_published/figures/fig2_proxy_vehicles.png (200 dpi) y .pdf (vectorial)
         Con --publish, además docs/figures/fig1_seg_population.png y fig2_proxy_vehicles.png
         (150 dpi, solo PNG)
Código:  src/lastmile_exposure/figures/maps.py (ver docs/paper_map.md)

Estos mapas muestran valores POR HEXÁGONO derivados de los datos confidenciales. Por defecto se
escriben solo en outputs/ (ignorado por git). Con --publish se copia a docs/figures/ una versión
reducida, por decisión del usuario (2026-10-10): el paper publica la misma figura. Solo el PNG a
150 dpi: el PDF vectorial guarda el color exacto de cada hexágono y no se versiona
(tests/test_published_figures.py lo vigila).

La Fig. 2 del paper (puntos GPS por hexágono) NO se puede reproducir sin el GPS crudo de todos los
días. `fig2_proxy_vehicles` es un SUSTITUTO, rotulado así en su título: la mediana de vehículos
por hexágono (media de las horas 7-22) con el estilo de la Fig. 2 (`inferno`, `log1p`). No se
versiona (como PNG de 150 dpi, igual que la Fig. 1) por decisión del usuario (2026-10-11).

Réplica del dibujo, no de los píxeles: escala lineal de 0 al máximo de las dos ventanas de cada
grupo, paleta `turbo`, límites y barra de escala del script de los autores. Termina siempre con
código 0: no hay una cifra del paper que validar más allá de la forma y la escala (AGENTS.md H35).
"""

import argparse
import sys

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import group_masses
from lastmile_exposure.figures.maps import (
    FIG1_NAME,
    FIG2_PROXY_NAME,
    PUBLISH_DPI,
    fig1_data,
    plot_fig1,
    plot_vehicle_proxy,
    vehicle_means,
)
from lastmile_exposure.figures.marginal_effects import save_figure
from lastmile_exposure.io.panel import load_counts_dataset, load_panel

PAPER_SCALE_END = {"AB": 1600.0, "C1b": 7000.0}  # lo que imprime la Fig. 1 del paper (p.6)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--publish", action="store_true", help="copia los PNG (150 dpi) a docs/figures"
    )
    args = parser.parse_args()
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "figures"
    masses = group_masses(load_panel())
    data = fig1_data(masses)
    print(f"Hexagonos dentro de los limites del mapa: {len(data['hexes'])} de {len(masses.hexes)}")
    for label, vmax in data["vmax"].items():
        print(f"  {label}: escala 0 - {vmax:,.0f} (el paper imprime 1600 para AB y 7000 para C1b)")
    tables_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "group": list(data["vmax"]),
            "ours_max": [float(v) for v in data["vmax"].values()],
            "paper_max": [PAPER_SCALE_END[g] for g in data["vmax"]],
        }
    ).assign(ratio=lambda d: d["ours_max"] / d["paper_max"]).to_csv(
        tables_dir / "fig1_scales.csv", index=False
    )
    fig = plot_fig1(masses)
    paths = save_figure(fig, out_dir / FIG1_NAME, dpi=200)
    print(f"{FIG1_NAME}: {', '.join(p.name for p in paths)}")
    print(f"-> {out_dir}  (outputs/: valores por hexagono, no se versionan)")
    if args.publish:
        (published,) = save_figure(
            fig, config.FIGURES_DIR / FIG1_NAME, dpi=PUBLISH_DPI, suffixes=(".png",)
        )
        print(f"-> {published}  (se versiona: solo PNG a {PUBLISH_DPI} dpi, como el paper)")
    # Sustituto de la Fig. 2 (vehiculos por hexagono; NO es la Fig. 2)
    proxy = plot_vehicle_proxy(vehicle_means(load_counts_dataset()))
    proxy_paths = save_figure(proxy, out_dir / FIG2_PROXY_NAME, dpi=200)
    print(f"{FIG2_PROXY_NAME} (SUSTITUTO de la Fig. 2): {', '.join(p.name for p in proxy_paths)}")
    if args.publish:
        (published,) = save_figure(
            proxy, config.FIGURES_DIR / FIG2_PROXY_NAME, dpi=PUBLISH_DPI, suffixes=(".png",)
        )
        print(f"-> {published}  (se versiona: solo PNG a {PUBLISH_DPI} dpi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
