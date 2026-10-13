"""Tablas 4 y 5 en el formato del paper, con la réplica y las cifras impresas lado a lado.

Paper: Tablas 4 (dinámico, p.12) y 5 (estático, p.15)
Código de los autores: `wide_effects` y `add_significance` en 02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H23, H26, H31, H32, D3
Estado: implementado. Solo presenta: no ajusta ni calcula modelos. Junta los valores de
    `reporting.marginal_tables`, las estrellas de `reporting.significance` y las cifras de
    `reference/paper_tables/`, y reutiliza `validation.paper_tables.compare_columns` y
    `compare_stars` para decidir qué celdas coinciden.

Cada celda se escribe como el paper: el valor sin ceros de más (hasta 4 decimales) seguido de sus
estrellas (`3.5569***`). Las estrellas de la réplica dependen de la variante de errores estándar
(`paper_text` o `authors_script`, D3); las impresas en el paper no salen del método correcto y los
autores lo reconocen (H31, H32), así que su coincidencia es informativa, no un objetivo.
"""

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.reporting.marginal_tables import REFERENCE_VARIABLES
from lastmile_exposure.reporting.significance import COLUMNS
from lastmile_exposure.validation.paper_tables import compare_columns, compare_stars

COLUMN_TITLES = {
    "zinb": "ZINB",
    "ols_k": "OLS",
    "ols_kpos": "OLS (no zero)",
    "ols_logk": "Log OLS",
}
# Los valores de la réplica se guardan a 4 decimales (como los imprime el paper): una diferencia de
# una unidad en la última cifra es redondeo (la diferencia sin redondear es <= 6e-5 y está en
# `comparison_table{4,5}.csv`), no una discrepancia.
DISPLAY_TOLERANCE = 1.0001e-4
VALUE_MARK = "‡"  # el valor difiere del impreso más que su redondeo
STARS_MARK = "†"  # las estrellas difieren de las impresas

# Qué dice cada variante de estrellas de la réplica (las dos que muestra D3)
VARIANT_NOTES = {
    "paper_text": (
        "Estrellas de la réplica: errores estándar con cluster por comuna en las cuatro columnas "
        "(lo que dice el paper, §4.2.3)."
    ),
    "authors_script": (
        "Estrellas de la réplica: como el script de los autores, que en el ZINB estático deja el "
        "cluster en `NULL` y no agrupa por comuna (error de su código, H26); se reproduce a "
        "propósito para comparar con su tabla de referencia, no es lo que dice el paper."
    ),
}
STARS_CAVEAT = (
    "Las estrellas impresas en el paper no salen del método correcto y los autores lo reconocen "
    "(H31, H32): que la réplica no las iguale todas no es una falla de la réplica. El objetivo de "
    "las estrellas son las tablas que regeneraron los autores (`outputs/reproduction/report.md`)."
)


def format_value(value: float) -> str:
    """Valor como lo imprime el paper: hasta 4 decimales, sin ceros de más (`0`, `-0.313`)."""
    text = f"{float(value) + 0.0:.4f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def format_cell(value: float, stars: object = "") -> str:
    """Celda `valor + estrellas` (las estrellas ausentes o NaN no se escriben)."""
    sig = "" if pd.isna(stars) else str(stars)
    return f"{format_value(value)}{sig}"


