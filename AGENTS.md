# AGENTS.md — Réplica en Python de Basso et al. (2026)

Guía para agentes (y personas) que trabajen en este repositorio. Contiene lo verificado del paper, las reglas de trabajo y las decisiones abiertas. **Léelo entero antes de escribir código.**

- **Paper:** Basso, Perotti, Pezoa, Fuentes, Covarrubia (2026). *Exposure to last-mile delivery emissions: A novel data fusion approach*. Transportation Research Part D 155, 105296. DOI 10.1016/j.trd.2026.105296. Archivo local: `data/Basso2026TRD.pdf` (21 páginas; la numeración impresa coincide con la del PDF).
- **Objetivo final:** replicar la metodología y los resultados del paper (Tablas 4 y 5, Figs. 6–10) con Python.
- **Idioma:** conversar y documentar en español; identificadores de código en inglés, con la notación del paper (ver §9).

---

## 0. Convenciones de procedencia (cómo leer este archivo)

Cada dato lleva una etiqueta de dónde sale, para separar lo que dice el paper de lo que inferimos:

| Etiqueta | Significado |
|---|---|
| `[P §x, p.N]` | Dicho explícitamente en el paper (sección, página impresa). Cifras de tablas verificadas contra la capa de texto del PDF. |
| `[Derivado]` | Cálculo propio a partir de cifras del paper. No está en el paper. |
| `[Datos]` | Observado en los archivos de `data/` (con fecha del perfilado). |
| `[Paquete]` | Leído en el código o README del *replication package* de los autores (ver §7–§8). |
| `[Verificado]` | Reproducido numéricamente por nosotros contra cifras del paper (ver §7.2). |
| `[Supuesto]` | Decisión nuestra, pendiente de confirmar con el usuario. |
| `[Abierto]` | El paper no lo especifica; ver §7. |

Si añades información nueva, etiquétala igual. Si algo del paper no está aquí, vuelve al PDF: **no lo rellenes de memoria**.

---

## 1. Reglas de trabajo

1. **Ir despacio, una fase a la vez.** El usuario decide cuándo se pasa a la siguiente fase (§10). No implementes fases posteriores por adelantado.
2. **Replicar tal como está escrito primero**; cualquier desviación (efectos fijos, otra definición de efecto marginal, etc.) se documenta y se ejecuta *además*, no en lugar de lo replicado.
3. **Datos confidenciales** `[P p.19: "The data that has been used is confidential"]`. Nunca subir datos a servicios externos (incluidos Artifacts, gists, etc.), nunca imprimir filas individuales en logs compartidos y **nunca versionarlos**. `data/` está en `.gitignore` (añadido 2026-09-29) y contiene los datos y el *replication package* extraído. **Los commits los hace solo el usuario**: no ejecutar `git commit`, `git push` ni `git add` sin que lo pida.
4. **No fabricar datos demográficos ni resultados.** Si falta una entrada, se declara y se le pregunta al usuario qué sustituto usar.
5. **Zona horaria:** los timestamps del GPS vienen en UTC (`Z`). Convertir a `America/Santiago` (UTC−3 en noviembre) **antes** de asignar horas o días de la semana.
6. **Validación contra el paper:** los objetivos numéricos son las Tablas 4 y 5 (§6). Comparar celda a celda (signo, magnitud, estrellas) y registrar las diferencias.
7. **Al recibir datos nuevos:** perfilarlos (columnas, rangos, nulos, duplicados, ventanas temporales, cobertura) y actualizar §8 antes de usarlos.
8. Instalar paquetes solo con el OK del usuario; proponer un `requirements.txt` cuando se defina el stack.

---

## 2. Stack

