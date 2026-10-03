"""Conteos diarios de vehículos por hexágono-hora (`hexagon_count_DD-MM-YYYY_cleaned.csv`).

Paper: §4.1.1 (`Y_hi`: nº de vehículos distintos con ≥1 ping en el hexágono h durante la hora i)
Código de los autores: 03_gps_hexagon_count.R (genera los archivos) y 04_modeling_wedenesday.R
    (los lee y los une)
Hallazgos (AGENTS.md §7): H1, H2, H3, H14
Estado: implementado (Fase 3). Solo lectura y validación; la mediana está en
    `exposure/aggregate.py`.

Cada archivo corresponde a un miércoles y SOLO contiene los hexágono-horas con ≥1 vehículo (los
días sin vehículos no aparecen: H2). La columna `hour` es la hora UTC del timestamp (0-23) y la
fecha del nombre del archivo es la fecha UTC (H1); aquí no se convierte nada (variante
`as_published`). La conversión a hora local es de la Fase 5.
"""

import re
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from lastmile_exposure import config

DAILY_PATTERN = "hexagon_count_*_cleaned.csv"
_DATE_IN_NAME = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
WEDNESDAY = 2  # `Timestamp.dayofweek`: lunes = 0


def default_daily_dir() -> Path:
    """Carpeta `00_out/hexagon_count` del replication package (un archivo por miércoles)."""
    return config.PACKAGE_DIR / "00_out" / "hexagon_count"


def date_from_filename(path: Path) -> pd.Timestamp:
    """Fecha (UTC) del miércoles a partir del nombre `hexagon_count_DD-MM-YYYY_cleaned.csv`."""
    m = _DATE_IN_NAME.search(path.name)
    if m is None:
        raise ValueError(f"No encuentro una fecha DD-MM-YYYY en el nombre {path.name!r}")
    day, month, year = (int(g) for g in m.groups())
    return pd.Timestamp(year=year, month=month, day=day)


def load_daily_counts(
    daily_dir: Path | None = None,
    *,
    hours: Iterable[int] | None = config.HOURS,
    exclude_dates: Iterable[str | pd.Timestamp] = (),
) -> pd.DataFrame:
    """Lee los archivos diarios y devuelve un marco largo `hex, hour, date, vehicles`.

    - `hours`: horas (UTC) que se conservan; por defecto 7-22, las de la grilla. `None` conserva
      las 24.
    - `exclude_dates`: miércoles que se omiten, p. ej. `("2024-05-01",)` (feriado, D4) para
      quedarse con 41 miércoles como el paper. Por defecto no se excluye ninguno (42).

    Valida que todas las fechas sean miércoles, que no haya (hex, hour, date) repetidos y que
    `vehicles` sea un entero ≥ 0.
    """
    folder = daily_dir or default_daily_dir()
    skip = {pd.Timestamp(d).normalize() for d in exclude_dates}
    keep_hours = None if hours is None else set(hours)

    frames = []
    for path in sorted(folder.glob(DAILY_PATTERN)):
        date = date_from_filename(path)
        if date in skip:
            continue
        if date.dayofweek != WEDNESDAY:
            raise ValueError(f"{path.name}: {date.date()} no es miércoles")
        df = pd.read_csv(path, usecols=["hex", "hour", "vehicles"])
        if keep_hours is not None:
            df = df[df["hour"].isin(keep_hours)]
        frames.append(df.assign(date=date))
    if not frames:
        raise FileNotFoundError(f"No hay archivos {DAILY_PATTERN} utilizables en {folder}")

    daily = pd.concat(frames, ignore_index=True)
    if daily.duplicated(["hex", "hour", "date"]).any():
        raise ValueError("Hay (hex, hour, date) repetidos en los conteos diarios")
    if (daily["vehicles"] < 0).any() or (daily["vehicles"] % 1 != 0).any():
        raise ValueError("`vehicles` debe ser un entero no negativo")
    return daily[["hex", "hour", "date", "vehicles"]]
