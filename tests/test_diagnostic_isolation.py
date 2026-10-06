"""El diagnóstico con `data_base` está aislado del pipeline (AGENTS.md H26).

`validation/stars_diagnosis.py` usa datos que NO son los del paper (la mediana de los dos primeros
miércoles). Estas pruebas garantizan que no se cuele en resultados de la réplica: nadie del
pipeline lo importa, solo escribe en `outputs/diagnostics/` y todo lo que produce va rotulado.
No necesitan los datos confidenciales.
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.validation import stars_diagnosis as diag

SRC = Path(config.ROOT) / "src" / "lastmile_exposure"
SCRIPTS = Path(config.ROOT) / "scripts"
TARGET = "stars_diagnosis"
ALLOWED_SCRIPTS = {"07_stars_diagnosis.py"}


def _imports_target(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names = [node.module or "", *[alias.name for alias in node.names]]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        else:
            continue
        if any(TARGET in name for name in names):
            return True
    return False


def test_no_pipeline_module_imports_the_diagnostic():
    offenders = [
        str(p.relative_to(SRC))
        for p in SRC.rglob("*.py")
        if p.name != f"{TARGET}.py" and _imports_target(p)
    ]
    assert not offenders, f"El pipeline no puede importar el diagnóstico: {offenders}"


def test_only_the_diagnostic_script_uses_it():
    offenders = [
        p.name for p in SCRIPTS.glob("*.py") if p.name not in ALLOWED_SCRIPTS and _imports_target(p)
    ]
    assert not offenders, f"Solo 07_stars_diagnosis.py puede usarlo: {offenders}"


def test_the_diagnostic_declares_itself_loudly():
    doc = diag.__doc__ or ""
    assert "NO ES UNA RÉPLICA" in doc and "ADVERTENCIA" in doc
    assert diag.DIAGNOSTIC_ONLY is True
    assert "DIAGNOSTICO" in diag.BANNER and "NO ES UNA REPLICA" in diag.BANNER
    assert diag.FILE_PREFIX.startswith("DIAGNOSTICO")
    assert "as_published" not in diag.diagnostics_dir().parts


def test_the_diagnostic_never_writes_into_as_published(tmp_path, monkeypatch):
    table = pd.DataFrame({"variable": ["a"], "fuente": [diag.SOURCE_LABEL]})
    report = pd.DataFrame({"variable": ["a"], "ok": [True], "fuente": [diag.SOURCE_LABEL]})
    # una carpeta de resultados "as_published" debe ser rechazada
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "as_published")
    with pytest.raises(ValueError, match="as_published"):
        diag.write_diagnostic("dynamic", table, report)
    assert not (tmp_path / "as_published").exists()
    # y en una carpeta normal escribe solo archivos rotulados y un LEEME
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path / "outputs")
    diag.write_diagnostic("dynamic", table, report)
    written = sorted(p.name for p in (tmp_path / "outputs" / diag.OUTPUT_DIRNAME).iterdir())
    assert written == [
        "DIAGNOSTICO_data_base_inference_dynamic.csv",
        "DIAGNOSTICO_data_base_stars_dynamic.csv",
        "LEEME_DIAGNOSTICO.txt",
    ]
    leeme = (tmp_path / "outputs" / diag.OUTPUT_DIRNAME / "LEEME_DIAGNOSTICO.txt").read_text(
        encoding="utf-8"
    )
    assert "NO ES UN RESULTADO DE LA REPLICA" in leeme


def test_data_base_frames_are_not_the_papers_dataset():
    """El cargador apunta a `00_out/data_base`, no a `00_data`."""
    assert diag.DATA_BASE_DIR.parts[-2:] == ("00_out", "data_base")
    assert "00_data" not in diag.DATA_BASE_DIR.parts