- **Python** es el lenguaje de la réplica. R solo para un caso puntual y justificado (p. ej. contrastar el ZINB); no complicarlo.
- `[Datos 2026-09-29]` Entorno: Python 3.12.3. Instalados: `pandas 3.0.5`, `numpy 2.5.2`, `matplotlib 3.11.1`, `h3 4.5.0` (API v4: `h3.latlng_to_cell`, no `geo_to_h3`). **No instalados** (y previsiblemente necesarios): `statsmodels` (ZINB, OLS, errores con cluster), `scipy` (Wasserstein, tests), `geopandas`/`shapely`/`pyproj` (recortar trayectorias por hexágono, medir metros, comunas), `libpysal`+`esda` (Moran's I).
- Distancias en metros: proyectar a un CRS métrico (p. ej. WGS 84 / UTM 19S, EPSG:32719 `[Supuesto]`, a confirmar con el usuario) antes de medir longitudes.

---

## 3. Qué hace el paper en una línea

Cruza, en una grilla **hexágono H3 (res. 9) × hora**, (a) cuántos vehículos de reparto hay / cuántos metros recorren (GPS de SimpliRoute) con (b) la **composición demográfica de la población presente** en ese hexágono-hora (móviles de Entel), y regresa la exposición sobre la composición para ver qué grupos quedan más expuestos. Compara contra una versión **estática** (demografía residencial fija). `[P §1, §4]`

"Exposición" = **co-ocurrencia espacio-temporal** de personas y vehículos; **no** son concentraciones de contaminante ni dosis inhaladas `[P §4, p.7]`. El análisis es correlacional, no causal, y a nivel hexágono-hora (ecológico), no individual `[P §5.1 p.12, §6.1 p.16, §6.2 p.19]`.

---

## 4. Datos del paper

### 4.1 Población — Entel `[P §3.1, pp.4–5]`

- Entel: mayor telco de Chile, cuota nacional ≈ 33 %. Posición triangulada del dispositivo en cada interacción con la red. Reconstrucción de trayectorias: ver Basso et al. (2025) (referencia externa, no incluida).
- **Hogar del dispositivo:** *census tract* donde está más frecuentemente de noche.
- **Atributos** (del censo de ese tract, como **probabilidades**, no atributos individuales): proporción de hombres/mujeres; 6 tramos de edad: `<25, 25–34, 35–44, 45–54, 55–64, 65+`; GSE chileno: `AB, C1a, C1b, C2, C3, D, E`.
- Ingreso per cápita mensual por GSE (CLP, aprox. USD): AB 4.959.437 (5.220) · C1a 1.998.058 (2.104) · C1b 1.360.167 (1.432) · C2 949.378 (999) · C3 637.655 (671) · D 407.170 (429) · E 196.192 (206).
- **Factor de expansión por comuna c:** `EF_c = P_c / P'_c`, con `P_c` = población proyectada del censo y `P'_c` = nº de usuarios Entel cuya comuna de residencia imputada es c. Comuna de residencia = donde pasan más tiempo **entre 20:00 y 23:00 durante 3 meses**. Valores de EF por comuna: Basso et al. (2024a) (externo). Cada dispositivo queda con (i) probabilidades sociodemográficas y (ii) su peso `EF`.
- **Sin verdad-terreno** de población por hexágono-hora; solo verificaciones de plausibilidad (Fig. 1) `[P p.5]`.
- **Grilla:** H3 **resolución 9**, "≈400 m de diámetro" (vértice a vértice; arista media ≈ 201 m `[Derivado: h3 4.5.0]`), **11.144 hexágonos**.
- **Horas:** de 7:00 a 22:00 → **16 horas** (ventana fijada por Entel por eficiencia de almacenamiento). En cada hora, cada dispositivo se asigna a su **hexágono modal** (donde pasó más tiempo esa hora).
- **Período:** todos los **miércoles de marzo a junio de 2024**, sin feriados.
- **Producto:** panel hexágono-hora con (i) población total estimada = **Σ de `EF`** de los dispositivos allí y (ii) **shares demográficos** = promedio de las probabilidades de los dispositivos **ponderado por `EF`**. Luego se agrega sobre los miércoles → "miércoles típico" (§3.1 dice *averaged*; el paquete indica **mediana**, ver §7 H16).
- **Tamaño:** 11.144 × 16 = **178.304 filas**.
- **Movilidad (descriptivo, Tabla 2):** distancia de Wasserstein (Earth Mover's) entre la distribución espacial de cada grupo en la mañana (10–12 h) y la tarde (20–22 h); ranking 1 = más móvil. **No entra en los modelos.**

### 4.2 Vehículos — SimpliRoute `[P §3.2, pp.5–6; Tabla 3, p.7]`

- Plataforma de ruteo de última milla (Chile), 334 empresas (alimentos, tecnología, servicios). Cubre **todos los días de 2024 salvo julio y diciembre**; se restringe a **miércoles sin feriados** ("consistencia con los datos móviles").
- Campos por ping: identificador único de vehículo, código de cuenta (empresa), lat/lon, timestamp.
- Límites: no incluye otros proveedores logísticos ni transportistas independientes `[P p.18]`.

**Tabla 3 (verbatim):**

| Descripción | Valor |
|---|---|
| Vehículos de reparto por día (promedio) | 3.345,74 |
| Empresas por día (promedio) | 334,23 |
| Puntos GPS por día (promedio) | 5.023.366,51 |
| Período de análisis | 41 miércoles (2024) |
| Distancia por vehículo por día (km) | 100,88 |
| Puntos GPS por vehículo por día | 802,29 |
| Tiempo entre pings consecutivos (percentil 90) | 5,45 min |

### 4.3 Estadística descriptiva de la población flotante — Tabla 2 `[P p.7, verbatim]`

Unidad: hexágono-hora. `Mean` = media del conteo poblacional de ese grupo; `Mean (%)`/`Std (%)` = share medio y desv. estándar.

| Variable | Mean | Std | Mean (%) | Std (%) | Wasserstein | Rank |
|---|---:|---:|---:|---:|---:|---:|
| Población promedio | 472,78 | 938,57 | | | | |
| Hombre | 232,93 | 464,99 | 49,3 | 3,5 | 1,02357 | 1 |
| Mujer | 239,83 | 474,95 | 50,7 | 3,5 | 0,97643 | 2 |
| <25 | 81,74 | 147,03 | 17,3 | 5 | 0,92013 | 5 |
| 25–34 | 85,8 | 193,85 | 18,1 | 3,9 | 0,99849 | 4 |
| 35–44 | 91,61 | 195,21 | 19,4 | 3,4 | 1,00151 | 3 |
| 45–54 | 87,63 | 177,84 | 18,5 | 3,4 | 1,12169 | 1 |
| 55–64 | 70,7 | 140,49 | 15 | 3 | 1,05467 | 2 |
| 65+ | 55,28 | 103,62 | 11,7 | 3,6 | 0,72591 | 6 |
| AB | 16,46 | 64,95 | 3,5 | 9,7 | 1,33703 | 1 |
| C1a | 42,03 | 184,98 | 8,9 | 15,3 | 0,60407 | 6 |
| C1b | 34,86 | 169,69 | 7,4 | 11,1 | 0,50839 | 7 |
| C2 | 73,6 | 240,68 | 15,6 | 15,8 | 1 | 4 |
| C3 | 133,12 | 283,81 | 28,2 | 19,4 | 1,06643 | 3 |
| D | 133,6 | 264,62 | 28,3 | 20,7 | 0,96796 | 5 |
| E | 39,11 | 105,79 | 8,3 | 11,3 | 1,15682 | 2 |

Nota `[Derivado]`: las medias por sexo suman 472,76 y por GSE 472,78, coherente con la población media. Los Wasserstein no tienen normalización documentada (C2 = 1 exacto; Hombre + Mujer = 2) → §7.3-D10.

---

## 5. Metodología

### 5.1 Variables dependientes `[P §4.1, pp.8–10]`

**Conteo de vehículos `Y_hi`** (por día): nº de vehículos **distintos** con **al menos un ping** dentro del hexágono h durante la hora i. Se suma sobre vehículos. Luego, **mediana entre días** → `Ỹ_hi` (variable dependiente del ZINB). Fig. 4: ejemplo con 3 vehículos y 4 hexágonos (`Y_b=0, Y_a=1, Y_c=2, Y_d=3`).

**Distancia `K_hi`** (por día): suma de **metros recorridos estrictamente dentro** del hexágono h en la hora i (Fig. 5: longitud de cada tramo de ruta dentro de cada hexágono; un vehículo que cruza hexágonos aporta a cada uno solo la parte interior). Luego **mediana entre días** → `K̃_hi` (variable dependiente de los OLS).

Motivos de la mediana: mitigar eventos especiales/anomalías de miércoles concretos y coherencia con el tratamiento de la población `[P p.8]`. Motivo de usar distancia: los factores de emisión estándar son por km. Motivo de usar también el conteo: las emisiones crecen más que linealmente con la densidad vehicular (congestión, stop-and-go) `[P p.8]`.

### 5.2 Regresores `D_hi` `[P §4.2, p.10]`

Vector de **shares** (probabilidades, escala [0,1]) del hexágono-hora, de §4.1. Dentro de cada dimensión se omite una categoría de referencia para evitar colinealidad perfecta: **Mujer, GSE AB, 65+**. Quedan **11 regresores**:

- `Male` (share de hombres);
- edad: `Under25, 25–34, 35–44, 45–54, 55–64`;
- GSE: `C1a, C1b, C2, C3, D+E`. **D y E se combinan en los modelos** (share D+E) aunque en la Tabla 2 van separados `[P p.12: "even when combining groups D and E in the models"; Tablas 4–5]`.

Interpretación: un coeficiente es el cambio esperado al subir el share de ese grupo, compensado por una caída equivalente en la categoría de referencia. Ejemplo del paper: pasar la probabilidad de C1a de 0 a 1 se asocia a "2 a 3 encuentros adicionales de vehículos en un miércoles típico" `[P p.12]`. **No hay** población total, efectos fijos ni otros controles en las ecuaciones (3) y (5) — ver §7 H12 (una variante del código añade efectos fijos de comuna solo a los OLS).

### 5.3 Modelo de conteo: ZINB `[P §4.2.1, pp.10–11; Apéndice A, pp.19–20]`

- Poisson descartado: test de Cameron–Trivedi, parámetro de dispersión **7,73** (≫1), p < 0,001. Además **≈30 %** de los hexágono-hora tienen cero vehículos.
- Ec. (1), con `π` **constante** (misma para todos los hexágono-hora):
  ```
  P(Ỹ=0)   = π + (1−π) f_NB(0; μ_hi, θ)
  P(Ỹ=y>0) = (1−π) f_NB(y; μ_hi, θ)
  ```
- Ec. (2), NB en parametrización (μ, θ) (Claim 1, Apéndice):
  ```
  f_NB(y; μ, θ) = Γ(y+θ) / (Γ(θ)·Γ(y+1)) · (θ/(μ+θ))^θ · (μ/(μ+θ))^y
  ```
  (NB2: Var = μ + μ²/θ `[Derivado, resultado estándar]`).
- Ec. (3): `log(μ_hi) = β0 + β' D_hi`.
- `E[Ỹ_hi] = (1−π) μ_hi` (Claim 2).
- **Efecto marginal, Ec. (4):** `∂E[Ỹ_hi]/∂x_k = (1−π) · β_k · μ_hi` (Claim 2). Depende de `μ_hi`, por lo que hay que agregarlo de alguna forma → en el código se calcula distinto (§7 H10–H11).
- Interpretación de π: probabilidad de **cero estructural** (parques, zonas sin cobertura del servicio); los ceros de muestreo vienen de la NB.
- Robustez declarada (sin mostrar): con covariables en la parte de inflación, los resultados de la parte de conteo son "sustancialmente idénticos".

### 5.4 Modelos de distancia: OLS `[P §4.2.2, p.11]`

- Ec. (5): `K̃_hi = β0 + β' D_hi + ε_hi`, `ε ~ N(0, σ²)`. Ec. (6): efecto marginal = `β_k` (metros).
- **Tres especificaciones** (columnas de las Tablas 4 y 5): (i) `K̃_hi` con todas las observaciones; (ii) `K̃_hi > 0` (**en el código es un modelo de dos partes logit + OLS, no un OLS sobre positivos**, §7 H7); (iii) `log(K̃_hi)`. La corrección de ceros no aplica a variables continuas; por eso se comparan con y sin ceros. (iii) se estima solo sobre `K̃>0` y se reporta el coeficiente crudo (§7 H8).
- Las figuras 6–10 usan **ZINB (azul, eje izq.)** y **OLS con `K̃>0` (rojo, "no zero", eje der.)** `[P pie de Fig. 6, 8, 9, 10]`.

### 5.5 Correlación espacial e inferencia `[P §4.2.3, pp.11–12]`

- **Moran's I** (promedio simple a través de las horas): **0,4694** para `K̃` y **0,4756** para `Ỹ`. Matriz de pesos no especificada → §7.3-D8.
- **No se modela** la dependencia espacial: solo se corrigen los errores estándar con **clusters a nivel comuna** (**51 comunas**; Cameron & Miller 2015). Justificación y crítica del propio paper: cluster más fino (p. ej. grupos de 6 hexágonos) captura mejor derrames locales pero da menos clusters/menos fiabilidad.

### 5.6 Enfoque estático `[P §5.2, pp.14–16]`

Mismo conjunto de datos y mismos modelos, con **una diferencia**: la composición demográfica de cada hexágono **no varía durante el día** (perspectiva residencial, típica de estudios de justicia ambiental). Es la línea base para medir el sesgo por ignorar la movilidad. **No se explica cómo se construyen los shares estáticos** → el paquete trae `datosxhexagono.csv` (§8.1), sin documentar su construcción.

### 5.7 Conversión a gramos de contaminante (Fig. 7) `[P p.13]`

Usa factores de emisión de NOx y PM **por metro** de un vehículo de reparto no eléctrico "de contaminación promedio" (EMEP/EEA, *Agency 2024*, capítulo 1.A.3.b.i-iv Road transport 2024). Resultado citado: SEG C1b vs AB → **+70,8 g NOx y +13,2 g PM al mes**, "60,6 % de aumento".
`[Derivado]` Todas las barras de la Fig. 7 corresponden a un factor casi constante contra el efecto marginal OLS `K̃>0` de la Tabla 4: **≈0,182 g NOx** y **≈0,034 g PM por metro marginal** (p. ej. 70,8/388,3212 = 0,1823; 13,2/388,3212 = 0,0340). El multiplicador a "mes" y los factores exactos no están documentados → §7.3-D10.

---

## 6. Resultados de referencia (objetivos de validación)

Valores de las Tablas 4 y 5, verificados contra la capa de texto del PDF. Son **efectos marginales** (no coeficientes, para el ZINB). Estrellas: `***` p<0,001, `**` p<0,01, `*` p<0,05, `.` p<0,1. **Las tablas no reportan N, θ, π ni errores estándar** → solo se puede validar signo, magnitud y estrellas.

### Tabla 4 — dinámico (demografía por hora) `[P p.12]`

| Variable | ZINB `Ỹ` | OLS `K̃` | OLS `K̃>0` | OLS `log K̃` |
|---|---:|---:|---:|---:|
| Male | 3,5569*** | 90,6926* | 260,836*** | 0,2429*** |
| 65+ (ref.) | 0 | 0 | 0 | 0 |
| Under 25 | −3,6291* | −444,5891*** | −550,3141*** | −1,529*** |
| 25–34 | 11,0087*** | 872,9379*** | 1446,0004*** | 1,6696*** |
| 35–44 | −3,0092** | −117,1339* | −179,1028*** | −0,8142*** |
| 45–54 | −1,5369 | −113,5191* | −141,3634 | −0,6763 |
| 55–64 | −0,313 | 50,1969* | 12,0917 | −0,4282* |
| AB (ref.) | 0 | 0 | 0 | 0 |
| C1a | 2,8017*** | 354,4696*** | 326,1956*** | 0,4232*** |
| C1b | 2,6735 | 439,9621* | 388,3212*** | 0,6061*** |
| C2 | 2,6614** | 268,6009** | 216,5829*** | 0,159 |
| C3 | 2,2027*** | 166,4846*** | 124,7486*** | −0,0038 |
| D+E | 0,4997 | −18,3538 | −88,3825** | −0,2337*** |

### Tabla 5 — estático `[P p.15]`

| Variable | ZINB `Ỹ` | OLS `K̃` | OLS `K̃>0` | OLS `log K̃` |
|---|---:|---:|---:|---:|
| Male | −3,0814*** | −1288,2834* | −1395,7866** | −2,0981 |
| 65+ (ref.) | 0 | 0 | 0 | 0 |
| Under 25 | −8,9981*** | −1531,6851*** | −1432,6091*** | −2,6208*** |
| 25–34 | 5,6151*** | 2350,2517** | 1953,129*** | 2,5876*** |
| 35–44 | −10,2721*** | −338,3899 | −695,0703** | −0,427 |
| 45–54 | −11,4694*** | 555,7175 | −49,7176 | 0,9072 |
| 55–64 | −10,1445*** | −1156,8464* | −1315,9431** | −1,4989 |
| AB (ref.) | 0 | 0 | 0 | 0 |
| C1a | 6,7695*** | 1340,5565 | 1542,785** | 1,2605 |
| C1b | −14,2813*** | −1015,3285 | −896,4961 | 2,3998 |
| C2 | 5,5297*** | 395,2089 | 424,9602 | −1,3379* |
| C3 | 7,2721*** | 841,4145 | 1215,0827** | 1,7016 |
| D+E | −5,1201*** | −289,7367 | −283,3003 | 0,0013 |

### Mensajes principales del paper (para reconocer si la réplica reproduce lo esencial) `[P §5–6, pp.12–17]`

1. **U invertida por GSE** en el modelo dinámico: la clase media (C1a, C1b, C2, C3) queda más expuesta que AB y que D+E. Los autores destacan C1b como el más expuesto (+70,8 g NOx, +13,2 g PM al mes vs AB; "60,6 %").
2. **Edad:** pico en 25–34; <25 y 65+ poco expuestos.
3. **Sexo:** hombres ≈ 24 % más expuestos (0,2429 del log-modelo) en el dinámico; **el signo se invierte** en el estático (−3,08).
4. **Estático vs dinámico:** C1b pasa de "más expuesto" a "menos expuesto" (ZINB: +2,67 → −14,28); se atribuye a que C1b es de baja movilidad pero está localizada en las zonas de más actividad de reparto durante el día.
5. Los autores leen los coeficientes del modelo log como porcentajes (0,4232 → "≈42,3 %"; 0,6061 → "60,6 %"; 0,2429 → "≈24 %"), es decir `β × 100`, no `exp(β)−1`.

`[Derivado]` Matiz sobre (1): "C1b es el más expuesto" vale para **distancia** (máximo en `K̃>0`: 388,32; en `K̃`: 439,96) pero en el **conteo ZINB** el máximo es **C1a (2,8017)** frente a C1b (2,6735, no significativo). Tenerlo presente al comparar la réplica.

---

## 7. Paper ↔ código de los autores: hallazgos y ambigüedades

Fuente: el *replication package* de los autores (`data/TRD_replication_share.zip`, ver §8). Se leyó todo su código y README (`[Paquete]`) y se contrastó numéricamente con los datos (`[Verificado]`, calculado por nosotros con numpy/pandas). **Donde el paper y el código difieren, el código es lo que produjo las tablas.** Para replicar "el paper" hay que replicar el código; para hacerlo bien hay que decidir aparte qué corregimos.

### 7.1 Hallazgos verificados

| ID | Tema | Hallazgo |
|---|---|---|
| H1 | **Hora = UTC** (crítico) | `[Paquete]` `03_gps_hexagon_count.R` hace `hour(timestamp)` sin convertir zona, y `01_extract_wednesday.R` define el miércoles con `as.Date(timestamp)` (fecha UTC). `[Verificado]` Al comparar `hexagon_count_27-11-2024_cleaned.csv` con nuestro GPS crudo del mismo día: con etiqueta de hora **UTC** coinciden el 60,7 % de los hexágono-hora (correlación 0,927; diferencia de totales por ser nuestro CSV un subconjunto filtrado); con hora **local** solo el 8,1 % (corr. 0,631). Luego la columna `hour` de los conteos son horas UTC (0–23), y se fusiona por `hour` con las horas 7–22 de la población (`hora`), que se presume local `[Abierto]`. Chile es UTC−3 (aprox. sept–abr) y UTC−4 el resto: desfase de 3–4 h y un "miércoles" que en hora local va de martes ~20:00 a miércoles ~20:00. **Decisión pendiente del usuario** (ver §7.3-D1). |
| H2 | **Mediana solo sobre días presentes** | `[Paquete]` `04_modeling_wedenesday.R`: los archivos diarios `hexagon_count_*` solo contienen hexágono-horas con ≥1 vehículo; `median(vehicles)` se calcula sobre esos días y `count_wednesdays = .N`. Los días sin vehículos **no entran como 0**. `[Verificado]` Recalculado desde los 42 archivos diarios reproduce el 100 % de `median_vehicles` y `count_wednesdays` de `00_data/hexagon_model_median_wednesdays_RM.csv`. Un hexágono-hora con ≥1 vehículo en un solo miércoles queda con esa cifra como "mediana" (sesgo al alza respecto de la mediana sobre los 42 días). Mismo criterio para distancia y tiempo. |
| H3 | **Nº de miércoles** | 42 archivos diarios `[Verificado]` (2024-01-03 … 2024-11-27), frente a **41** del paper (Tabla 3) y **44** del README del paquete. Incluye el 2024-05-01 (feriado; archivo mucho más pequeño); el 2024-09-18 (feriado) sí está excluido. Sin julio ni diciembre, coherente con el paper. |
| H4 | **Distancia ≠ Fig. 5** | `[Paquete]` `03_alternative_metrics.R` **no recorta trayectorias por hexágono**. Calcula haversine entre pings consecutivos del mismo `owner_id` y **conserva solo pares cuyo ping previo y actual están en el mismo hexágono y la misma hora**; los tramos que cruzan hexágono u hora se **descartan**. Además elimina pares con `time_diff = 0` y con velocidad > 100 km/h (33,33 m/s). No hay tope de brecha temporal. Suma por (hex, hora, vehículo) y luego por (hex, hora). `median_time` = Σ de segundos. |
| H5 | **Limpieza del GPS** | `[Paquete]` `cleaning_gps.R`: se eliminan camiones (owner_id) con distancia total del día < 1 km o > 2400 km (haversine de pings consecutivos, incluyendo duplicados); caja lat ∈ [−33,7; −33,2], lon ∈ [−71,0; −70,5]. El H3 res. 9 se asigna con `h3jsr::point_to_cell`. |
| H6 | **Copias distintas del dataset** | `[Verificado]` `00_out/data_base/hexagon_model_*` **no** son copia de `00_data/hexagon_model_*` (contra lo que dice el README): 52,1 % de ceros y `count_wednesdays` medio 0,79, frente a 29,56 % y 17,55. **Usar solo `00_data/`** (29,56 % de ceros ≈ "30 %" del paper; reproducible desde los conteos). |
| H7 | **Columna "OLS K̃>0" = modelo de dos partes** | `[Paquete]` en todos los `summary_results*.R` la columna "OLS (no zero)" (usada en las Figs. 6–10) es el AME de un modelo **logit + OLS**, no un OLS sobre positivos. `[Verificado]` Con esa fórmula (ver §8.3) reproducimos la columna 3 de las Tablas 4 y 5 con diferencia máxima **0,0** en las 22 celdas. Un OLS simple sobre `K̃>0` da otras cifras (p. ej. C1b: 474,78 en vez de 388,32). |
| H8 | **Columnas OLS `K̃` y `log K̃`** | `[Verificado]` Reproducidas exactamente (Tablas 4 y 5, 22 celdas por columna): OLS de `median_distance` sobre las 11 variables con **todas** las filas (efecto marginal = coeficiente), y OLS de `log(median_distance)` sobre las filas con distancia > 0, **coeficiente crudo**. En el estático, los shares se toman de `datosxhexagono.csv` (GSE ÷ 100; `gse_de = gse_d + gse_e`) fusionados por `hex`. |
| H9 | **Script del `log` inconsistente** | `[Paquete]` los `summary_results*.R` **dinámicos** calculan el efecto del log como `coef × media(distancia>0)`, no el coeficiente crudo que aparece en la Tabla 4; los **estáticos** (`*_static*.R`) sí usan el coeficiente crudo (`log(distance)`). El paquete no trae el script exacto que generó la columna log de la Tabla 4. |
| H10 | **AME del ZINB (probable doble conteo de (1−π))** — *no verificado numéricamente* | `[Paquete]` `AME_k = β_k · mean(predict(type="response")) · (1−π)`. En `pscl::zeroinfl` y `glmmTMB`, `predict(type="response")` ya es `E[Y] = (1−π)·μ`, luego el resultado sería `β_k·(1−π)²·mean(μ)`, no `(1−π)·β_k·μ_hi` como la Ec. (4). Pendiente de comprobar al estimar el ZINB en Python (¿coincide con la columna 1 de las Tablas 4/5?). |
| H11 | **Variantes del ZINB** | `[Paquete]` Principal: `pscl::zeroinfl(vehicles ~ X \| 1, dist="negbin")` con `vehicles = round(median_vehicles)` (R redondea a par: 0,5→0; 1,5→2) y SE de `sandwich::vcovCL(cluster = comuna)` (bloque de conteo); `p = 2(1−Φ(|β/se|))` normal. Variante `summary_results.R`: `glmmTMB(..., family=nbinom2, ziformula=~1)` **sin** cluster. Variantes con covariables en la inflación (`*_cov.R`, `zinb_marginal_effects_with_covariates.R`) usan otra fórmula de AME. |
| H12 | **SE en los OLS** | `[Paquete]` `fixest::feols(..., cluster = ~comuna)`; los p-valores se recalculan con la normal (no t). El logit del modelo de dos partes no lleva cluster; el SE del AME de dos partes es una aproximación burda (suma en cuadratura). `summary_results_fe.R` añade efectos fijos de comuna (`\| comuna`) solo a los OLS: probable origen de la frase "controla por ubicación" de §6.2 del paper. **No consta** cuál variante generó las estrellas del paper. |
| H13 | **Observaciones con población 0** | `[Verificado]` 1.427 filas (0,8 %) tienen `poblacion_flotante = 0` y **todos los shares = 0** (no NaN); entran igual a las regresiones (198 tienen `median_vehicles > 0`). Los shares suman como máximo 1,0066. |
| H14 | **Hexágonos fuera de la grilla** | `[Verificado]` Los conteos tienen 16.400 hexágonos distintos con ≥1 ping, de los que solo 11.144 están en el panel; los 5.256 restantes se pierden en el `merge` (`all.x = TRUE` sobre el panel). Hexágono-horas del panel sin vehículos → 0. |
| H15 | **Tabla 2 reproducida** | `[Verificado]` `miercoles_rm.csv` reproduce exactamente Mean y Std de la Tabla 2 (población 472,78 / 938,57; hombres 232,93 / 464,99; …). `Mean (%)` = media del conteo del grupo ÷ población media; `Std (%)` = **desviación estándar de los shares ponderada por población** (filas con pob > 0). |
| H16 | **Período de la población** | `[Paquete]` `00_data/README.md`: "mediana de miércoles del semestre", cita la *Nota metodológica – Población flotante – S2 2024 V2* del proveedor (no incluida). El paper dice marzo–junio 2024. Además, la población es **mediana** (no promedio, cf. §3.1 del paper). |
| H17 | **Contexto del proyecto** | `[Paquete]` README raíz: "Para ruido, la idea sería reemplazar [`median_vehicles`] por tu métrica de ruido y reutilizar el mismo pipeline". El objetivo posterior del usuario (proyecto *Noise Map*) es aplicar este pipeline a ruido. |
| H18 | **Conversión UTC → hora chilena: factible y validada (solo conteos)** | `[Verificado 2026-09-29]` (a) La base de zonas horarias da los cambios de 2024 correctos (−3 el 05‑abr, −4 el 08‑abr, −4 el 07‑sep, −3 el 09‑sep) y el desfase es constante dentro de cada archivo diario. De los 42 miércoles UTC, 17 caen en UTC−4 (2024‑04‑10 … 2024‑09‑04) y 25 en UTC−3. (b) De 4.574.852 filas de conteos, 4.192.449 caen en miércoles local; el resto es martes por la tarde/noche local. (c) **Validación:** con las etiquetas de los autores pasadas a hora local, el 27‑11 coincide con el GPS crudo (hora local) en el 60,7 % de los hexágono‑hora (corr. 0,927), idéntico a la comparación en UTC ⇒ la conversión es consistente (la diferencia restante se debe a que nuestro CSV es un subconjunto). |
| H19 | **Cobertura de la versión en hora local** | `[Verificado]` Cada archivo diario cubre el día UTC, luego el miércoles local solo queda completo hasta la hora local 19 (UTC−4) o 20 (UTC−3). Días que aportan por hora local: **7–19: 42 de 42; 20: 25; 21–22: 0** (esas horas están en el archivo UTC del jueves, que no tenemos). La **distancia/tiempo no es convertible**: solo hay medianas ya mezcladas (desfases −3/−4) y no vienen los archivos diarios `alternative_metrics/`. Efecto de la conversión sobre `median_vehicles` (horas 7–19): correlación 0,747 con la versión publicada; ceros 31,10 % (etiqueta UTC) → 23,40 % (local). Perfil de Σ`median_vehicles` por hora: con etiqueta UTC el máximo está en 15–17 (~36.800); en local, en 10–15 (~37.000) y baja a ~12.100 a las 20. |
| H20 | **La hora de la población parece local (inferencia)** | `[Verificado]` como patrón, no como prueba: en comunas de destino laboral (Las Condes, Providencia, Santiago) la población relativa parte en 0,61–0,77 a las 7, sube a ~1,1–1,2 entre las 9 y las 16 y cae a 0,61–0,80 hacia las 21–22; en comunas dormitorio (Puente Alto, La Pintana, Pudahuel, Maipú) es baja por la mañana (0,62–0,77 a las 7) y sube por la tarde/noche (~1,15–1,2). Es la firma del desplazamiento en hora local. **Confirmar** con la nota del proveedor o con los autores; si la población también estuviera en UTC, no habría desfase. |

### 7.2 Estado de la validación numérica contra el paper

| Objetivo | Estado |
|---|---|
| Tabla 2 (Mean, Std, Mean %, Std %) | ✅ exacta (H15). Wasserstein/ranks: no reproducidos. |
| Tabla 4 — cols. OLS `K̃`, "OLS `K̃>0`" (dos partes), `log K̃` (estimaciones puntuales) | ✅ exactas (H7, H8) |
| Tabla 5 — mismas 3 columnas (estático) | ✅ exactas |
| Tablas 4 y 5 — col. ZINB | ⏳ pendiente (requiere estimar ZINB; ver H10) |
| Estrellas de significancia (todas las tablas) | ⏳ pendiente (requiere SE con cluster por comuna, H11–H12) |
| Moran's I (0,4694 / 0,4756), Cameron–Trivedi (7,73), π | ⏳ pendiente |
| Figs. 1, 2, 6–10 | ⏳ pendiente |
| Conversión UTC → hora local (solo conteos) | ✅ validada contra el GPS crudo del 27‑11 (H18); pendiente aplicarla al modelo. |

### 7.3 Decisiones y ambigüedades abiertas

| ID | Pri. | Tema | Detalle / propuesta |
|---|:-:|---|---|
| D1 | **A** | Hora UTC vs local (H1, H18–H20) | **Acordado con el usuario (2026-09-29):** secuencia (1) réplica **tal cual el paquete** (hora UTC, miércoles UTC) para reproducir las tablas; (2) versión **corregida a hora local** `America/Santiago` como **sensibilidad**, solo conteos y solo horas locales **7–19** (las únicas completas); para aislar el efecto de la etiqueta horaria, compararla contra la versión publicada **restringida a las mismas horas 7–19**, no contra el paper completo; (3) **solicitar a los autores**, en un solo mensaje: GPS crudo o conteos/distancias diarios por fecha local, confirmación de la base horaria de la población y la *Nota metodológica – Población flotante – S2 2024 V2*. Para la extensión a ruido: fijar hora local desde el inicio (convertir a `America/Santiago` antes de agregar por hora y por día). |
| D2 | **A** | ZINB y AME (H10, H11) | Estimar el ZINB en Python y comprobar si se reproduce la col. ZINB usando la fórmula del código y/o la Ec. (4) del paper. Decidir cuál queda como "réplica" y cuál como "corregida". |
| D3 | **A** | Qué variante generó las estrellas | H12: sin cluster (`summary_results.R`), con cluster comuna (`*_cluster.R`), o FE comuna. Se decide al comparar estrellas con las Tablas 4/5. |
| D4 | M | Nº de miércoles (H3) | ¿Réplica con los 42 archivos (incluye 2024-05-01) o excluir el feriado (→ 41, como el paper)? Los datos entregados ya contienen la mediana de 42. |
| D5 | M | Período de la población (H16) | Paper: mar–jun 2024; nota del proveedor: S2 2024. Solo resoluble con el proveedor. |
| D6 | M | Universo y ceros (H13, H14) | Mantener las 1.427 filas con población 0 y shares 0 (como el código) o excluirlas (sensibilidad). |
| D7 | M | Distancia (H4) | El paper describe recorte por hexágono (Fig. 5); el código descarta tramos que cruzan hexágono/hora. Para ruido u otras métricas habrá que decidir cuál usar. Sin los GPS crudos ni los `alternative_metrics/` diarios no podemos reconstruirla; solo disponemos de las medianas finales. |
| D8 | M | Moran / comunas | Matriz de pesos de Moran no especificada (¿vecindad H3 de anillo 1?). La comuna de cada hexágono **ya viene en el panel** (`comuna`, `codigo_comuna`, 51 comunas). |
| D9 | B | Interpretación del `log` | Los autores leen β×100 como % (para 0,6061, `exp(β)−1 ≈ 83 %`). Replicar su cifra y reportar la exacta. |
| D10 | B | Wasserstein, gramos NOx/PM | Método de Wasserstein y factores de emisión/multiplicador mensual sin documentar (§5.7 y Tabla 2). Baja prioridad. |
| D11 | B | Validación | Las tablas no reportan N, θ, π ni SE: solo se compara signo/magnitud/estrellas (más lo que reporte el ajuste propio). |

Ambigüedades del borrador anterior **resueltas** por el código: A1 (efectos fijos: solo comuna-FE en una variante de OLS, H12), A2/A3 (definición del AME y software, H10–H11), A4 (`log` solo sobre `K̃>0`, H8), A7 (mediana, H16), A9 (comuna incluida en el panel), A11 (`datosxhexagono.csv`, ver §8), A15 (`round()` de R, H11).

---

## 8. Datos disponibles en el repositorio

### 8.1 Replication package — `data/TRD_replication_share.zip` → `data/replication_package/`

Enviado por los autores. Extraído (2026-09-29) a `data/replication_package/` (ignorado por git). 77 entradas, 423,8 MB. README dirigido al usuario.

**Incluido:**

| Archivo | Contenido `[Verificado 2026-09-29]` |
|---|---|
| `00_data/miercoles_rm.csv` | 178.304 × 24. Panel población flotante + demografía por (`h3_9`, `hora` 7–22). 11.144 hex, 51 comunas, sin nulos, `es_urbano` = 1, `dia_semana` = miércoles. Reproduce la Tabla 2. Columnas: `OID_, h3_9, codigo_comuna, comuna, es_urbano, id_dia_semana, dia_semana, hora, poblacion_flotante, genero_{masc,fem}, gse_{ab,c1a,c1b,c2,c3,d,e}, edad_{menor_25,25_34,35_44,45_54,55_64,mayor_65}` (shares en [0,1]). |
| `00_data/datosxhexagono.csv` | 11.144 × 17. Demografía **estática** por hexágono (mismo conjunto de hex). `gse_*` en **porcentaje (0–100)**, el resto en proporción; `poblacion` media 664. Composición muy distinta a la horaria (p. ej. `<25` = 35,6 % frente a 19,5 %). El README no dice cómo se construyó (¿residencial nocturno?) `[Abierto]`. |
| `00_data/hexagon_model_median_wednesdays_RM.csv` | **Dataset del paper para conteo.** 178.304 × 28. Panel + `median_vehicles` (media 2,222; sd 4,296; máx 77; 29,56 % ceros; 5.810 medianas x,5) + `count_wednesdays` (máx 42). Índices `hex`, `hour`. |
| `00_data/hexagon_model_median_wednesday_alternative_metrics_RM.csv` | **Dataset del paper para distancia.** 178.304 × 29. Panel + `median_distance` (media 329,7 m; sd 553,8; 32,79 % ceros; 119.837 positivos con media 490,5) + `median_time` (32,43 % ceros) + `count_wednesdays`. 5.762 hex-horas con vehículos pero distancia 0. |
| `00_out/hexagon_count/hexagon_count_DD-MM-2024_cleaned.csv` | 42 archivos (miércoles 2024-01-03 … 2024-11-27). Columnas `hex, hour (0–23, UTC), vehicles`. Insumo del paso 04 (permite rehacer `median_vehicles`). 16.400 hex distintos en total. |
| `01_building_data/`, `02_estimation/`, `03_heatmaps/` | Código R original + READMEs (rutas `D:/transport/replication_package/...`; ver §7). |

**No incluido:** GPS crudo (`gps_all_months/`, ~52 GB, "restricciones de uso"), archivos diarios `alternative_metrics/` (distancia/tiempo por día), datos crudos de Entel, la *Nota metodológica – Población flotante – S2 2024 V2*. **`00_out/data_base/*` no es fiable** (H6).

**Consecuencia:** desde el paquete se puede reproducir todo lo que sigue al paso 04 para conteos (medianas) y toda la estimación; **no** se puede reconstruir la distancia diaria ni rehacer horas locales sin los GPS crudos.

### 8.2 GPS de un día — `data/gps-27-11-2024 - filtrado zona urbana (2).csv` `[Datos, perfilado 2026-09-29]`

- 140,9 MB; 1.843.525 filas; `account_id, latitude, longitude, owner_id, timestamp, timestamp_act` (idénticos); UTC (`...Z`); sin nulos.
- Miércoles **2024-11-27**; ventana `03:00:00Z` del 27 → `02:59:59Z` del 28 = día local completo (UTC−3). 2.600 `owner_id` (probable vehículo `[Supuesto]`), 308 `account_id`, 2 `owner_id` en más de una cuenta. Caja lat [−33,65259; −33,312828], lon [−70,84297; −70,46235]. 114.154 duplicados exactos (6,2 %).
- Ritmo de pings por `owner_id`: mediana ≈ 10 s, p90 ≈ 1,0 min (paper: p90 = 5,45 min), máx ≈ 1385 min.
- Es un **subconjunto** más pequeño y filtrado que el día equivalente de los autores (`hexagon_count_27-11-2024_cleaned.csv`: 502.621 vehículo-hex-hora frente a nuestros ~434.000). Sirve para contrastar convenciones (H1), no para reproducir cifras.

### 8.3 Recetas verificadas (reproducen las Tablas 4 y 5 al 4.º decimal)

Regresores `X` (11): `genero_masc, gse_c1a, gse_c1b, gse_c2, gse_c3, gse_de (= gse_d + gse_e), edad_menor_25, edad_25_34, edad_35_44, edad_45_54, edad_55_64`; referencias: mujer, AB, 65+. Todas las filas del panel (178.304). Estático: `X` reemplazado por `datosxhexagono.csv` (merge por `hex`; `gse_* / 100`).

1. **OLS `K̃`** (col. 2): `median_distance ~ 1 + X` (todas las filas); ME = β.
2. **OLS `log K̃`** (col. 4): `log(median_distance) ~ 1 + X` solo con `median_distance > 0`; se reporta β crudo.
3. **"OLS `K̃>0`"** (col. 3, modelo de dos partes): (a) logit de `1[K̃>0]` sobre `X` (todas las filas) → `pr = mean(p̂)`; (b) OLS de `K̃` sobre `X` con `K̃>0` → `m = mean(ŷ)` sobre esas filas; (c) `AME_k = pr(1−pr)·β^logit_k·m + β^OLS_k·pr`. Valores: `pr = 0,6721`, `m = 490,52` (idénticos en dinámico y estático).
4. **Tabla 2:** `Mean` = media de (share × población) sobre todas las filas; `Mean (%)` = Mean ÷ 472,78; `Std (%)` = desv. estándar ponderada por población de los shares.
5. **ZINB (pendiente de verificar):** ver H10–H11.

### 8.4 Entradas que aún faltan

- GPS crudo o, al menos, distancias diarias por hexágono-hora si se quiere rehacer/alterar la construcción (p. ej. hora local, recorte real por hexágono, o una métrica de ruido).
- **Solicitud pendiente a los autores (D1):** GPS crudo o conteos/distancias diarios por fecha local; confirmación de la base horaria de la población; nota del proveedor.
- Nota metodológica del proveedor de población (definición de `hora`, período, cómo se hizo la demografía estática).
- Entorno: faltan en Python `statsmodels`, `scipy`, `geopandas`/`shapely`/`pyproj`, `esda`/`libpysal`; R 4.6.1 está instalado pero solo con `MASS` (faltan `pscl`, `glmmTMB`, `fixest`, `sandwich`, etc.). Instalar solo con el OK del usuario.

---

## 9. Glosario y notación (paper ↔ código)

| Paper | Significado | Sugerencia de nombre |
|---|---|---|
| `h ∈ H` | hexágono H3 res. 9 | `h3_cell` |
| `i ∈ I` | hora local (7…22) | `hour` |
| día | miércoles de la muestra | `date` |
| `Y_hi` | nº de vehículos distintos con ≥1 ping, por día | `veh_count_day` |
| `Ỹ_hi` | mediana entre días de `Y_hi` (dep. del ZINB) | `veh_count` |
| `K_hi` | metros recorridos dentro del hexágono, por día | `dist_m_day` |
| `K̃_hi` | mediana entre días de `K_hi` (dep. de los OLS) | `dist_m` |
| `D_hi` | vector de shares demográficos | `share_*` |
| `EF_c` | factor de expansión de la comuna c | `expansion_factor` |
| `μ_hi, θ, π` | media NB, dispersión NB, prob. de cero estructural | — |
| SEG / GSE | grupo socioeconómico AB, C1a, C1b, C2, C3, D, E | `seg_*` |
| columnas del paquete | `hex`/`h3_9` (H3), `hour`/`hora`, `poblacion_flotante`, `genero_*`, `edad_*`, `gse_*`, `median_vehicles` (=`Ỹ`), `median_distance` (=`K̃`), `median_time`, `count_wednesdays`, `comuna` | ver §8.1 |

---

## 10. Plan por fases (tentativo — el usuario decide el avance)

- **Fase 0 — Comprensión del paper:** ✅ (2026-09-29).
- **Fase 1 — AGENTS.md:** ✅ (verificado contra la capa de texto del PDF y contra el replication package).
- **Fase 2 — Análisis del paquete y datos:** ✅ (§7–§8). Tabla 2 y las 3 columnas OLS de Tablas 4–5 reproducidas al 4.º decimal; conversión horaria validada (H18).
- **Fase 3 — Réplica "tal cual el paquete" (hora UTC): ZINB.** Estimar el ZINB en Python y reproducir la col. ZINB de Tablas 4–5; cerrar D2 (fórmula del AME) y D3 (variante de SE/estrellas). ⏳ **Requiere instalar `statsmodels`/`scipy`: pendiente del OK explícito del usuario.**
- **Fase 4 — Inferencia:** SE con cluster por comuna, estrellas, Moran's I, Cameron–Trivedi, π.
- **Fase 5 — Sensibilidad en hora local (D1, punto 2):** solo conteos, horas locales 7–19; comparar contra la versión publicada restringida a las mismas horas.
- **Fase 6 — Solicitud a los autores (D1, punto 3):** en paralelo desde ya; no bloquea las fases 3–5.
- **Fase 7 — Figuras:** Figs. 1, 2, 6–10 (y 7 si hay factores de emisión).
- **Fase 8 — Extensión a ruido** (objetivo posterior, §7 H17): reemplazar `median_vehicles` por la métrica de ruido reutilizando el pipeline, con hora local desde el inicio.

---

## 11. Referencias externas que el paper delega

- Basso et al. (2024a), *Transp. Res. Part A* 186, 104149 — valores de `EF_c` por comuna.
- Basso et al. (2025), *Sci. Rep.* 15(1), 22150 — reconstrucción de trayectorias de Entel.
- Basso et al. (2024b), *J. Transp. Geogr.* 116, 103854 — SimpliRoute / paradas de reparto.
- European Environment Agency (2024), EMEP/EEA *Road transport 1.A.3.b.i-iv* — factores de emisión (NOx, PM).
- Cameron & Trivedi (test de sobredispersión); Cameron & Miller (2015), *J. Human Resour.* 50(2) — SE con cluster; Winkelmann (2008), *Econometric Analysis of Count Data* — ZINB.
- Moran (1950), *Biometrika* 37 — I de Moran.
