# Exposure-to-last-mile-delivery-emissions-TRD2026-

Réplica en Python de:

> Basso, F., Perotti, S., Pezoa, R., Fuentes, F., Covarrubia, J. (2026). *Exposure to last-mile delivery emissions: A novel data fusion approach*. Transportation Research Part D, 155, 105296. https://doi.org/10.1016/j.trd.2026.105296

El paper cruza, en una grilla **hexágono H3 (res. 9) × hora**, la actividad de vehículos de reparto (GPS) con la composición demográfica de la población presente (telefonía móvil) para medir qué grupos quedan más expuestos a la última milla en Santiago. Estima un **ZINB** para el conteo de vehículos y **OLS** para la distancia recorrida, con errores estándar agrupados por comuna, y compara contra un enfoque estático (demografía residencial).

> **Estado:** proyecto en curso. El detalle metodológico, los hallazgos y las decisiones abiertas están en [`AGENTS.md`](AGENTS.md), que es la referencia de trabajo.

## Estructura del Proyecto

```
.
├── AGENTS.md            # Guía de trabajo: metodología verificada, hallazgos, decisiones, plan
├── CLAUDE.md            # Importa AGENTS.md para Claude Code
├── README.md
├── pyproject.toml       # Paquete y configuración de pytest/ruff (sin dependencias)
├── requirements.txt     # Dependencias con versiones fijadas (Python 3.12)
├── LICENSE              # MIT
├── src/lastmile_exposure/   # Código de la réplica, un módulo por concepto del paper
├── reference/paper_tables/  # Cifras publicadas (Tablas 2–5) para validar la réplica
├── docs/paper_map.md    # Índice: dónde está cada ecuación, tabla y figura
├── scripts/             # Puntos de entrada por fase (delgados)
├── tests/               # Pruebas, incluida la validación contra el paper
├── notebooks/           # Solo exploración
├── outputs/             # Resultados generados. No se versiona
├── .venv/               # Entorno virtual (uv). No se versiona
└── data/                # Datos y paper. NO se versiona (confidencial)
    ├── Basso2026TRD.pdf
    ├── TRD_replication_share.zip        # Paquete de los autores, versión anterior (2026-09-29)
    ├── TRD_replication_share (1).zip    # Paquete vigente de los autores (2026-10-10)
    ├── replication_package/             # Versión anterior, extraída. Solo la lee el diagnóstico de data_base
    └── replication_package_v2/          # Paquete vigente, extraído: el que lee el pipeline
```

**¿Buscas una fórmula o un paso?** Empieza por [`docs/paper_map.md`](docs/paper_map.md): mapea cada ecuación, tabla y figura del paper a su módulo.

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
uv pip install --python .venv -e . --no-deps      # instala el paquete lastmile_exposure (editable)
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
uv pip install --python .venv -e . --no-deps      # instala el paquete lastmile_exposure (editable)
```

```bash
# macOS / Linux / Git Bash
deactivate 2>/dev/null
rm -rf .venv
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
uv pip install --python .venv -e . --no-deps      # instala el paquete lastmile_exposure (editable)
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

Para extraer el paquete vigente de los autores (una vez copiado el `.zip` en `data/`), en una carpeta nueva y vacía:

```bash
python -m zipfile -e "data/TRD_replication_share (1).zip" data/replication_package_v2
```

El paquete incluye las bases finales de modelación, los conteos y las distancias diarias (41 miércoles), las tablas 4 y 5 regeneradas por los autores y el código R original, pero **no** el GPS crudo. La versión anterior (`replication_package/`) solo se conserva por su `00_out/data_base` de 2 miércoles, que lee el diagnóstico de las estrellas; los autores lo reconocieron como un residuo de prueba. Qué contiene cada archivo, sus estadísticas y sus limitaciones están en la sección 8 de [`AGENTS.md`](AGENTS.md).

## Reproducir resultados

Con el entorno activo y los datos en `data/replication_package_v2/`:

