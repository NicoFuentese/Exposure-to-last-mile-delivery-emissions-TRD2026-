# Exposure-to-last-mile-delivery-emissions-TRD2026-

Réplica en Python de:

> Basso, F., Perotti, S., Pezoa, R., Fuentes, F., Covarrubia, J. (2026). *Exposure to last-mile delivery emissions: A novel data fusion approach*. Transportation Research Part D, 155, 105296. https://doi.org/10.1016/j.trd.2026.105296

El paper cruza, en una grilla **hexágono H3 (res. 9) × hora**, la actividad de vehículos de reparto (GPS) con la composición demográfica de la población presente (telefonía móvil) para medir qué grupos quedan más expuestos a la última milla en Santiago. Estima un **ZINB** para el conteo de vehículos y **OLS** para la distancia recorrida, con errores estándar agrupados por comuna, y compara contra un enfoque estático (demografía residencial).

> **Estado:** proyecto en curso. El detalle metodológico, los hallazgos y las decisiones abiertas están en [`AGENTS.md`](AGENTS.md), que es la referencia de trabajo.

## Contenido

```
.
├── AGENTS.md            # Guía de trabajo: metodología verificada, hallazgos, decisiones, plan
├── CLAUDE.md            # Importa AGENTS.md para Claude Code
├── README.md
├── requirements.txt     # Dependencias con versiones fijadas (Python 3.12)
├── LICENSE              # MIT
├── .venv/               # Entorno virtual (uv). No se versiona
└── data/                # Datos y paper. NO se versiona (confidencial)
    ├── Basso2026TRD.pdf
    ├── TRD_replication_share.zip        # Paquete de los autores (código R + bases)
    └── replication_package/             # El zip extraído
```

## Requisitos

- **Python 3.12**
- **[uv](https://docs.astral.sh/uv/)** para crear y gestionar el entorno virtual

Instalar `uv` (una sola vez por máquina):

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# o bien
winget install --id=astral-sh.uv -e
```

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Comprobar: `uv --version`.

## Entorno virtual

### Crear el entorno e instalar las dependencias

Desde la raíz del repositorio:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
```

### Activarlo

| Shell | Comando |
|---|---|
| PowerShell | `.venv\Scripts\Activate.ps1` |
| CMD | `.venv\Scripts\activate.bat` |
| Git Bash | `source .venv/Scripts/activate` |
| macOS / Linux | `source .venv/bin/activate` |

Si PowerShell bloquea la activación por la política de ejecución, habilita los scripts solo para esa sesión:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

Con el entorno activo, `python`, `pytest`, `ruff` y `jupyter` usan lo instalado en `.venv`. Para salir: `deactivate`.

### Usarlo sin activarlo

```bash
uv run python mi_script.py          # ejecuta con el .venv del proyecto
.venv\Scripts\python.exe mi_script.py    # Windows, llamando al intérprete directamente
```

### Instalar o actualizar dependencias

Los entornos de `uv` **no incluyen `pip`**: usa `uv pip`.

```bash
uv pip install nombre-paquete            # con el entorno activo
uv pip install --python .venv nombre-paquete   # sin activarlo
```

Si es una dependencia del proyecto, agrégala también a `requirements.txt` **con su versión fijada** (`paquete==x.y.z`). Para ver lo instalado:

```bash
uv pip list
```

### Recrear el entorno desde cero

Si el entorno se corrompe o quieres partir limpio, bórralo y créalo de nuevo:

```powershell
# Windows (PowerShell)
deactivate                      # si estaba activo
Remove-Item -Recurse -Force .venv
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
```

```bash
# macOS / Linux / Git Bash
deactivate 2>/dev/null
rm -rf .venv
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
```

### Comprobar que funciona

```bash
python -c "import statsmodels, geopandas, h3, esda; print('ok')"
pytest --version
ruff --version
```

> **En Windows la primera importación tras crear el entorno tarda varios minutos** (compilación de bytecode y escaneo del antivirus sobre ~800 MB). Es normal; las siguientes son rápidas.

## Librerías

| Grupo | Paquetes | Uso |
|---|---|---|
| Núcleo | `numpy`, `pandas`, `pyarrow`, `scipy`, `tzdata` | datos, parquet, tests, zona horaria `America/Santiago` |
| Modelos | `statsmodels` | ZINB, logit, OLS, errores estándar con cluster por comuna |
| Espacial | `h3` (v4), `shapely`, `pyproj`, `geopandas`, `libpysal`, `esda` | grilla H3, proyección a metros, mapas, Moran's I |
| Gráficos | `matplotlib` | figuras |
| Desarrollo | `pytest`, `ruff`, `ipykernel` | validación contra las tablas del paper, lint y formato, notebooks |

Las versiones exactas están en [`requirements.txt`](requirements.txt).

## Datos

Los datos del paper son **confidenciales** (*"The data that has been used is confidential"*) y **no se versionan**: `data/` está en `.gitignore`. No los subas a servicios externos ni los incluyas en commits.

Para extraer el paquete de los autores (una vez copiado el `.zip` en `data/`):

```bash
python -m zipfile -e data/TRD_replication_share.zip data/replication_package
```

El paquete incluye las bases finales de modelación y el código R original, pero **no** el GPS crudo ni los archivos diarios de distancia. Qué contiene cada archivo, sus estadísticas y sus limitaciones están en la sección 8 de [`AGENTS.md`](AGENTS.md).

## Desarrollo

```bash
pytest            # pruebas (aún no hay; se irán agregando contra las Tablas 2, 4 y 5)
ruff check .      # lint
ruff format .     # formato
```

## Hoja de ruta

| Fase | Estado |
|---|---|
| Comprensión del paper y guía de trabajo (`AGENTS.md`) | ✅ |
| Análisis del paquete de los autores y de los datos | ✅ |
| Entorno de trabajo (`uv`, `requirements.txt`) | ✅ |
| Réplica tal cual el paquete (hora UTC): ZINB y comparación con la Tabla 4/5 | ⏳ |
| Inferencia: errores con cluster por comuna, estrellas, Moran's I | ⏳ |
| Sensibilidad en hora local (`America/Santiago`) | ⏳ |
| Figuras (1, 2, 6–10) | ⏳ |
| Extensión a métricas de ruido | ⏳ |

Ya están reproducidos exactamente la **Tabla 2** y las tres columnas de distancia (OLS) de las **Tablas 4 y 5**. Los detalles, incluidas las diferencias entre el paper y el código de los autores (por ejemplo, que la hora de los conteos de vehículos está en UTC), están en `AGENTS.md`.

## Licencia

[MIT](LICENSE) © 2026 Nicolas Andres Fuentes Espinoza. El paper es propiedad de sus autores y de Elsevier; los datos son confidenciales y no están cubiertos por esta licencia.
