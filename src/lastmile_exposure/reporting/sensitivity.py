"""Comparación de dos versiones de las Tablas 4 y 5 y chequeo de las conclusiones del paper.

Paper: Tablas 4 y 5 (pp.12, 15) y mensajes principales (§5-6, pp.12-17)
Código de los autores: (no hay; comparación propia para la sensibilidad en hora local)
Hallazgos (AGENTS.md §7): D1, H1, H19, H31(d)
Estado: implementado (Fase 5): `estimate_version` (ajusta una versión completa: efectos y
    estrellas), `results_table` (une efectos y estrellas), `compare_tables` / `comparison_summary`
    (celda a celda entre dos versiones) y `robustness_checks` (cuatro conclusiones del paper,
    definidas ANTES de ver los resultados).

Una "versión" es una tabla con las columnas de `reporting.marginal_tables` y
`reporting.significance`: `variable`, `label`, `group` y, para cada columna de `COLUMNS`, el efecto
`<col>` y sus estrellas `<col>_sig` (y, opcionalmente, `<col>_p`). Las tablas impresas en el paper
(`validation.paper_tables.load_table4` / `load_table5`) tienen ese mismo formato.

Significancia: se considera significativa una celda con `*`, `**` o `***` (p < 0,05).

Efecto marginal del ZINB: aquí se usa la Ec. (4) del paper, `(1−π)·β_k·mean(μ)` (`"eq4"`), que es la
correcta. El código de los autores multiplica por (1−π) dos veces (H10); con π̂ = 0 coinciden y da
igual, pero con otras horas π̂ podría ser > 0. Se guarda también la fórmula de los autores
(`Version.zinb_authors`) para ver cuánto difiere.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.models.zinb import fit_zinb_mle
from lastmile_exposure.reporting.marginal_tables import (
    REFERENCE_VARIABLES,
    distance_marginal_table,
    zinb_marginal_column,
)
from lastmile_exposure.reporting.significance import (
    authors_script_inference_table,
    inference_table,
)

COLUMNS = ("zinb", "ols_k", "ols_kpos", "ols_logk")
STAR_LEVEL = {"": 0, ".": 1, "*": 2, "**": 3, "***": 4}
SIGNIFICANT = ("*", "**", "***")
_ID = ["variable", "label", "group"]


def results_table(effects: pd.DataFrame, inference: pd.DataFrame) -> pd.DataFrame:
    """Une efectos marginales (`reporting.marginal_tables`) con p-valores y estrellas.

    `effects` trae `variable`, `label`, `group` y las columnas de `COLUMNS` (el ZINB ya cargado
    con `zinb_marginal_column`); `inference` es `reporting.significance.inference_table`.
    """
    stats = [f"{c}_{s}" for c in COLUMNS for s in ("p", "sig")]
    return effects[[*_ID, *COLUMNS]].merge(
        inference[["variable", *stats]], on="variable", how="left", validate="one_to_one"
    )


def _levels(stars: pd.Series) -> pd.Series:
    return stars.fillna("").map(STAR_LEVEL).astype(int)


def compare_tables(base: pd.DataFrame, alt: pd.DataFrame) -> pd.DataFrame:
    """Compara `alt` contra `base` celda a celda (44 celdas no referenciales por tabla).

    Informe largo con una fila por (variable, columna): `base`, `alt`, `diff` (alt − base),
    `rel_change` (diff / |base|, NaN si base = 0), `same_sign`, las estrellas de cada versión
    (`base_sig`, `alt_sig`), `level_change` (cambio de nivel de estrellas, − ninguna = 0, `.` = 1,
    `*` = 2, `**` = 3, `***` = 4), `lost_significance` y `gained_significance` (cruza el 5 %).
    """
    b = base.set_index("variable")
    a = alt.set_index("variable")
    variables = [v for v in b.index if v not in REFERENCE_VARIABLES]
    frames = []
    for col in COLUMNS:
        frame = pd.DataFrame(
            {
                "variable": variables,
                "label": b.loc[variables, "label"].to_numpy(),
                "group": b.loc[variables, "group"].to_numpy(),
                "column": col,
                "base": b.loc[variables, col].to_numpy(dtype=float),
                "alt": a.loc[variables, col].to_numpy(dtype=float),
                "base_sig": b.loc[variables, f"{col}_sig"].fillna("").to_numpy(),
                "alt_sig": a.loc[variables, f"{col}_sig"].fillna("").to_numpy(),
            }
        )
        frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    out["diff"] = out["alt"] - out["base"]
    out["rel_change"] = (out["diff"] / out["base"].abs()).where(out["base"] != 0)
    out["same_sign"] = np.sign(out["base"]) == np.sign(out["alt"])
    out["level_change"] = _levels(out["alt_sig"]) - _levels(out["base_sig"])
    was, is_ = out["base_sig"].isin(SIGNIFICANT), out["alt_sig"].isin(SIGNIFICANT)
    out["lost_significance"] = was & ~is_
    out["gained_significance"] = ~was & is_
    return out


def comparison_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    """Resumen de `compare_tables` por columna: cambios de signo, de estrellas y magnitud."""
    grouped = comparison.groupby("column", sort=False)
    return pd.DataFrame(
        {
            "cells": grouped.size(),
            "sign_changes": grouped["same_sign"].apply(lambda s: int((~s).sum())),
            "star_changes": grouped["level_change"].apply(lambda s: int((s != 0).sum())),
            "lost_significance": grouped["lost_significance"].sum().astype(int),
            "gained_significance": grouped["gained_significance"].sum().astype(int),
            "median_abs_rel_change": grouped["rel_change"].apply(lambda s: s.abs().median()),
        }
    ).reindex(list(COLUMNS))


# ------------------------------------------------------------------ conclusiones del paper
CHECK_COLUMNS = ("zinb", "ols_kpos")  # las dos columnas que usan las Figs. 6-10
MIDDLE_CLASSES = ("gse_c1a", "gse_c1b", "gse_c2", "gse_c3")
AGES = ("edad_menor_25", "edad_25_34", "edad_35_44", "edad_45_54", "edad_55_64")


def _effects(table: pd.DataFrame, col: str) -> pd.Series:
    return table.set_index("variable")[col].astype(float)


def _is_significant(table: pd.DataFrame, col: str, variable: str) -> bool:
    return bool(table.set_index("variable").loc[variable, f"{col}_sig"] in SIGNIFICANT)


def _inverted_u(dynamic: pd.DataFrame) -> tuple[bool, str]:
    """Clase media (C1a, C1b, C2, C3) con efecto positivo y por sobre el de D+E."""
    holds, parts = True, []
    for col in CHECK_COLUMNS:
        e = _effects(dynamic, col)
        floor = max(0.0, float(e["gse_de"]))
        lowest = float(e[list(MIDDLE_CLASSES)].min())
        holds &= lowest > floor
        parts.append(f"{col}: min. clase media {lowest:.4g} vs max.(0, D+E) {floor:.4g}")
    return holds, "; ".join(parts)


def _age_peak(dynamic: pd.DataFrame) -> tuple[bool, str]:
    """El mayor efecto entre los tramos de edad es 25-34 y es positivo."""
    holds, parts = True, []
    for col in CHECK_COLUMNS:
        e = _effects(dynamic, col)[list(AGES)]
        peak = e.idxmax()
        holds &= peak == "edad_25_34" and float(e[peak]) > 0
        parts.append(f"{col}: maximo en {peak} ({float(e[peak]):.4g})")
    return holds, "; ".join(parts)


def _sex(dynamic: pd.DataFrame, static: pd.DataFrame) -> tuple[bool, str]:
    """Hombre positivo y significativo en el ZINB dinámico, y con signo opuesto en el estático."""
    dyn = float(_effects(dynamic, "zinb")["genero_masc"])
    sta = float(_effects(static, "zinb")["genero_masc"])
    significant = _is_significant(dynamic, "zinb", "genero_masc")
    holds = dyn > 0 and significant and sta < 0
    return holds, f"dinamico {dyn:.4g} (significativo: {significant}); estatico {sta:.4g}"


def _c1b_flip(dynamic: pd.DataFrame, static: pd.DataFrame) -> tuple[bool, str]:
    """C1b pasa de positivo (dinámico) a negativo (estático) en el ZINB."""
    dyn = float(_effects(dynamic, "zinb")["gse_c1b"])
    sta = float(_effects(static, "zinb")["gse_c1b"])
    return dyn > 0 > sta, f"dinamico {dyn:.4g}; estatico {sta:.4g}"


def robustness_checks(dynamic: pd.DataFrame, static: pd.DataFrame) -> pd.DataFrame:
    """Cuatro conclusiones del paper (§5-6) evaluadas sobre una versión de las Tablas 4 y 5.

    Definidas antes de mirar los resultados de la hora local (AGENTS.md D1):
    1. `gse_inverted_u`: C1a, C1b, C2 y C3 con efecto > 0 y > D+E, en el ZINB y en OLS `K̃>0`.
    2. `age_peak_25_34`: el máximo entre los tramos de edad es 25-34 (y > 0), en las mismas dos.
    3. `sex`: hombre > 0 y significativo en el ZINB dinámico, y < 0 en el ZINB estático.
    4. `c1b_flip`: C1b del ZINB pasa de > 0 (dinámico) a < 0 (estático).

    `dynamic` y `static` son tablas en el formato de `results_table`. Devuelve una fila por
    conclusión con `check`, `holds` y `detail`. Una conclusión es «robusta» a un cambio solo si
    se cumple en la versión original y en la modificada.
    """
    checks = {
        "gse_inverted_u": _inverted_u(dynamic),
        "age_peak_25_34": _age_peak(dynamic),
        "sex": _sex(dynamic, static),
        "c1b_flip": _c1b_flip(dynamic, static),
    }
    return pd.DataFrame(
        [
            {"check": name, "holds": bool(ok), "detail": detail}
            for name, (ok, detail) in checks.items()
        ]
    )


# ------------------------------------------------------------------ ajuste de una versión
PI_NEGLIGIBLE = 1e-6  # por debajo, la fórmula de los autores y la Ec. (4) coinciden en la práctica


@dataclass
class Version:
    """Una versión de la Tabla 4 (o 5): sus tablas por variante de errores estándar y su ajuste.

    - `tables`: variante → `results_table`. `paper_text` = cluster por comuna en todo (lo que dice
      el paper); en la tabla estática hay además `authors_script` (ZINB sin agrupar, error de su
      script, H26).
    - `zinb_authors`: la columna ZINB con la fórmula del código de los autores (H10), para comparar.
    - `fit`: filas, π̂, θ̂, si el máximo está en la frontera π = 0, proporción de ceros y la
      diferencia máxima entre la fórmula de los autores y la Ec. (4).
    """

    tables: dict[str, pd.DataFrame]
    zinb_authors: pd.Series
    fit: dict[str, float | int | bool]


def estimate_version(count_df: pd.DataFrame, distance_df: pd.DataFrame, *, static: bool) -> Version:
    """Ajusta las cuatro columnas de una versión de la Tabla 4 (`static=False`) o 5 (`True`).

    `count_df` y `distance_df` son `panel.count_frame` / `panel.distance_frame` (o sus versiones
    restringidas o en hora local). El ZINB se ajusta por su máximo (`fit_zinb_mle`) y su efecto
    marginal usa la Ec. (4). Errores estándar con cluster por comuna.
    """
    zinb = fit_zinb_mle(count_df)
    effects = distance_marginal_table(distance_df).assign(zinb=zinb_marginal_column(zinb, "eq4"))
    inferences = {"paper_text": inference_table(distance_df, count_df, zinb, cluster="comuna")}
    if static:
        inferences["authors_script"] = authors_script_inference_table(
            distance_df, count_df, zinb, static=True
        )
    tables = {name: results_table(effects, inf) for name, inf in inferences.items()}
    variables = [v for v, _, _ in config.TABLE_ROWS]
    zinb_authors = pd.Series(zinb_marginal_column(zinb, "authors"), index=variables)
    eq4 = pd.Series(zinb_marginal_column(zinb, "eq4"), index=variables)
    fit = {
        "n_rows": len(count_df),
        "pi": zinb.pi,
        "theta": zinb.theta,
        "boundary": zinb.boundary,
        "zero_share": float((count_df["vehicles"] == 0).mean()),
        "max_abs_authors_minus_eq4": float((zinb_authors - eq4).abs().max()),
    }
    return Version(tables=tables, zinb_authors=zinb_authors.rename("zinb_authors"), fit=fit)