```bash
python scripts/01_table2.py            # Tabla 2 (población flotante)
python scripts/02_distance_tables.py   # columnas de distancia de las Tablas 4 y 5
python scripts/03_zinb_tables.py        # columna ZINB de las Tablas 4 y 5 (~2 min)
python scripts/04_median_counts.py      # mediana de conteos desde los 42 archivos diarios (~1 min)
python scripts/11_median_distance.py    # mediana de distancia y tiempo desde los 41 archivos diarios (~30 s)
python scripts/05_mobility.py --use-reference   # Wasserstein/movilidad (Tabla 2); sin la bandera tarda ~10 min
python scripts/12_mobility_seeds.py --use-reference   # Wasserstein con el metodo de los autores y 200 semillas; sin la bandera ~40 min con 8 procesos
python scripts/06_inference.py          # SE por comuna y estrellas de las Tablas 4 y 5 (~8 min)
python scripts/08_dispersion_test.py    # Cameron-Trivedi (7,73): rapido
python scripts/09_moran.py              # I de Moran (0,4694 / 0,4756): rapido; la especificacion no esta identificada
python scripts/10_zero_inflation.py     # pi del ZINB (diagnostico; el paper no lo reporta): ~4 min
python scripts/07_stars_diagnosis.py    # DIAGNOSTICO con data_base (2 miercoles): NO es una replica, no usar sus resultados
```

Cada script escribe sus tablas en `outputs/as_published/tables/`, las compara celda a celda con las cifras publicadas (`reference/paper_tables/`) y termina con código 1 si alguna difiere del paper más de su redondeo. El mapa de qué está reproducido y dónde vive cada fórmula está en [`docs/paper_map.md`](docs/paper_map.md).

## Desarrollo

```bash
pytest            # constantes, estructura, modelos sintéticos y validación contra las Tablas 2, 4 y 5
pytest -m "not slow"   # omite los ajustes ZINB completos sobre datos reales (minutos)
                  # (las pruebas que usan datos confidenciales se saltan solas si no están)
ruff check .      # lint
ruff format .     # formato
```

## Hoja de ruta

| Fase | Estado |
|---|---|
| Comprensión del paper y guía de trabajo (`AGENTS.md`) | ✅ |
| Análisis del paquete de los autores y de los datos | ✅ |
| Entorno de trabajo (`uv`, `requirements.txt`) | ✅ |
| Tabla 2 y columnas de distancia (OLS) de las Tablas 4 y 5, tal cual el paquete | ✅ |
| Columna ZINB de las Tablas 4 y 5 (a la precisión impresa, 6·10⁻⁵: el máximo está en π = 0, es la NB) | ✅ |
| Mediana de conteos reconstruida desde los archivos diarios (idéntica al paper) | ✅ |
| Mediana de distancia y tiempo reconstruida desde los 41 archivos diarios del paquete v2 (idéntica al paper) | ✅ |
| Wasserstein y ranking de movilidad (Tabla 2): los autores usaron una muestra aleatoria sin semilla, así que los valores no se reproducen exactamente; con 200 semillas, 13/15 caen en la banda del 95 % y los extremos son estables (`scripts/12_mobility_seeds.py`) | 🟡 |
| Errores con cluster por comuna y estrellas: 88/88 contra las tablas regeneradas por los autores (las impresas en el paper no salen del método correcto, como reconocen) | ✅ |
| Test de Cameron–Trivedi (7,73): 7,750, dentro de la tolerancia | ✅ |
| I de Moran: la lectura literal no reproduce; las alternativas solo se acercan (~1–2 %), especificación no identificada | 🟡 |
| π (el paper no lo reporta): máximo del perfil en π = 0, IC 95 % [0, ~10⁻⁴]; diagnóstico | ℹ️ |
| Sensibilidad en hora local (`America/Santiago`), ahora con conteos y distancia | ⏳ |
| Figuras (1, 2, 6–10) | ⏳ |
| Extensión a métricas de ruido | ⏳ |

Ya están reproducidos, con código en el paquete y scripts ejecutables, la **Tabla 2** y las tres columnas de distancia (OLS) de las **Tablas 4 y 5** (al redondeo del paper), y la columna **ZINB** (a la precisión impresa: con estos datos el máximo de la verosimilitud está en π = 0, es decir la NB; el ZINB de `pscl` se detiene antes del máximo). Los detalles, incluidas las diferencias entre el paper y el código de los autores (por ejemplo, que la hora de los conteos de vehículos está en UTC), están en `AGENTS.md`.

## Licencia

[MIT](LICENSE) © 2026 Nicolas Andres Fuentes Espinoza. El paper es propiedad de sus autores y de Elsevier; los datos son confidenciales y no están cubiertos por esta licencia.
