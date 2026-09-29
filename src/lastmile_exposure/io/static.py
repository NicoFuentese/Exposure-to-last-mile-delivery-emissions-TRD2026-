"""Demografía estática por hexágono (`datosxhexagono.csv`).

Paper: §5.2 (enfoque estático)
Código de los autores: summary_results_static*.R (`static_data`)
Hallazgos (AGENTS.md §7): H8, §8.1
Estado: implementado (Fase 3). Solo lectura; la conversión de unidades está en
`demographics/static.py`.

El archivo tiene una fila por hexágono (11.144). `gse_*` viene en PORCENTAJE (0-100); el
resto en proporción. El README de los autores no explica cómo se construyó.
"""

from pathlib import Path

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.io.panel import default_data_dir

STATIC_FILE = "datosxhexagono.csv"


def load_static_raw(data_dir: Path | None = None) -> pd.DataFrame:
    """Lee la demografía estática tal como viene (GSE en %, sin combinar D y E)."""
    df = pd.read_csv((data_dir or default_data_dir()) / STATIC_FILE, encoding="utf-8")
    if len(df) != config.N_HEXAGONS or df["hex"].nunique() != config.N_HEXAGONS:
        raise ValueError("`datosxhexagono.csv` debe tener una fila por cada uno de los 11.144 hex")
    return df
