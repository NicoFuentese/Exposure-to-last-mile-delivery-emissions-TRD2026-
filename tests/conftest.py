"""Fixtures compartidas.

Las pruebas que usan los datos confidenciales (data/replication_package/) se SALTAN si esos
datos no están, para que el repositorio se pueda probar sin ellos. Los datos se cargan una
sola vez por sesión.
"""

import pytest

from lastmile_exposure import config


def _require_data():
    if not (config.PACKAGE_DIR / "00_data" / "miercoles_rm.csv").exists():
        pytest.skip("Datos confidenciales no disponibles en data/replication_package/")


@pytest.fixture(scope="session")
def panel():
    _require_data()
    from lastmile_exposure.io.panel import load_panel

    return load_panel()


@pytest.fixture(scope="session")
def distance_tables():
    """Columnas de distancia de las Tablas 4 (dinámico) y 5 (estático)."""
    _require_data()
    from lastmile_exposure.panel import distance_frame
    from lastmile_exposure.reporting.marginal_tables import distance_marginal_table

    return {
        "dynamic": distance_marginal_table(distance_frame()),
        "static": distance_marginal_table(distance_frame(static=True)),
    }
