"""Panel de población flotante y bases de modelación hexágono-hora.

Paper: §3.1, Tabla 2
Código de los autores: 04_modeling_wedenesday.R (lectura de `miercoles_rm.csv`); 00_data/README.md
Hallazgos (AGENTS.md §7): H6, H13, H15
Estado: implementado (Fase 3). Lee y valida la grilla; reproduce la Tabla 2.

Se leen SOLO los archivos de `data/replication_package/00_data/`: las copias de
`00_out/data_base/` no son las del paper (H6).
"""

from pathlib import Path

import pandas as pd

from lastmile_exposure import config

PANEL_FILE = "miercoles_rm.csv"
COUNTS_FILE = "hexagon_model_median_wednesdays_RM.csv"
DISTANCE_FILE = "hexagon_model_median_wednesday_alternative_metrics_RM.csv"


def default_data_dir() -> Path:
    """Carpeta `00_data` del replication package."""
    return config.PACKAGE_DIR / "00_data"


def validate_grid(df: pd.DataFrame) -> pd.DataFrame:
    """Comprueba que `df` es la grilla completa hexágono-hora del paper.

    Exige 178.304 filas (11.144 hexágonos × 16 horas), sin pares (hex, hour) repetidos.
    Devuelve `df` para poder encadenarla.
    """
    if len(df) != config.N_HEXAGON_HOURS:
        raise ValueError(f"Se esperaban {config.N_HEXAGON_HOURS} filas, hay {len(df)}")
    if df["hex"].nunique() != config.N_HEXAGONS:
        raise ValueError(f"Se esperaban {config.N_HEXAGONS} hexágonos, hay {df['hex'].nunique()}")
    if set(df["hour"].unique()) != set(config.HOURS):
        raise ValueError("Las horas no son 7..22")
    if df.duplicated(["hex", "hour"]).any():
        raise ValueError("Hay pares (hex, hour) repetidos")
    return df


def _read_csv(name: str, data_dir: Path | None) -> pd.DataFrame:
    return pd.read_csv((data_dir or default_data_dir()) / name, encoding="utf-8")


def load_panel(data_dir: Path | None = None) -> pd.DataFrame:
    """Panel de población flotante y demografía por hexágono-hora (`miercoles_rm.csv`).

    Columnas: `hex`, `hour` (renombradas de `h3_9`, `hora`), `poblacion_flotante`, los shares
    `genero_*`, `edad_*`, `gse_*` (en [0, 1]) y la `comuna`. 1.427 filas tienen población 0 y
    todos los shares en 0 (H13): se conservan, como en el código de los autores.
    """
    df = _read_csv(PANEL_FILE, data_dir).rename(columns={"h3_9": "hex", "hora": "hour"})
    return validate_grid(df)


def load_counts_dataset(data_dir: Path | None = None) -> pd.DataFrame:
    """Base del paper para conteos: panel + `median_vehicles` + `count_wednesdays`."""
    return validate_grid(_read_csv(COUNTS_FILE, data_dir))


def load_distance_dataset(data_dir: Path | None = None) -> pd.DataFrame:
    """Base del paper para distancia: panel + `median_distance` y `median_time`."""
    return validate_grid(_read_csv(DISTANCE_FILE, data_dir))
