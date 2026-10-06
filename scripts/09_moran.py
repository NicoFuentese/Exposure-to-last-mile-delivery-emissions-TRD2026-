"""I de Moran de la distancia y los vehiculos, comparada con el paper (0,4694 y 0,4756).

Uso (con el entorno activo, desde la raiz del repositorio):
    python scripts/09_moran.py               # rapido: unos segundos

Entrada: data/replication_package/00_data/ (datos confidenciales, no versionados)
Salida:  outputs/as_published/tables/moran.csv
Codigo:  src/lastmile_exposure/inference/moran.py (docs/paper_map.md)

El paper no especifica la matriz de pesos ni como promedia el tiempo (AGENTS.md H28, D8). Se
calcula la lista CERRADA de lecturas directas: hexagonos adyacentes (anillo 1 de H3) con pesos W
(filas estandarizadas) o B (binaria), por 3 agregaciones en el tiempo. La principal es la lectura
literal (promedio de las 16 I horarias, pesos W); el resto son sensibilidades, no la metodologia
del paper. Etiquetas: exacto (|dif| <= 0,0005), aproximado (<= 2 % relativo; NO identifica la
especificacion) o no reproduce. Termina siempre con codigo 0: el metodo no esta identificado.
"""

import sys

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.inference.moran import (
    h3_ring1_weights,
    morans_i_grid,
    n_islands,
    wide_by_hour,
)
from lastmile_exposure.io.panel import load_counts_dataset, load_distance_dataset
from lastmile_exposure.validation.paper_tables import load_paper_scalars, moran_agreement

VARIABLES = {  # nombre en el paper -> (columna, cifra del paper)
    "distancia": ("median_distance", "moran_i_distance"),
    "vehiculos": ("median_vehicles", "moran_i_vehicles"),
}


def main() -> int:
    scalars = load_paper_scalars()
    distance, counts = load_distance_dataset(), load_counts_dataset()
    hexes = np.array(sorted(distance["hex"].unique()))
    sources = {"distancia": distance, "vehiculos": counts}
    wides = {
        name: wide_by_hour(sources[name], column, hexes) for name, (column, _) in VARIABLES.items()
    }
    w = h3_ring1_weights(hexes, style="B")
    print(f"hexagonos: {len(hexes)} | horas: {wides['distancia'].shape[1]} | "
          f"islas (sin vecinos en la grilla): {n_islands(w)}")  # fmt: skip

    grid = morans_i_grid(wides, hexes)
    rows = []
    for _, r in grid.iterrows():
        for name, (_, key) in VARIABLES.items():
            paper = float(scalars[key])
            rows.append(
                {
                    "estilo": r["estilo"],
                    "agregacion": r["agregacion"],
                    "rol": "principal" if r["principal"] else "sensibilidad",
                    "variable": name,
                    "moran_i": r[name],
                    "paper": paper,
                    "abs_diff": abs(r[name] - paper),
                    "etiqueta": moran_agreement(r[name], paper),
                }
            )
    table = pd.DataFrame(rows)
    out_dir = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    table.round(6).to_csv(out_dir / "moran.csv", index=False)

    show = table.pivot_table(
        index=["rol", "estilo", "agregacion"], columns="variable", values=["moran_i", "etiqueta"],
        aggfunc="first",
    )  # fmt: skip
    print("\nI de Moran (paper: distancia 0,4694 | vehiculos 0,4756):")
    print(show.to_string())
    print(f"\n-> {out_dir / 'moran.csv'}")
    print("La especificacion del paper NO esta identificada (AGENTS.md H28, D8):")
    print("'aproximado' no la identifica (dos elecciones libres: matriz y agregacion).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
