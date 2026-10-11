"""Carga de las cifras publicadas y comparación celda a celda contra la réplica.

Paper: Tablas 2 a 5
Código de los autores: (no aplica)
Hallazgos (AGENTS.md §7): §7.2 (estado de la validación)
Estado: implementado. Compara valores (Fase 3) y estrellas (`compare_stars`, Fase 4A).

Las cifras viven en `reference/paper_tables/*.csv` (ver su README). Además, `load_authors_reference`
lee las Tablas 4 y 5 REGENERADAS por los autores con los datos de 42 miércoles (paquete,
`00_out/reference_tables_42wed/`): los coeficientes son los publicados, pero las estrellas del paper
NO corresponden a esas tablas (los autores lo reconocen), así que ellas, no el paper, son el
objetivo de validación de las estrellas. Son datos del paquete, no se versionan.
"""

import re
from dataclasses import dataclass
from pathlib import Path

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
MARGINAL_TOLERANCE = 6e-5  # el paper imprime 4 decimales (columnas OLS y ZINB)
# ZINB: la columna del paper es numéricamente la NB (π = 0), el máximo de la verosimilitud (H29):
# coincide con `fit_zinb_mle` a la precisión que imprime (dif. máx. 5,7e-5 y 4,5e-5), igual que
# las columnas OLS. Criterio ACORDADO con el usuario (2026-10-10, AGENTS.md D2), que endurece el
# relativo de 1 % con piso 0,005 del 2026-10-03: ese valía para el ZINB de `statsmodels` (que no
# alcanza la frontera, dif. hasta 0,0321) y para `pscl` (dif. hasta 0,0038), no para el máximo.
ZINB_TOLERANCE = Tolerance(absolute=MARGINAL_TOLERANCE)


def load_reference(name: str, *, text_stars: bool = False) -> pd.DataFrame:
    """Lee `reference/paper_tables/<name>.csv`.

    `text_stars=True` conserva las estrellas vacías como "" (Tablas 4-5); si no, las celdas
    vacías quedan NaN y las columnas numéricas (Tablas 2-3).
    """
    return pd.read_csv(config.REFERENCE_DIR / f"{name}.csv", keep_default_na=not text_stars)


def load_table2() -> pd.DataFrame:
    return load_reference("table2_floating_population")


def load_fig7_bars() -> pd.DataFrame:
    """Etiquetas de las barras de la Fig. 7 (`label`, `nox_g`, `pm_g`), leídas de ella (H36)."""
    return load_reference("fig7_bars")


def load_table4() -> pd.DataFrame:
    return load_reference("table4_dynamic", text_stars=True)


def load_table5() -> pd.DataFrame:
    return load_reference("table5_static", text_stars=True)


# Tablas regeneradas por los autores (summary_results_cluster.R y summary_results_static_cluster.R)
AUTHORS_REFERENCE_FOLDERS = {
    "dynamic": ("table4_dynamic_clustered", "Log OLS"),
    "static": ("table5_static_clustered", "Log-Linear"),
}
AUTHORS_REFERENCE_COLUMNS = {
    "nb": "NB",
    "zinb": "ZINB",
    "ols_k": "OLS",
    "ols_kpos": "OLS (no zero)",
}
_CELL = re.compile(r"^(-?\d+(?:\.\d+)?)(\*{1,3}|\.)?$")


def authors_reference_dir() -> Path:
    """Carpeta `00_out/reference_tables_42wed` del paquete vigente."""
    return config.PACKAGE_DIR / "00_out" / "reference_tables_42wed"


def load_authors_reference(tag: str) -> pd.DataFrame:
    """Tabla 4 (`tag="dynamic"`) o 5 (`"static"`) regenerada por los autores, con la forma de
    `load_table4()`: `variable` y, por columna, el valor y sus estrellas (`<col>`, `<col>_sig`).

    Columnas: `nb` (glm.nb), `zinb` (pscl), `ols_k`, `ols_kpos` y `ols_logk`. Notas:
    - La columna `nb` es la que coincide con la "ZINB" del paper (H23): la ZINB de `pscl` se
      detiene antes del máximo.
    - `ols_logk` dinámica viene multiplicada por la media de `K̃>0` (490,52; H9): solo sirve para
      las estrellas. La estática es el coeficiente crudo.
    - En la tabla estática el cluster del `zinb` queda NULL (H26) y no se agrupa por comuna; las
      estrellas del `nb` (las 11 son `***`) indican lo mismo.
    """
    folder, log_name = AUTHORS_REFERENCE_FOLDERS[tag]
    path = authors_reference_dir() / folder / "selected_models_marginal_effects.csv"
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    variable_of = {label: variable for variable, label, _ in config.TABLE_ROWS}
    unknown = set(raw["Variable"]) - set(variable_of)
    if unknown:
        raise ValueError(f"{path.name}: filas que no son de la Tabla 4/5: {sorted(unknown)}")
    out = pd.DataFrame({"variable": raw["Variable"].map(variable_of)})
    for key, column in {**AUTHORS_REFERENCE_COLUMNS, "ols_logk": log_name}.items():
        cells = raw[column].map(_CELL.match)
        if cells.isna().any():
            raise ValueError(f"{path.name}: celdas ilegibles en {column!r}")
        out[key] = cells.map(lambda m: float(m.group(1)))
        out[f"{key}_sig"] = cells.map(lambda m: m.group(2) or "")
    return out


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

# I de Moran: la especificación del paper no está identificada (matriz de pesos y agregación en el
# tiempo sin definir). Etiquetas acordadas: "exacto" = coincide en el cuarto decimal que imprime el
# paper (|dif| <= 0,0005); "aproximado" = dentro del 2 % relativo, lo que NO identifica la
# especificación (con dos elecciones libres es fácil acercarse por casualidad); el resto,
# "no reproduce".
MORAN_EXACT = Tolerance(absolute=0.0005)
MORAN_APPROX = Tolerance(relative=0.02)


def moran_agreement(value: float, paper: float) -> str:
    """Etiqueta de una I de Moran frente al paper: `exacto`, `aproximado` o `no reproduce`."""
    diff = abs(value - paper)
    if diff <= MORAN_EXACT.limit(paper):
        return "exacto"
    if diff <= MORAN_APPROX.limit(paper):
        return "aproximado"
    return "no reproduce"


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


MOBILITY_SEEDS_FILE = "wasserstein_authors_seeds_km.csv"


def load_mobility_seeds_reference() -> pd.DataFrame:
    """W1 en km de los 15 grupos por semilla, con el método del script de los autores.

    Una fila por semilla (índice `seed`) y una columna por grupo de la Tabla 2
    (`reference/mobility/`). Son agregados calculados por nosotros sobre los datos confidenciales,
    no cifras del paper (AGENTS.md H24).
    """
    return pd.read_csv(config.MOBILITY_DIR / MOBILITY_SEEDS_FILE, index_col="seed")
