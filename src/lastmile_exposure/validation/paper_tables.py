"""Carga de las cifras publicadas y comparación celda a celda contra la réplica.

Paper: Tablas 2 a 5
Código de los autores: (no aplica)
Hallazgos (AGENTS.md §7): §7.2 (estado de la validación)
Estado: implementado. Compara valores (Fase 3) y estrellas (`compare_stars`, Fase 4A).

Las cifras viven en `reference/paper_tables/*.csv` (ver su README).
"""

from dataclasses import dataclass

import pandas as pd

from lastmile_exposure import config


@dataclass(frozen=True)
class Tolerance:
    """Tolerancia de comparación: máx(absoluta, relativa × |valor del paper|)."""

    absolute: float = 0.0
    relative: float = 0.0

    def limit(self, paper_value: float) -> float:
        return max(self.absolute, self.relative * abs(paper_value))


# Tolerancia absoluta según la precisión con que el paper imprime cada cifra.
TABLE2_TOLERANCES = {"mean": 0.006, "std": 0.006, "mean_pct": 0.051, "std_pct": 0.051}
MARGINAL_TOLERANCE = 6e-5  # el paper imprime 4 decimales (columnas OLS)
# ZINB: la columna del paper depende de dónde detuvo su búsqueda el optimizador (la verosimilitud es
# casi plana, π → 0); ni R/pscl la reproduce al 4.º decimal (dif. máx. 0,0038). Criterio ACORDADO
# con el usuario (2026-10-03, AGENTS.md D2): error relativo de 1 % con un piso de 0,005 para los
# coeficientes cercanos a cero. Detecta fórmulas equivocadas (desvíos > 1).
ZINB_TOLERANCE = Tolerance(absolute=0.005, relative=0.01)


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
    tolerances: dict[str, float | Tolerance],
    key: str = "variable",
) -> pd.DataFrame:
    """Compara `computed` con `reference` columna a columna y devuelve un informe largo.

    Cada tolerancia es un número (error absoluto máximo) o un `Tolerance` (absoluta y/o relativa
    al valor del paper). Columnas del informe: `variable`, `column`, `computed`, `paper`,
    `abs_diff`, `limit` (el máximo permitido para esa celda) y `ok`.
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
        tolerance = tol if isinstance(tol, Tolerance) else Tolerance(absolute=float(tol))
        for _, r in merged.iterrows():
            mine, paper = r[f"{col}_computed"], r[f"{col}_paper"]
            if pd.isna(paper):
                continue
            diff = float("nan") if pd.isna(mine) else abs(float(mine) - float(paper))
            limit = tolerance.limit(float(paper))
            rows.append(
                {
                    key: r[key],
                    "column": col,
                    "computed": float(mine),
                    "paper": float(paper),
                    "abs_diff": diff,
                    "limit": limit,
                    "ok": bool(diff <= limit),  # NaN <= limit es False
                }
            )
    columns = [key, "column", "computed", "paper", "abs_diff", "limit", "ok"]
    return pd.DataFrame(rows, columns=columns)


# Test de Cameron-Trivedi (7,73): el valor depende de la versión exacta de los datos de los autores
# (la dispersión cambia ~0,03 con 41 en vez de 42 miércoles), así que se usa el mismo criterio
# relativo del ZINB (AGENTS.md D2): error relativo de 1 %.
DISPERSION_TOLERANCE = Tolerance(absolute=0.0, relative=0.01)

STAR_COLUMNS = ("zinb", "ols_k", "ols_kpos", "ols_logk")
_REFERENCE_ROWS = ("edad_mayor_65", "gse_ab")  # categorías omitidas: sin estrellas por definición


def compare_stars(inference: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Compara las estrellas de `reporting.significance.inference_table` con las del paper.

    `reference` es `load_table4()` / `load_table5()`. Informe largo con una fila por celda no
    referencial (44 por tabla): `variable`, `column`, `computed`, `paper`, `p` (p-valor calculado)
    y `ok` (las estrellas coinciden exactamente). Es la medida que decide D3 (qué variante de
    errores estándar generó las estrellas).
    """
    merged = inference.merge(reference, on="variable", suffixes=("_computed", "_paper"))
    merged = merged[~merged["variable"].isin(_REFERENCE_ROWS)]
    rows = []
    for col in STAR_COLUMNS:
        for _, r in merged.iterrows():
            mine, paper = r[f"{col}_sig_computed"], r[f"{col}_sig_paper"]
            rows.append(
                {
                    "variable": r["variable"],
                    "column": col,
                    "computed": mine,
                    "paper": paper,
                    "p": r[f"{col}_p"],
                    "ok": bool(mine == paper),
                }
            )
    return pd.DataFrame(rows, columns=["variable", "column", "computed", "paper", "p", "ok"])


def stars_summary(report: pd.DataFrame) -> pd.DataFrame:
    """Resumen de `compare_stars`: celdas con estrellas iguales y total, por columna."""
    grouped = report.groupby("column")["ok"].agg(matches="sum", cells="count")
    return grouped.reindex(list(STAR_COLUMNS)).astype(int)


def load_paper_scalars() -> pd.Series:
    """Cifras sueltas del texto del paper (`paper_scalars.csv`), indexadas por `name`.

    Hoy: `cameron_trivedi_dispersion` (7,73), `moran_i_distance` (0,4694) y
    `moran_i_vehicles` (0,4756).
    """
    df = pd.read_csv(config.REFERENCE_DIR / "paper_scalars.csv")
    return df.set_index("name")["value"].astype(float)


def load_pscl_oracle(tag: str) -> pd.Series:
    """Parámetros del ZINB estimado con `pscl` (R) para `tag` = "dynamic" | "static".

    Índice: `inflate_const`, `const`, los 11 regresores, `alpha` (= 1/θ), `loglik` y
    `ame_authors:<regresor>`. No son cifras del paper (ver `reference/r_oracle/README.md`).
    """
    df = pd.read_csv(config.R_ORACLE_DIR / f"zinb_pscl_{tag}.csv")
    return df.set_index("name")["value"]


def load_cluster_se_oracle(tag: str) -> pd.DataFrame:
    """Errores estándar con cluster por comuna calculados en R (`sandwich::vcovCL`), `tag` =
    "dynamic" | "static". Índice: `(Intercept)` y los 11 regresores; columnas: `zinb_se_cluster`
    (bloque de conteo de `vcovCL(zeroinfl)`), `zinb_se_iid`, `nb_se_cluster`, `ols_k_se_cluster`,
    `ols_logk_se_cluster`, `ols_pos_se_cluster` y los coeficientes (`reference/r_oracle/`).
    No son cifras del paper.
    """
    return pd.read_csv(config.R_ORACLE_DIR / f"cluster_se_{tag}.csv").set_index("name")


def load_mobility_reference() -> pd.Series:
    """W1 en metros por grupo de la Tabla 2 calculada por nosotros (`reference/mobility/`).

    No son cifras del paper y no reproducen los valores publicados (AGENTS.md H24).
    """
    df = pd.read_csv(config.MOBILITY_DIR / "wasserstein_w1_utm_pooled.csv")
    return df.set_index("group")["w1_m"]
