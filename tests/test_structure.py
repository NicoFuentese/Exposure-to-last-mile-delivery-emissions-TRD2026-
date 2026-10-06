"""Convención de documentación: todo módulo dice a qué parte del paper corresponde.

Cada módulo de `lastmile_exposure` debe abrir con un docstring que incluya las líneas
`Paper:`, `Código de los autores:`, `Hallazgos` y `Estado:`. Así cualquiera puede buscar
una fórmula o un paso y llegar a su origen (ver docs/paper_map.md).
"""

import importlib
import pkgutil

import lastmile_exposure

REQUIRED = ("Paper:", "Código de los autores:", "Hallazgos", "Estado:")
EXEMPT = {"lastmile_exposure"}  # el __init__ raíz apunta a docs/paper_map.md


def _all_modules():
    yield lastmile_exposure.__name__
    for info in pkgutil.walk_packages(lastmile_exposure.__path__, "lastmile_exposure."):
        yield info.name


def test_every_module_documents_its_paper_origin():
    missing = {}
    for name in _all_modules():
        if name in EXEMPT:
            continue
        doc = importlib.import_module(name).__doc__ or ""
        absent = [r for r in REQUIRED if r not in doc]
        if absent:
            missing[name] = absent
    assert not missing, f"Módulos sin la documentación requerida: {missing}"


def test_test_file_names_are_unique():
    """Sin `__init__.py` en `tests/`, pytest no puede importar dos archivos con el mismo nombre
    (falla toda la recolección): cada `test_*.py` debe tener un nombre único en `tests/`."""
    from collections import Counter
    from pathlib import Path

    tests_dir = Path(__file__).resolve().parent
    names = Counter(p.name for p in tests_dir.rglob("test_*.py"))
    duplicated = sorted(name for name, count in names.items() if count > 1)
    assert not duplicated, f"Nombres de prueba repetidos: {duplicated}"
