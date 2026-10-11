"""Conversión UTC → America/Santiago y selección de miércoles locales.

Paper: §3.2 (los timestamps del GPS vienen en UTC)
Código de los autores: (el código de los autores NO convierte: usa hora y fecha UTC, H1)
Hallazgos (AGENTS.md §7): H1, H18, H19, H20, D1
Estado: implementado (Fase 5). Convierte los marcos diarios de `io/daily_counts.py` y
    `io/daily_metrics.py` (`hex, hour, date, …`) a hora y fecha locales y deja solo las filas de
    miércoles locales en las horas pedidas. Es la variante `local_time` (sensibilidad), no la
    réplica.

Cada archivo diario del paquete es un día UTC (con `hour` UTC 0-23) y solo existen los de los
miércoles UTC. Con las horas locales 7-19 todo sale del mismo miércoles (UTC−3: horas UTC 10-22;
UTC−4: 11-23), así que esas horas están completas; la hora 20 está solo en los días UTC−3 y las
horas 21-22 pertenecen al archivo del jueves UTC, que no existe (H19). Las horas UTC 0-2/3 de un
archivo son martes local y se descartan.

La conversión usa la base de zonas horarias (`tzdata`) para cada instante, sin suponer un
desfase fijo; `day_offsets` comprueba que dentro de cada archivo diario sea constante (H18), lo
que vale para los miércoles porque los cambios de horario de 2024 fueron en fin de semana.
"""

from collections.abc import Iterable

import pandas as pd

from lastmile_exposure import config

WEDNESDAY = 2  # `Timestamp.dayofweek`: lunes = 0
LOCAL_COLUMNS = ["local_date", "local_hour", "utc_offset"]


def _local_clock(date: pd.Series, hour: pd.Series) -> pd.DataFrame:
    """Fecha local, hora local y desfase (horas, local − UTC) de cada instante `date` + `hour`."""
    utc = date + pd.to_timedelta(hour, unit="h")
    wall = utc.dt.tz_localize("UTC").dt.tz_convert(config.TIMEZONE).dt.tz_localize(None)
    return pd.DataFrame(
        {
            "local_date": wall.dt.normalize(),
            "local_hour": wall.dt.hour,
            "utc_offset": (wall - utc).dt.total_seconds() / 3600,
        },
        index=date.index,
    )


def to_local(daily: pd.DataFrame) -> pd.DataFrame:
    """Agrega `local_date`, `local_hour` y `utc_offset` a un marco diario (`date`, `hour` UTC).

    Solo convierte las combinaciones distintas de (`date`, `hour`) y las une al marco, en su mismo
    orden. No filtra ni modifica `date` y `hour`.
    """
    keys = daily[["date", "hour"]].drop_duplicates().reset_index(drop=True)
    keys = pd.concat([keys, _local_clock(keys["date"], keys["hour"])], axis=1)
    return daily.merge(keys, on=["date", "hour"], how="left")


def local_wednesdays(
    daily: pd.DataFrame, hours: Iterable[int] = config.LOCAL_COMPLETE_HOURS
) -> pd.DataFrame:
    """Filas de miércoles locales en las horas locales `hours`, con `date` y `hour` en hora local.

    Devuelve el mismo esquema que `daily` (`hex, hour, date, …`), de modo que
    `exposure.vehicles_counts.median_vehicles` y `exposure.vehicles_distance.median_distance` se
    usan sin cambios. Por defecto conserva las horas locales 7-19, las únicas completas (H19).
    Falla si la conversión dejara dos filas con el mismo (hex, hour, date).
    """
    local = to_local(daily)
    keep = (local["local_date"].dt.dayofweek == WEDNESDAY) & local["local_hour"].isin(list(hours))
    out = local.loc[keep].drop(columns=["date", "hour", "utc_offset"])
    out = out.rename(columns={"local_date": "date", "local_hour": "hour"})
    columns = [c for c in daily.columns if c in out.columns]
    out = out[columns].reset_index(drop=True)
    if out.duplicated(["hex", "hour", "date"]).any():
        raise ValueError("La conversión a hora local dejó (hex, hour, date) repetidos")
    return out


def day_offsets(dates: Iterable[str | pd.Timestamp]) -> pd.Series:
    """Desfase (horas, local − UTC) de cada día UTC, que debe ser el mismo en sus 24 horas.

    Devuelve −3 (verano) o −4 (invierno) para los miércoles de 2024. Falla si en algún día el
    desfase cambia a mitad del día (cambio de horario), porque entonces un archivo diario mezclaría
    dos desfases.
    """
    days = pd.Series(sorted({pd.Timestamp(d).normalize() for d in dates}), name="date")
    grid = days.to_frame().merge(pd.DataFrame({"hour": range(24)}), how="cross")
    grid = pd.concat([grid, _local_clock(grid["date"], grid["hour"])], axis=1)
    per_day = grid.groupby("date")["utc_offset"].agg(["min", "max"])
    changing = per_day[per_day["min"] != per_day["max"]]
    if len(changing):
        raise ValueError(f"El desfase UTC cambia dentro del día en: {list(changing.index.date)}")
    return per_day["min"].rename("utc_offset")


def coverage_by_hour(daily: pd.DataFrame) -> pd.Series:
    """Nº de miércoles distintos que aportan a cada hora de un marco ya convertido.

    `daily` es el resultado de `local_wednesdays` (con `date` y `hour` en hora local). Con las
    horas locales 7-19 debe dar el total de archivos; la hora 20 solo los días UTC−3 y las horas
    21-22 ninguno (H19).
    """
    return daily.groupby("hour")["date"].nunique().rename("days")
