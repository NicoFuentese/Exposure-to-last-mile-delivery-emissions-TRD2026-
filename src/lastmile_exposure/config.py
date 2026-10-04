"""Constantes y configuración global de la réplica.

Paper: §3.1 (grilla, horas), §4.2 (regresores y categorías de referencia), §4.2.3 (51 comunas)
Código de los autores: `model_vars` y `prep_data` en 02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H1, H13, D1
Estado: valores verificados contra el paper y el replication package (2026-09-29).

Aquí solo hay constantes; nada de lógica. Si un número del paper se usa en más de un
módulo, debe vivir en este archivo.
"""

from enum import StrEnum
from pathlib import Path

# --- Rutas ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"  # ignorado por git (datos confidenciales)
PACKAGE_DIR = DATA_DIR / "replication_package"  # zip de los autores, extraído
PROCESSED_DIR = DATA_DIR / "processed"  # datos derivados (ignorado por git)
OUTPUTS_DIR = ROOT / "outputs"  # resultados; ignorado por git por defecto
REFERENCE_DIR = ROOT / "reference" / "paper_tables"  # cifras publicadas (sí se versionan)
R_ORACLE_DIR = ROOT / "reference" / "r_oracle"  # contraste del ZINB con pscl (R); no es del paper


class Variant(StrEnum):
    """Variante de la réplica (AGENTS.md §7.3-D1). Cambia el resultado, no el código."""

    AS_PUBLISHED = "as_published"  # tal cual el paquete: hora y miércoles en UTC
    LOCAL_TIME = "local_time"  # America/Santiago; solo conteos, horas locales 7-19


# --- Grilla y tiempo -------------------------------------------------------------------
H3_RESOLUTION = 9  # [P §3.1]
N_HEXAGONS = 11_144  # [P §3.1]
HOURS = tuple(range(7, 23))  # 16 horas, etiquetas 7..22 [P §3.1]
N_HEXAGON_HOURS = N_HEXAGONS * len(HOURS)  # 178.304 filas [P §3.1]
LOCAL_COMPLETE_HOURS = tuple(range(7, 20))  # horas locales con los 42 días (H19)
TIMEZONE = "America/Santiago"
N_COMUNAS = 51  # clusters de los errores estándar [P §4.2.3]

# --- Regresores (11) y referencias -------------------------------------------------------
# Nombres tal como aparecen en las bases del paquete (gse_de = gse_d + gse_e).
REGRESSORS = (
    "genero_masc",
    "gse_c1a",
    "gse_c1b",
    "gse_c2",
    "gse_c3",
    "gse_de",
    "edad_menor_25",
    "edad_25_34",
    "edad_35_44",
    "edad_45_54",
    "edad_55_64",
)
# Categorías omitidas por dimensión (colinealidad de shares) [P §4.2, p.10]
REFERENCE_CATEGORIES = {"sex": "genero_fem", "age": "edad_mayor_65", "seg": "gse_ab"}
# Nombre de cada regresor en las Tablas 4 y 5 del paper
LABELS = {
    "genero_masc": "Male",
    "edad_menor_25": "Under 25",
    "edad_25_34": "25-34",
    "edad_35_44": "35-44",
    "edad_45_54": "45-54",
    "edad_55_64": "55-64",
    "edad_mayor_65": "65+",
    "gse_ab": "AB",
    "gse_c1a": "C1a",
    "gse_c1b": "C1b",
    "gse_c2": "C2",
    "gse_c3": "C3",
    "gse_de": "D+E",
}

# --- Variables resultado del paquete ------------------------------------------------------
OUTCOME_COUNT = "median_vehicles"  # Ỹ_hi (se redondea a entero para el ZINB, H11)
OUTCOME_DISTANCE = "median_distance"  # K̃_hi, en metros

# --- Filas de las Tablas 4 y 5 (mismo orden que reference/paper_tables/table4_dynamic.csv) ------
# (variable, etiqueta del paper, grupo). Las referencias (65+, AB) valen 0 en todas las columnas.
TABLE_ROWS = (
    ("genero_masc", "Male", "sex"),
    ("edad_mayor_65", "65+", "age"),
    ("edad_menor_25", "Under 25", "age"),
    ("edad_25_34", "25-34", "age"),
    ("edad_35_44", "35-44", "age"),
    ("edad_45_54", "45-54", "age"),
    ("edad_55_64", "55-64", "age"),
    ("gse_ab", "AB", "seg"),
    ("gse_c1a", "C1a", "seg"),
    ("gse_c1b", "C1b", "seg"),
    ("gse_c2", "C2", "seg"),
    ("gse_c3", "C3", "seg"),
    ("gse_de", "D+E", "seg"),
)

# --- Grupos de la Tabla 2 y ventanas de la movilidad (Wasserstein) ---------------------------
# (etiqueta del paper, columna del panel, dimensión), en el orden de la Tabla 2
TABLE2_GROUPS = (
    ("Male", "genero_masc", "sex"),
    ("Female", "genero_fem", "sex"),
    ("Under 25", "edad_menor_25", "age"),
    ("25-34", "edad_25_34", "age"),
    ("35-44", "edad_35_44", "age"),
    ("45-54", "edad_45_54", "age"),
    ("55-64", "edad_55_64", "age"),
    ("65+", "edad_mayor_65", "age"),
    ("AB", "gse_ab", "seg"),
    ("C1a", "gse_c1a", "seg"),
    ("C1b", "gse_c1b", "seg"),
    ("C2", "gse_c2", "seg"),
    ("C3", "gse_c3", "seg"),
    ("D", "gse_d", "seg"),
    ("E", "gse_e", "seg"),
)
DIMENSION_OF = {label: dimension for label, _, dimension in TABLE2_GROUPS}
# Ventanas de la mañana (10-12 h) y la tarde (20-22 h) [P §3.1]; el código de los autores las usa
# INCLUSIVAS (`hora >= 10 & hora <= 12`, `morning_range <- c(10, 12)` en heatmaps_to_latex.R).
MORNING_HOURS = (10, 11, 12)
EVENING_HOURS = (20, 21, 22)
METRIC_CRS = (
    "EPSG:32719"  # WGS 84 / UTM 19S: coordenadas en metros para medir distancias [Supuesto]
)
MOBILITY_DIR = (
    ROOT / "reference" / "mobility"
)  # W1 calculada por nosotros (no son cifras del paper)
