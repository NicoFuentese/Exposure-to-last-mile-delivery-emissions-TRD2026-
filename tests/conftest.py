"""Fixtures compartidas.

Las pruebas que usan los datos confidenciales (data/replication_package_v2/) se SALTAN si esos
datos no están, para que el repositorio se pueda probar sin ellos. Los datos se cargan una
sola vez por sesión.
"""

import pytest

from lastmile_exposure import config


def _require_data():
    if not (config.PACKAGE_DIR / "00_data" / "miercoles_rm.csv").exists():
        pytest.skip("Datos confidenciales no disponibles en data/replication_package_v2/")


@pytest.fixture(scope="session")
def legacy_data_base():
    """`00_out/data_base` de 2 miércoles (residuo de prueba, H26); solo existe en el paquete
    anterior. Las pruebas del diagnóstico se saltan si no está."""
    path = config.LEGACY_PACKAGE_DIR / "00_out" / "data_base"
    if not (path / "hexagon_model_median_wednesdays_RM.csv").exists():
        pytest.skip("El paquete anterior (data_base de 2 miércoles) no está en data/")
    return path


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


@pytest.fixture(scope="session")
def zinb_dynamic():
    """MLE del ZINB sobre la base dinámica completa (~30 s); se ajusta una sola vez.

    Con estos datos el máximo está en la frontera π = 0 (H29), así que es la NB (`fit_zinb_mle`).
    """
    _require_data()
    from lastmile_exposure.models.zinb import fit_zinb_mle
    from lastmile_exposure.panel import count_frame

    return fit_zinb_mle(count_frame())


@pytest.fixture(scope="session")
def zinb_static():
    """MLE del ZINB con la demografía estática (~1 min); se ajusta una sola vez."""
    _require_data()
    from lastmile_exposure.models.zinb import fit_zinb_mle
    from lastmile_exposure.panel import count_frame

    return fit_zinb_mle(count_frame(static=True))


@pytest.fixture(scope="session")
def model_frames():
    """Marcos de modelación (conteo y distancia) dinámicos y estáticos, sin ajustar nada."""
    _require_data()
    from lastmile_exposure.panel import count_frame, distance_frame

    return {
        tag: {"count": count_frame(static=static), "distance": distance_frame(static=static)}
        for tag, static in (("dynamic", False), ("static", True))
    }


@pytest.fixture(scope="session")
def zero_inflation_reports(model_frames):
    """Perfil de π (NB, grilla, máximo, test de frontera e IC) de las dos tablas (~3 min)."""
    from lastmile_exposure.inference.zero_inflation import zero_inflation_report

    return {tag: zero_inflation_report(model_frames[tag]["count"]) for tag in model_frames}


@pytest.fixture(scope="session")
def daily_metrics():
    """Los 41 archivos diarios de distancia y tiempo (horas 7-22, UTC); se leen una sola vez."""
    _require_data()
    from lastmile_exposure.io.daily_metrics import load_daily_metrics

    return load_daily_metrics()


@pytest.fixture(scope="session")
def daily_counts():
    """Los 42 archivos diarios de conteos (horas 7-22, UTC); se leen una sola vez."""
    _require_data()
    from lastmile_exposure.io.daily_counts import load_daily_counts

    return load_daily_counts()
