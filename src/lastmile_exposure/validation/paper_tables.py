"""Carga de las cifras publicadas y comparación celda a celda contra la réplica.

Paper: Tablas 2 a 5
Código de los autores: (no aplica)
Hallazgos (AGENTS.md §7): §7.2 (estado de la validación)
Estado: implementado (Fase 3). Compara valores; la comparación de estrellas se añade con la
    inferencia (Fase 4).

Las cifras viven en `reference/paper_tables/*.csv` (ver su README).
"""

import pandas as pd

from lastmile_exposure import config

# Tolerancia absoluta según la precisión con que el paper imprime cada cifra.
TABLE2_TOLERANCES = {"mean": 0.006, "std": 0.006, "mean_pct": 0.051, "std_pct": 0.051}
MARGINAL_TOLERANCE = 6e-5  # el paper imprime 4 decimales


def load_reference(name: str, *, text_stars: bool = False) -> pd.DataFrame:
    """Lee `reference/paper_tables/<name>.csv`.

    `text_stars=True` conserva las estrellas vacías como "" (Tablas 4-5); si no, las celdas
    vacías quedan NaN y las columnas numéricas (Tablas 2-3).
    """
    return pd.read_csv(config.REFERENCE_DIR / f"{name}.csv", keep_default_na=not text_stars)


def load_table2() -> pd.DataFrame:
    return load_reference("table2_floating_population")


def load_table4() -> pd.DataFrame:
    return load_reference("table4_dynamic", text_stars=True)


def load_table5() -> pd.DataFrame:
    return load_reference("table5_static", text_stars=True)


def compare_columns(
    computed: pd.DataFrame,
    reference: pd.DataFrame,
    tolerances: dict[str, float],
    key: str = "variable",
) -> pd.DataFrame:
    """Compara `computed` con `reference` columna a columna y devuelve un informe largo.

    Columnas del informe: `variable`, `column`, `computed`, `paper`, `abs_diff`, `ok`.
    - Las celdas que el paper no reporta (NaN en `reference`) se omiten.
    - Si la réplica deja NaN donde el paper sí tiene valor, la celda queda `ok=False`
      (nunca se omite en silencio).
    - Si a `computed` le faltan filas de `reference`, se lanza `ValueError`.
    """
    missing = set(reference[key]) - set(computed[key])
    if missing:
        raise ValueError(f"A la réplica le faltan filas del paper: {sorted(missing)}")
    merged = computed.merge(reference, on=key, suffixes=("_computed", "_paper"))
    rows = []
    for col, tol in tolerances.items():
        for _, r in merged.iterrows():
            mine, paper = r[f"{col}_computed"], r[f"{col}_paper"]
            if pd.isna(paper):
                continue
            diff = float("nan") if pd.isna(mine) else abs(float(mine) - float(paper))
            rows.append(
                {
                    key: r[key],
                    "column": col,
                    "computed": float(mine),
                    "paper": float(paper),
                    "abs_diff": diff,
                    "ok": bool(diff <= tol),  # NaN <= tol es False
                }
            )
    return pd.DataFrame(rows, columns=[key, "column", "computed", "paper", "abs_diff", "ok"])