def side_by_side(
    values: pd.DataFrame, inference: pd.DataFrame, reference: pd.DataFrame
) -> pd.DataFrame:
    """Tabla 4 o 5 con la réplica y el paper lado a lado, una fila por `config.TABLE_ROWS`.

    `values` es `table{4,5}_complete_no_stars` (columnas `variable`, `zinb`, `ols_k`, `ols_kpos`,
    `ols_logk`); `inference` es la salida de `significance.inference_table` (columnas
    `<col>_sig`); `reference` es `load_table4()` o `load_table5()`.

    Para cada columna de `significance.COLUMNS` devuelve `<col>_replica` y `<col>_paper` (texto
    con las estrellas), `<col>_value_ok` (valor a una unidad de la última cifra impresa) y
    `<col>_stars_ok` (estrellas iguales; las categorías de referencia no se comparan y valen
    True).
    """
    inference = inference.copy()
    for col in COLUMNS:  # las estrellas vacías se leen como NaN desde un CSV
        inference[f"{col}_sig"] = inference[f"{col}_sig"].fillna("")
    value_ok = compare_columns(values, reference, dict.fromkeys(COLUMNS, DISPLAY_TOLERANCE)).pivot(
        index="variable", columns="column", values="ok"
    )
    stars_ok = compare_stars(inference, reference).pivot(
        index="variable", columns="column", values="ok"
    )
    mine, sig = values.set_index("variable"), inference.set_index("variable")
    paper = reference.set_index("variable")
    rows = []
    for variable, label, group in config.TABLE_ROWS:
        row: dict[str, object] = {"variable": variable, "label": label, "group": group}
        for col in COLUMNS:
            row[f"{col}_replica"] = format_cell(
                mine.at[variable, col], sig.at[variable, f"{col}_sig"]
            )
            row[f"{col}_paper"] = format_cell(
                paper.at[variable, col], paper.at[variable, f"{col}_sig"]
            )
            row[f"{col}_value_ok"] = bool(value_ok.at[variable, col])
            row[f"{col}_stars_ok"] = (
                True if variable in REFERENCE_VARIABLES else bool(stars_ok.at[variable, col])
            )
        rows.append(row)
    return pd.DataFrame(rows)


def agreement(table: pd.DataFrame) -> pd.DataFrame:
    """Cuántas celdas coinciden, por columna: valores (13 por columna) y estrellas (11)."""
    body = table[~table["variable"].isin(REFERENCE_VARIABLES)]
    rows = [
        {
            "column": col,
            "values_ok": int(table[f"{col}_value_ok"].sum()),
            "values": len(table),
            "stars_ok": int(body[f"{col}_stars_ok"].sum()),
            "stars": len(body),
        }
        for col in COLUMNS
    ]
    return pd.DataFrame(rows)


def to_markdown(table: pd.DataFrame, title: str, variant: str) -> str:
    """La tabla en Markdown: `réplica | paper` por columna, marcas de diferencia y resumen."""
    header = ["Variable"] + [
        f"{COLUMN_TITLES[c]} {side}" for c in COLUMNS for side in ("réplica", "paper")
    ]
    lines = [
        f"# {title}",
        "",
        VARIANT_NOTES[variant],
        "",
        f"`{VALUE_MARK}` el valor difiere del impreso en más de una unidad de su última cifra; "
        f"`{STARS_MARK}` las estrellas difieren de las impresas. "
        "La réplica se guarda a 4 decimales: una diferencia de 0.0001 en la última cifra es "
        "redondeo (sin redondear, la diferencia máxima es de 6e-5; ver `comparison_table*.csv`). "
        "Las categorías de referencia (65+ y AB) valen 0 por definición.",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|",
    ]
    for _, r in table.iterrows():
        cells = [r["label"]]
        for col in COLUMNS:
            marks = ("" if r[f"{col}_value_ok"] else VALUE_MARK) + (
                "" if r[f"{col}_stars_ok"] else STARS_MARK
            )
            cells += [f"{r[f'{col}_replica']} {marks}".strip(), r[f"{col}_paper"]]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "| Columna | Valores iguales (±0.0001) | Estrellas iguales |", "|---|---:|---:|"]
    summary = agreement(table)
    for _, r in summary.iterrows():
        lines.append(
            f"| {COLUMN_TITLES[r['column']]} | {r['values_ok']}/{r['values']} | "
            f"{r['stars_ok']}/{r['stars']} |"
        )
    lines.append(
        f"| **Total** | {summary['values_ok'].sum()}/{summary['values'].sum()} | "
        f"{summary['stars_ok'].sum()}/{summary['stars'].sum()} |"
    )
    lines += ["", STARS_CAVEAT, ""]
    return "\n".join(lines)
