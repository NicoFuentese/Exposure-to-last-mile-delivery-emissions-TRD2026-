"""Shares estáticos (residenciales) para el enfoque estático.

Paper: §5.2
Código de los autores: summary_results_static*.R (conversión de `static_data`)
Hallazgos (AGENTS.md §7): H8
Estado: implementado (Fase 3).
"""

import pandas as pd

GSE_COLUMNS = ("gse_ab", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3", "gse_d", "gse_e")


def static_shares(raw: pd.DataFrame) -> pd.DataFrame:
    """Convierte la demografía estática a la misma escala que la dinámica.

    Los `gse_*` vienen en porcentaje (0-100) y se dividen por 100; luego se añade
    `gse_de = gse_d + gse_e`. El resto de las columnas ya está en proporción.
    """
    out = raw.copy()
    for col in GSE_COLUMNS:
        out[col] = out[col] / 100.0
    out["gse_de"] = out["gse_d"] + out["gse_e"]
    return out
