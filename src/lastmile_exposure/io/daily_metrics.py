"""Distancia y tiempo diarios por hexágono-hora (`DD-MM-YYYY_metrics.csv`).

Paper: §4.1.2 (`K_hi`: metros recorridos dentro del hexágono h durante la hora i, por día)
Código de los autores: 03_alternative_metrics.R (genera los archivos) y
    04_modeling_wednesday_alternative_metrics.R (los lee y toma la mediana)
Hallazgos (AGENTS.md §7): H1, H3, H4, H30
Estado: implementado (2026-10-10, paquete v2). Solo lectura y validación; la mediana está en
    `exposure/vehicles_distance.py`.

Cada archivo corresponde a un miércoles y SOLO contiene los hexágono-horas con al menos un par de
pings consecutivos válidos (mismo camión, mismo hexágono y misma hora; H4): los días sin tránsito
no aparecen, igual que en los conteos (H2). La columna `hour` es la hora UTC del timestamp (0-23)
y la fecha del nombre del archivo es la fecha UTC (H1); aquí no se convierte nada (variante
`as_published`). La conversión a hora local es de la Fase 5.

Son 41 archivos (no hay del 2024-05-01, feriado), no los 42 de los conteos (H3, D4).
"""

from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.io.daily_counts import WEDNESDAY, date_from_filename

DAILY_PATTERN = "*_metrics.csv"
VALUE_COLUMNS = ("total_distance_m", "total_time_sec")
COLUMNS = ["hex", "hour", "date", *VALUE_COLUMNS]


def default_metrics_dir() -> Path:
    """Carpeta `00_out/alternative_metrics` del replication package (un archivo por miércoles)."""
    return config.PACKAGE_DIR / "00_out" / "alternative_metrics"


def load_daily_metrics(
    metrics_dir: Path | None = None,
    *,
    hours: Iterable[int] | None = config.HOURS,
    exclude_dates: Iterable[str | pd.Timestamp] = (),
) -> pd.DataFrame:
    """Lee los archivos diarios y devuelve un marco largo `hex, hour, date, total_distance_m,
    total_time_sec`.

    - `hours`: horas (UTC) que se conservan; por defecto 7-22, las de la grilla. `None` conserva
      las 24 (necesario para la conversión a hora local, Fase 5).
    - `exclude_dates`: miércoles que se omiten (por defecto, ninguno: 41).

    Valida que todas las fechas sean miércoles, que estén las columnas esperadas, que no haya
    (hex, hour, date) repetidos y que distancia y tiempo sean números finitos no negativos.
    """
    folder = metrics_dir or default_metrics_dir()
    skip = {pd.Timestamp(d).normalize() for d in exclude_dates}
    keep_hours = None if hours is None else set(hours)

    frames = []
    for path in sorted(folder.glob(DAILY_PATTERN)):
        date = date_from_filename(path)
        if date in skip:
            continue
        if date.dayofweek != WEDNESDAY:
            raise ValueError(f"{path.name}: {date.date()} no es miércoles")
        df = pd.read_csv(path)
        missing = {"hex", "hour", *VALUE_COLUMNS} - set(df.columns)
        if missing:
            raise ValueError(f"{path.name}: faltan las columnas {sorted(missing)}")
        df = df[["hex", "hour", *VALUE_COLUMNS]]
        if keep_hours is not None:
            df = df[df["hour"].isin(keep_hours)]
        frames.append(df.assign(date=date))
    if not frames:
        raise FileNotFoundError(f"No hay archivos {DAILY_PATTERN} utilizables en {folder}")

    daily = pd.concat(frames, ignore_index=True)
    if daily.duplicated(["hex", "hour", "date"]).any():
        raise ValueError("Hay (hex, hour, date) repetidos en las métricas diarias")
    for column in VALUE_COLUMNS:
        values = daily[column]
        if not pd.api.types.is_numeric_dtype(values) or not np.isfinite(values).all():
            raise ValueError(f"`{column}` debe ser numérica y finita (sin faltantes)")
        if (values < 0).any():
            raise ValueError(f"`{column}` no puede ser negativa")
    return daily[COLUMNS]
