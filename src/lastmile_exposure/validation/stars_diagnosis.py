"""DIAGNÓSTICO de las estrellas con `00_out/data_base`. NO ES UNA RÉPLICA.

*** ADVERTENCIA ***  Este módulo existe SOLO para validar y probar por qué las estrellas
publicadas no coinciden con las estimaciones (H26). NO sirve para la réplica del paper y sus
resultados NO deben usarse como inferencia, ni en tablas, ni en figuras, ni citarse como
resultados de la réplica:

- `00_out/data_base` NO es la base del paper: sus conteos son la mediana de solo los DOS primeros
  miércoles (2024-01-03 y 2024-01-10), no de los 41–42 del paper, y sus coeficientes no son los
  publicados. Con 2 días de datos los errores estándar y las estrellas no valen como inferencia.
- Aquí solo se usa para comprobar la hipótesis de que las estrellas del paper se generaron con
  esa base (los scripts de los autores la leen por defecto): con ella coinciden 78 de 88 estrellas
  frente a 61 de 88 con `00_data`. Es evidencia sugerente, no una prueba (quedan 10 celdas
  distintas).
- Ningún módulo del pipeline puede importar este módulo (lo verifica
  `tests/test_diagnostic_isolation.py`) y sus salidas van siempre a `outputs/diagnostics/`, nunca
  a `outputs/as_published/`, con el nombre y la columna `fuente` rotulados como diagnóstico.

Paper: Tablas 4 y 5 (estrellas de significancia)
Código de los autores: summary_results_cluster.R y summary_results_static_cluster.R (leen
    `00_out/data_base` por defecto, `data_path`)
Hallazgos (AGENTS.md §7): H6, H25, H26
Estado: implementado (Fase 4A, diagnóstico). Punto de entrada: `scripts/07_stars_diagnosis.py`.
"""

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.models.zinb import fit_zinb
from lastmile_exposure.panel import attach_regressors
from lastmile_exposure.reporting.significance import authors_script_inference_table
from lastmile_exposure.validation.paper_tables import (
    compare_stars,
    load_table4,
    load_table5,
    stars_summary,
)

DIAGNOSTIC_ONLY = True
SOURCE_LABEL = "DIAGNOSTICO_data_base_2_miercoles"
DATA_BASE_DIR = config.PACKAGE_DIR / "00_out" / "data_base"
OUTPUT_DIRNAME = "diagnostics"
FILE_PREFIX = "DIAGNOSTICO_data_base_"
COUNTS_FILE = "hexagon_model_median_wednesdays_RM.csv"
DISTANCE_FILE = "hexagon_model_median_wednesday_alternative_metrics_RM.csv"
TABLES = (("dynamic", False, load_table4), ("static", True, load_table5))

BANNER = (
    "=" * 78 + "\n  DIAGNOSTICO: NO ES UNA REPLICA. Usa data_base (mediana de los 2 primeros\n"
    "  miercoles), NO la base del paper. No usar estos resultados como inferencia,\n"
    "  ni en tablas o figuras. Solo sirve para probar por que las estrellas\n"
    "  publicadas no coinciden con las estimaciones (AGENTS.md H26).\n" + "=" * 78
)
README_TEXT = (
    "DIAGNOSTICO - NO ES UN RESULTADO DE LA REPLICA\n\n"
    "Estos archivos se calcularon con 00_out/data_base (conteos y distancias de los DOS\n"
    "primeros miercoles de 2024), no con la base del paper (41-42 miercoles). Sirven solo para\n"
    "comprobar la hipotesis de que las estrellas publicadas se generaron con esa base\n"
    "(AGENTS.md H26). No son inferencia valida y no deben usarse en tablas, figuras ni citarse\n"
    "como resultados de la replica.\n"
)


def diagnostics_dir():
    """Carpeta de salida del diagnóstico (nunca `outputs/as_published/`)."""
    return config.OUTPUTS_DIR / OUTPUT_DIRNAME


def load_data_base_frames(*, static: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(marco de conteos, marco de distancia) construidos con `data_base`, no con `00_data`."""
    counts = pd.read_csv(DATA_BASE_DIR / COUNTS_FILE)
    counts = counts.assign(vehicles=np.round(counts[config.OUTCOME_COUNT]))
    distance = pd.read_csv(DATA_BASE_DIR / DISTANCE_FILE)
    return (
        attach_regressors(counts, "vehicles", static=static),
        attach_regressors(distance, config.OUTCOME_DISTANCE, static=static),
    )


def diagnose_table(tag: str, static: bool, load_reference) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(tabla de inferencia, informe de estrellas) de una tabla, con la lógica del script."""
    counts, distance = load_data_base_frames(static=static)
    zinb = fit_zinb(counts)
    table = authors_script_inference_table(distance, counts, zinb, static=static)
    table["fuente"] = SOURCE_LABEL
    report = compare_stars(table, load_reference())
    report["fuente"] = SOURCE_LABEL
    return table, report


def residual_cells(report: pd.DataFrame) -> pd.DataFrame:
    """Celdas cuyas estrellas siguen distintas de las del paper."""
    return report.loc[~report["ok"], ["variable", "column", "computed", "paper", "p"]]


def write_diagnostic(tag: str, table: pd.DataFrame, report: pd.DataFrame) -> None:
    """Guarda la tabla y el informe en `outputs/diagnostics/`, rotulados como diagnóstico."""
    out_dir = diagnostics_dir()
    if "as_published" in out_dir.parts:
        raise ValueError("el diagnóstico no puede escribir en outputs/as_published")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "LEEME_DIAGNOSTICO.txt").write_text(README_TEXT, encoding="utf-8")
    table.round(6).to_csv(out_dir / f"{FILE_PREFIX}inference_{tag}.csv", index=False)
    report.to_csv(out_dir / f"{FILE_PREFIX}stars_{tag}.csv", index=False)


def run_diagnosis(*, write: bool = True) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    """Calcula el diagnóstico de las dos tablas; devuelve `{tag: (tabla, informe)}`."""
    results = {}
    for tag, static, load_reference in TABLES:
        table, report = diagnose_table(tag, static, load_reference)
        if write:
            write_diagnostic(tag, table, report)
        results[tag] = (table, report)
    return results


def summarize(results: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> pd.DataFrame:
    """Estrellas iguales por tabla y columna (de 11 por columna)."""
    return pd.DataFrame({tag: stars_summary(rep)["matches"] for tag, (_, rep) in results.items()}).T
