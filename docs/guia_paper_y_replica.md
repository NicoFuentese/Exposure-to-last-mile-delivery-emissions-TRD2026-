# Guía del paper y de la réplica: modelos, tablas, figuras y diferencias

Una guía estándar para **entender y explicar** el paper de Basso et al. (2026) y nuestra réplica: qué hace el paper, cómo funcionan sus modelos, qué dicen sus tablas y figuras, qué significan las estrellas, y en qué difiere la réplica de lo impreso y por qué. Complementa a `docs/conclusiones.md` (qué conclusiones se sostienen) y a `AGENTS.md` (el detalle técnico; aquí se citan sus hallazgos H*, decisiones D* y observaciones O*). Estado al 2026-10-13.

| Sección | Contenido |
|---|---|
| 1 | La idea en 30 segundos |
| 2 | Conceptos previos: variables, efecto marginal, estrellas |
| 3 | **Los modelos** (ZINB, OLS, dos partes, log; inferencia; diagnósticos) |
| 4 | Figura por figura |
| 5 | Las estrellas en detalle |
| 6 | **Las tablas generadas** y cómo difieren de las impresas |
| 7 | Qué replicamos exacto, qué difiere y por qué |
| 8 | Qué se puede y qué no se puede concluir |
| 9 | Cómo explicarlo (guion) |
| 10 | Dónde mirar cada cosa |

---

## 1. La idea en 30 segundos

El paper pregunta: **¿qué grupos de personas quedan más expuestos a la actividad de reparto de última milla en Santiago?** Para responderlo cruza dos fuentes que casi nunca se juntan:

- **Dónde está la gente, hora a hora** (teléfonos de Entel): cuánta población hay en cada celda y de qué grupo socioeconómico (GSE), edad y sexo es.
- **Dónde están los camiones de reparto, hora a hora** (GPS de SimpliRoute): cuántos vehículos distintos pasan por esa celda y cuántos metros recorren dentro de ella.

La unidad es el **hexágono-hora**: un hexágono de ≈ 400 m (H3, resolución 9) en una hora del día (7:00 a 22:00). Son 11.144 hexágonos × 16 horas = **178.304 observaciones**. Con una regresión se mide si las celdas con **más proporción** de cierto grupo tienen **más vehículos o más metros recorridos**.

"Exposición" aquí significa **coincidir en el espacio y el tiempo** con vehículos de reparto. **No** son concentraciones de contaminante ni dosis inhaladas (§4 del paper).

Lo más original: se compara con un enfoque **estático** (la composición de cada hexágono es la residencial y no cambia durante el día, como en los estudios clásicos de justicia ambiental). Si dinámico y estático dan conclusiones distintas, ignorar la movilidad sesga el diagnóstico.

---

## 2. Conceptos que hay que tener claros antes de leer una figura

### 2.1 Las dos variables que se explican

| Símbolo | Qué es | Modelo |
|---|---|---|
| `Ỹ` (conteo) | Mediana, entre miércoles, de cuántos vehículos **distintos** pasaron por el hexágono en esa hora | ZINB (modelo de conteo) |
| `K̃` (distancia) | Mediana, entre miércoles, de los **metros** recorridos por vehículos dentro del hexágono en esa hora | OLS (mínimos cuadrados) |

Se usa la **mediana** de los miércoles (no el promedio) para que un día raro no domine, el mismo criterio que se aplica a la población.

### 2.2 Las variables explicativas y las categorías de referencia

Son **proporciones** (entre 0 y 1) de cada grupo en el hexágono-hora. Dentro de cada dimensión se omite una categoría de referencia, y cada coeficiente se lee **contra ella**:

- sexo: referencia **mujer** (se estima `Male`);
- edad: referencia **65+** (se estiman <25, 25–34, 35–44, 45–54, 55–64);
- GSE: referencia **AB**, el más rico (se estiman C1a, C1b, C2, C3 y D+E; D y E se juntan en los modelos).

Por eso en las figuras **65+ y AB valen 0**: no es un resultado, es el punto de comparación.

### 2.3 Qué es un "efecto marginal" y cómo se lee un número

Un efecto marginal es **cuánto cambia la variable explicada cuando la proporción de un grupo sube de 0 a 1, compensada por una caída equivalente en la categoría de referencia**.

Ejemplo con la Tabla 4 (dinámico), C1b:

- ZINB: **+2,67 vehículos**; OLS `K̃>0`: **+388 m**.
- Lectura literal: un hexágono-hora poblado solo por C1b tendría ≈ 2,7 vehículos más y ≈ 388 m más de recorrido que uno poblado solo por AB.
- Lectura realista (más fácil de explicar): como los hexágonos nunca son 100 % de un grupo, **una diferencia de 10 puntos porcentuales** en la proporción de C1b se asocia con ≈ 0,27 vehículos y ≈ 39 m más. `[Derivado]`

Las unidades son **por hexágono-hora** (no por persona ni por mes). El paper habla de "encuentros de un individuo", que es una forma de contarlo, pero el análisis es **ecológico**: describe celdas, no individuos (§5.1, p.12).

### 2.4 Las columnas de las tablas (y qué hay detrás de cada nombre)

| Columna impresa | Qué es realmente | Hallazgo |
|---|---|---|
| **ZINB** | Con estos datos la probabilidad de cero estructural es π̂ = 0, así que el ZINB **es** una binomial negativa. La cifra impresa coincide con la columna NB de las tablas que regeneraron los autores | H21, H23, H29 |
| **OLS** | Regresión de `K̃` sobre las 11 proporciones, todas las filas | H8 |
| **OLS `K̃>0`** ("no zero") | No es un OLS sobre los positivos: es un **modelo de dos partes** (un logit para "¿hay recorrido?" más un OLS para "¿cuánto?"), combinado en un solo efecto | H7 |
| **Log OLS** | OLS de `log(K̃)` sobre los hexágono-horas con distancia > 0; se imprime el coeficiente crudo | H8 |

Las figuras 6 a 10 dibujan solo **dos** de estas columnas: **ZINB (azul)** y **OLS `K̃>0` (rojo)**. Cada modelo se explica con detalle en la sección 3.

### 2.5 Las estrellas

Las estrellas **no están en las figuras**, solo en las Tablas 4 y 5. Son la respuesta a una pregunta: *¿este efecto se distingue de cero, o podría ser ruido?*

| Marca | Significa |
|---|---|
| `***` | p < 0,001 |
| `**` | p < 0,01 |
| `*` | p < 0,05 |
| `.` | p < 0,1 |
| (nada) | p ≥ 0,1: no se distingue de cero |

Cómo explicarlo:

- El p-valor sale de dividir el efecto por su **error estándar** (z = efecto / error). Más estrellas = el efecto es grande respecto de su incertidumbre.
- **Una estrella dice si hay señal, no cuánto importa.** Un efecto enorme sin estrellas es incierto; uno diminuto con `***` puede ser irrelevante en la práctica.
- Los errores estándar del paper son **agrupados por comuna** (51 comunas). Razón: hexágonos vecinos se parecen (el I de Moran es ≈ 0,42–0,47, positivo), así que las 178.304 filas **no son 178.304 datos independientes**. Agrupar por comuna reconoce que la información efectiva se parece más a 51 unidades que a 178 mil, y por eso **da errores más grandes y menos estrellas**. Ignorar el cluster infla la significancia.
- Son p-valores de una asociación **correlacional**; no prueban causalidad.

---

## 3. Los modelos

El paper estima **cuatro modelos** y los repite dos veces: con la demografía **dinámica** (Tabla 4) y con la **estática** (Tabla 5). Todos usan las mismas 11 variables explicativas (sección 2.2) sobre las 178.304 filas hexágono-hora, y todos son **de corte transversal**: una fila por hexágono-hora, sin trayectoria temporal.

### 3.1 Vista de conjunto

| Columna impresa | Variable explicada | Filas que usa | Pregunta que responde | El efecto marginal viene en… |
|---|---|---|---|---|
| **ZINB** | `Ỹ`: vehículos distintos (conteo) | todas | ¿Las celdas con más proporción del grupo reciben más vehículos? | vehículos por hexágono-hora |
| **OLS** | `K̃`: metros recorridos | todas (incluye ceros) | ¿Tienen más metros recorridos? | metros |
| **OLS `K̃>0`** | `K̃` | todas, en dos partes | Lo mismo, contando a la vez que haya recorrido y cuánto | metros |
| **Log OLS** | `log K̃` | solo `K̃ > 0` | ¿Cambia proporcionalmente el recorrido? | coeficiente (cambio relativo) |

**Por qué dos variables explicadas** (§4.1 del paper): el conteo captura la **densidad** de vehículos, y las emisiones crecen más que linealmente con ella (congestión, arranque y parada); la distancia captura los **kilómetros**, que es la unidad de los factores de emisión estándar.

### 3.2 ZINB: el modelo de conteo

**Por qué un modelo de conteo.** `Ỹ` es un número entero no negativo (media 2,22, máximo 77) y el 29,56 % de las celdas tiene cero vehículos. Un Poisson no sirve: supone varianza igual a la media, y aquí la varianza es unas **7,7 veces** la media. Esa es la cifra del test de Cameron–Trivedi (7,73 en el paper, 7,75 en la réplica).

**Las piezas** (Ecs. 1 a 4 del paper):

```
log(μ) = β0 + β1·Male + β2·Under25 + … + β11·D+E     (el efecto de cada grupo, en escala log)
Var(Ỹ) = μ + μ²/θ                                    (binomial negativa: la varianza crece más que la media)
P(Ỹ = 0)   = π + (1−π)·f_NB(0)                       (ceros "estructurales" más ceros de azar)
P(Ỹ = y>0) = (1−π)·f_NB(y)
E[Ỹ] = (1−π)·μ
efecto marginal (Ec. 4) = (1−π)·β_k·μ                (se promedia sobre las 178.304 filas)
```

- **`μ`** es el número esperado de vehículos en la celda; **`θ`** controla cuánto se dispersan los conteos (con estos datos θ ≈ 0,76 en el dinámico y 0,84 en el estático).
- **`π`** es la probabilidad de un **cero estructural** (zonas donde nunca habría reparto: parques, lugares sin cobertura del servicio). En el paper es **la misma para todas las celdas** (inflación constante).
- El coeficiente `β_k` vive en escala logarítmica; el **efecto marginal** lo traduce a vehículos. Como depende de `μ`, que cambia de celda en celda, se calcula el **promedio** sobre todas las celdas.

**Detalles que importan para replicar.**

- La variable es `round(median_vehicles)`: la binomial negativa pide enteros y la mediana de varios miércoles suele terminar en 0,5 (5.810 filas). R redondea el 0,5 al par (0,5 → 0; 1,5 → 2), y se replicó así.
- **Con estos datos π̂ = 0** (frontera). El intervalo del 95 % de π es [0, 0,00008] (dinámico) y [0, 0,00004] (estático): los datos **no sostienen ceros estructurales**, y el 29,6 % de ceros lo explica la binomial negativa como ceros de azar. El paper no reporta π.
- Consecuencia: **el "ZINB" impreso es numéricamente una binomial negativa.** La cifra del paper coincide con la columna NB de las tablas que regeneraron los autores, y no con el ZINB de `pscl`, que se detiene unas décimas de log-verosimilitud antes del máximo (H21–H23, H29).
- Ojo con el alcance: esto vale **solo para π constante**, que es lo que describe el paper. El paper dice haber probado covariables en la parte de inflación ("resultados sustancialmente idénticos"), pero no lo muestra y no lo replicamos.
- Para que se pueda replicar a la precisión impresa se reporta el **máximo** de la verosimilitud (`fit_zinb_mle`); la implementación estándar de `statsmodels` no puede representar π = 0.
- El código de los autores multiplica por (1−π) **dos veces** en el efecto marginal (un error). No cambia nada porque π̂ = 0, y la sensibilidad en hora local usa la fórmula correcta (H10).

### 3.3 OLS de la distancia (todas las filas)

```
K̃ = β0 + β1·Male + … + β11·D+E + ε          el efecto marginal de cada grupo es su coeficiente β_k, en metros
```

Es la regresión lineal más simple, ajustada sobre **todas** las filas, ceros incluidos (32,8 % de las celdas tiene distancia 0). Su limitación: trata un recorrido de 0 m como una observación más y no impide predecir distancias negativas. Por eso el paper la compara con las dos variantes siguientes.

### 3.4 "OLS `K̃>0`": en realidad un modelo de dos partes

El nombre induce a error: **no es un OLS sobre las celdas con distancia positiva**, es un **modelo de dos partes** (H7):

1. **Parte 1 (logit):** ¿esta celda tiene algún recorrido (`K̃ > 0`)? Se ajusta sobre todas las filas. En promedio, el 67,2 % de las celdas lo tiene (`pr`).
2. **Parte 2 (OLS):** si hay recorrido, ¿cuántos metros? Se ajusta solo sobre las filas con `K̃ > 0`. Esos recorridos tienen un promedio de 490,5 m (`m`).
3. **Efecto marginal combinado** (fórmula del código de los autores):

```
AME_k = pr·(1−pr)·β_logit,k·m  +  β_OLS,k·pr
          └ cambia la probabilidad de haber recorrido ┘   └ cambia los metros si hay recorrido ┘
```

Se interpreta como el cambio esperado en metros **contando ambos canales**: que la celda tenga o no recorrido, y cuánto recorrido tenga. Es la columna roja de las Figs. 6 a 10. Un OLS simple sobre los positivos da otras cifras (por ejemplo, C1b: 474,78 en vez de 388,32), y solo el modelo de dos partes reproduce lo impreso.

### 3.5 Log OLS

`log(K̃)` sobre las celdas con distancia positiva. El coeficiente se interpreta como un **cambio proporcional**: pasar la proporción de un grupo de 0 a 1 multiplica el recorrido por `exp(β)`. Se imprime el coeficiente crudo.

Cómo lo leen los autores: `β × 100` como porcentaje (0,4232 → "42,3 %"; 0,6061 → "60,6 %"; 0,2429 → "24 %"). Eso solo es una aproximación válida para β pequeños; leído como corresponde, `exp(β) − 1` da 52,7 %, 83 % y 27,5 %. Es una decisión que se documenta y no se corrige (D9). Además, los scripts dinámicos de los autores multiplican el coeficiente por la media de `K̃>0` en su tabla de referencia, mientras la Tabla 4 impresa trae el coeficiente crudo (H9); esa multiplicación solo importa para comparar sus estrellas.

### 3.6 Dinámico frente a estático: qué cambia entre las Tablas 4 y 5

**Solo cambia el origen de las proporciones.** Los modelos, las variables explicadas y los datos de vehículos son los mismos.

| | Dinámico (Tabla 4) | Estático (Tabla 5) |
|---|---|---|
| Proporciones | Las de la **población presente** en cada hexágono y cada hora (Entel) | Las **residenciales** de cada hexágono, iguales a todas las horas |
| Archivo | `miercoles_rm.csv` | `datosxhexagono.csv` |
| Varía con la hora | Sí | No |

La composición estática es muy distinta de la horaria (por ejemplo, la proporción de menores de 25 años es 35,6 % frente a 19,5 % en nuestro perfilado de los datos, `AGENTS.md` §8.1), y el paper **no explica cómo se construyó**. Esa es la razón de fondo de las diferencias entre las dos tablas.

### 3.7 Errores estándar, p-valores y estrellas: cómo se calculan

- **Errores estándar agrupados por comuna** (51 comunas): una estimación "sandwich" que permite que las celdas de una misma comuna estén correlacionadas entre sí. Se valida contra R (`sandwich::vcovCL`): los OLS coinciden a ≤ 0,5 % y el ZINB a ≤ 1,5 % (H25).
- **ZINB:** el sandwich del modelo completo (inflación, conteo y dispersión), que es lo que calcula el código de los autores. Con π̂ = 0 no coincide exactamente con el de la binomial negativa equivalente (sus errores difieren entre −17 % y +6 %), por eso se usa el del modelo completo.
- **OLS `K̃>0`:** el código de los autores combina el error del logit (sin agrupar) y el del OLS (agrupado) **en cuadratura**, una aproximación burda que se replica tal cual (H12).
- **p-valor** con la distribución **normal** (no la t), y las estrellas con los umbrales de la sección 2.5.
- **Variantes** que se calculan: `paper_text` (cluster por comuna en todo, lo que dice el paper), `authors_script` (como el script, con el cluster `NULL` del ZINB estático) e `iid` (sin cluster, solo de referencia). Ver la sección 5.

### 3.8 Diagnósticos y estadísticos descriptivos (no son modelos de exposición)

| Qué | Para qué | Resultado de la réplica | Paper |
|---|---|---|---|
| **Cameron–Trivedi** | ¿Hay sobredispersión? (justifica no usar Poisson) | 7,750 | 7,73 ✅ |
| **I de Moran** | ¿Hay correlación espacial? (justifica el cluster por comuna) | 0,419 y 0,430 (literal); 0,466 y 0,470 (otra lectura) | 0,4694 y 0,4756 🟡 |
| **Test de π** | ¿Hay ceros estructurales? | π̂ = 0; IC 95 % [0, 8·10⁻⁵]; p de frontera = 1 | No lo reporta ℹ️ |
| **Wasserstein** | ¿Cuánto cambia la distribución espacial de cada grupo entre la mañana y la tarde? Ranking 1 = el más móvil; no entra en los modelos | 13/15 valores dentro de la banda del 95 % | Tabla 2 🟡 |

- **I de Moran:** mide si hexágonos vecinos tienen valores parecidos (0 = sin patrón, 1 = agrupamiento perfecto). Todas las lecturas dan valores muy por encima de 0, así que la correlación espacial positiva se confirma. El paper **no define** la matriz de vecindad ni cómo promedia las 16 horas, por lo que la cifra exacta no se identifica.
- **Wasserstein** (distancia del transporte óptimo, "earth mover"): cuánta "tierra" hay que mover para pasar del mapa de la mañana al de la tarde. Se divide por la mediana de su categoría: un valor en torno a 1 es "movilidad típica" y, en el sexo (dos grupos), los dos valores suman 2.

### 3.9 Lo que los modelos **no** incluyen

- **No hay controles:** ni población total del hexágono, ni uso del suelo, ni efectos fijos de comuna, ni rezagos espaciales. Es una asociación entre composición y reparto, no un efecto causal: parte del patrón puede deberse a que ciertos grupos viven o trabajan en zonas con otras características.
- **π constante** y solo el intercepto en la parte de inflación.
- **La dependencia espacial no se modela**; solo se corrige el error estándar con el cluster por comuna.
- Las celdas con población 0 (el 0,8 % de las filas, con todas las proporciones en 0) **entran** igual a las regresiones, como en el código de los autores.

---

## 4. Figura por figura

Resumen rápido de lo replicado:

| Fig. | Qué muestra | Réplica |
|---|---|---|
| 1 | Mapas de población de AB y C1b, mañana y tarde | 🟡 patrón y valores sí; los extremos de la escala de color difieren |
| 2 | Puntos GPS de camiones por hexágono | 🚫 no reproducible (falta el GPS crudo); hay un sustituto rotulado |
| 3, 4, 5 | Diagramas del método | — no se replican |
| 6, 8 | Efectos por GSE y por edad (dinámico) | ✅ mismos puntos |
| 9, 10 | Efectos por GSE y por edad (estático) | ✅ mismos puntos |
| 7 | Gramos de NOx y PM por GSE | 🟡 reproduce las 12 etiquetas, pero con un factor derivado de ellas |

### 4.1 Fig. 1 — ¿Dónde está la población de AB y de C1b? (`docs/figures/fig1_seg_population.png`)

**Qué es.** Cuatro mapas de Santiago: SEG AB (arriba) y SEG C1b (abajo), con la población promedio de 10:00 a 12:00 (izquierda) y de 20:00 a 22:00 (derecha). Cada hexágono se pinta según cuánta población de ese grupo hay. Dentro de cada grupo, la **escala de color es la misma** en la mañana y en la tarde, para poder comparar.

**Cómo leerla.** Mirar el color: más cálido = más gente de ese grupo. Comparar mañana con tarde dentro del mismo grupo.

**Qué se deduce (según el paper, p.12).**

- **AB cambia de lugar:** de día se concentra en el centro y el nororiente (una franja que sube hacia el noreste), y de noche se recoge en el sector nororiente. Es el grupo más móvil.
- **C1b casi no cambia:** el mismo centro de la ciudad de día y de noche. Es el grupo menos móvil (Tabla 2).
- Esto sostiene el **mecanismo** que propone el paper: C1b se queda en las zonas con más reparto (Fig. 2), AB las visita para trabajar y vuelve a zonas más limpias.

**Qué reproduce la réplica.** El patrón espacial y los valores por hexágono (coinciden con un cálculo independiente en pandas a 10⁻¹⁰); la Tabla 2 (medias y desviaciones) coincide exactamente con este panel.

**En qué difiere y por qué.**

| Diferencia | Detalle | Por qué |
|---|---|---|
| Extremos de la escala | Nuestra escala común llega a **1.511** (AB) y **7.073** (C1b); el paper imprime **1600** y **7000** (−5,5 % y +1,0 %) | **No sabemos.** Probamos cuatro formas de agregar las horas y ninguna da ambos números. Hipótesis **no probada**: los mapas usan otro período o corte de la población. No afecta a la lectura (H35) |
| Estilo | El script del paquete de los autores dibuja con `inferno` y escala logarítmica, pero la Fig. 1 impresa es lineal y arcoíris. Seguimos el estilo **impreso** | La Fig. 1 salió de otra versión del script (H35, O3) |
| Rótulos | El paper llama "Daytime Population" también al panel de 20–22 h y su leyenda dice "SEG AB and SEG C1" frente a los paneles "C1B". Los rótulos de los paneles se conservan | Observación del original (O1) |

**Cuidado al explicarla.** Las personas no están clasificadas por GSE: el GSE de cada teléfono es **una probabilidad** tomada del censo de la zona donde pasa las noches. El mapa muestra población **esperada** de cada grupo.

### 4.2 Fig. 2 — ¿Dónde están los camiones? (sustituto: `docs/figures/fig2_proxy_vehicles.png`)

**Qué es en el paper.** Un mapa de la cantidad de **puntos GPS de camiones por hexágono** (escala logarítmica con etiquetas 0, 11, 147 y 1.807). Muestra los "puntos calientes" del reparto.

**Qué se deduce (según el paper, pp.12 y 16).** Los puntos calientes del reparto están en los distritos comerciales centrales. Es el complemento de la Fig. 1: C1b pasa el día en esas mismas zonas, y de ahí sale el mecanismo de la exposición.

**Qué hicimos.** **No es reproducible**: necesita el GPS crudo de todos los días (≈ 52 GB, con restricciones de uso, que no tenemos). Hicimos un **sustituto rotulado** en el propio título ("PROXY, NOT Fig. 2"): la **mediana de vehículos por hexágono**, promediada en las horas 7–22, con el mismo estilo (`inferno`, escala logarítmica). Se ve la red vial principal (autopistas, anillo central y ejes radiales). No comparé este sustituto con la Fig. 2 impresa celda a celda, porque no es la misma medida.

**Por qué no es lo mismo.** Cuenta vehículos distintos, no puntos GPS, y trabaja con medianas ya agregadas; por eso la escala es otra (0 a 47 vehículos, no 0 a 1.807 puntos). Sirve para ver el patrón espacial, **no** para comparar cifras con el paper.

### 4.3 Figs. 3, 4 y 5 — Diagramas

Explican el método (la fusión de datos, el conteo de vehículos con 3 vehículos y 4 hexágonos, y la distancia dentro de cada hexágono). No tienen datos y no se replican. Una diferencia que sí importa: la Fig. 5 muestra la distancia **recortada** dentro de cada hexágono, pero el código de los autores **descarta** los tramos que cruzan hexágono u hora (H4). Replicamos el código (es lo que produjo las tablas).

### 4.4 Figs. 6, 8, 9 y 10 — Efectos marginales (las cuatro gráficas de líneas)

Las cuatro tienen **la misma construcción**; cambia el tipo de grupo y si es dinámico o estático:

| Fig. | Grupo | Modelo | Archivo |
|---|---|---|---|
| 6 | GSE | dinámico | `fig6_seg_dynamic` |
| 8 | Edad | dinámico | `fig8_age_dynamic` |
| 9 | GSE | estático | `fig9_seg_static` |
| 10 | Edad | estático | `fig10_age_static` |

**Cómo leerlas.**

- **Eje horizontal:** los grupos, con la categoría de referencia (AB o 65+) al final, en 0.
- **Línea azul (eje izquierdo):** efecto sobre el **conteo** de vehículos (ZINB), en vehículos.
- **Línea roja punteada (eje derecho):** efecto sobre la **distancia** (OLS `K̃>0`), en metros.
- **Un punto por encima de 0** significa: las celdas con más proporción de ese grupo tienen **más** reparto que las de la referencia. Por debajo de 0, menos.
- **Las figuras solo muestran puntos, no incertidumbre.** Los patrones se respaldan con las tablas y sus estrellas.

**Trampa importante: el eje derecho está reescalado.** El código de los autores (`plot_dual_axis`) transforma la serie roja para que su mínimo y su máximo caigan exactamente sobre los de la azul. Los picos coinciden **por construcción**. Por eso las figuras permiten comparar **formas**, no **magnitudes**: no se puede decir que "la línea roja sube más que la azul" ni leer el 400 de la derecha contra el 2,8 de la izquierda (H34, O5). El paper lo dice así: se muestran juntos "para enfatizar sus patrones similares".

#### Fig. 6 — GSE, dinámico (`fig6_seg_dynamic.png`)

| | D+E | C3 | C2 | C1b | C1a | AB |
|---|---:|---:|---:|---:|---:|---:|
| ZINB (vehículos) | 0,50 | 2,20 | 2,66 | 2,67 | 2,80 | 0 |
| OLS `K̃>0` (metros) | −88 | 125 | 217 | 388 | 326 | 0 |

- **Forma:** una **U invertida**: sube desde D+E, llega al máximo en la clase media (C1a, C1b, C2) y cae de golpe en AB.
- **Qué se deduce:** la clase media está **más expuesta** que los dos extremos. Los autores lo interpretan como un efecto de **dónde** pasan el día, no de cuánto se mueven: tanto AB como D+E circulan por zonas con menos reparto, y la clase media está en las zonas de más actividad.
- **Matiz:** el paper destaca a C1b. En distancia sí es el máximo (388 m), pero en conteo el máximo es **C1a** (2,80 frente a 2,67), y el efecto de C1b en el conteo ni siquiera se distingue de cero en la tabla impresa (O6).
- **Réplica:** mismos puntos que la Tabla 4 impresa.

#### Fig. 8 — Edad, dinámico (`fig8_age_dynamic.png`)

| | <25 | 25–34 | 35–44 | 45–54 | 55–64 | 65+ |
|---|---:|---:|---:|---:|---:|---:|
| ZINB (vehículos) | −3,63 | **11,01** | −3,01 | −1,54 | −0,31 | 0 |
| OLS `K̃>0` (metros) | −550 | **1.446** | −179 | −141 | 12 | 0 |

- **Forma:** un pico muy marcado en **25–34 años**; los menores de 25 quedan por debajo de los 65+ y el resto es casi plano.
- **Qué se deduce:** los 25–34 son el grupo más asociado a celdas con reparto. El paper lo atribuye a la participación laboral (oficinas en zonas comerciales); los menores de 25 (estudiantes) y los mayores (jubilados) estarían menos presentes en esas zonas en horario laboral.
- **Cuidado:** como la referencia es 65+, los valores negativos quieren decir "menos que los 65+", no "ninguna exposición".

#### Fig. 9 — GSE, estático (`fig9_seg_static.png`)

| | D+E | C3 | C2 | C1b | C1a | AB |
|---|---:|---:|---:|---:|---:|---:|
| ZINB (vehículos) | −5,12 | 7,27 | 5,53 | **−14,28** | 6,77 | 0 |
| OLS `K̃>0` (metros) | −283 | 1.215 | 425 | **−896** | 1.543 | 0 |

- **Forma:** el patrón de la Fig. 6 **casi se mantiene, salvo C1b**, que se desploma al valor más bajo.
- **Qué se deduce (la conclusión central del paper):** con la demografía **residencial** (estática), C1b aparece como el grupo **menos** expuesto; con la población **presente de día** (dinámica), aparece como el más expuesto. La razón propuesta: C1b vive en zonas con poco reparto pero **trabaja en las zonas de mayor actividad**. Mirar solo dónde duerme la gente llevaría a **proteger las zonas equivocadas**.
- **Cuidado (la parte débil, ver 5.4):** con el método de errores estándar que declara el paper, el efecto estático de C1b **no es significativo** (p ≈ 0,48 en el conteo). La conclusión cualitativa se sostiene en los puntos, pero su respaldo estadístico es frágil.

#### Fig. 10 — Edad, estático (`fig10_age_static.png`)

| | <25 | 25–34 | 35–44 | 45–54 | 55–64 | 65+ |
|---|---:|---:|---:|---:|---:|---:|
| ZINB (vehículos) | −9,00 | **5,62** | −10,27 | −11,47 | −10,14 | 0 |
| OLS `K̃>0` (metros) | −1.433 | **1.953** | −695 | −50 | −1.316 | 0 |

- **Forma:** casi la misma que la Fig. 8, "desplazada hacia abajo" (palabras del paper): el pico en 25–34 se mantiene y, salvo ese grupo, todos quedan **bajo** los 65+.
- **Qué se deduce:** el pico de 25–34 es robusto al enfoque; pero el grupo de 65+ queda como referencia en ambos, así que no se pueden comparar niveles absolutos entre la Fig. 8 y la 10.

**Sobre el sexo.** No tiene figura propia. En el dinámico, `Male` = +3,56 vehículos (ZINB) y el paper concluye que los hombres están ~24 % más expuestos (coeficiente 0,2429 del modelo log, leído como %); en el estático el signo se invierte (−3,08). Ver 5.4 sobre por qué el 24 % no se sostiene.

**Qué replica la réplica en estas cuatro figuras.** Los mismos puntos que las Tablas 4 y 5 impresas (diferencia ≤ 1·10⁻⁴, que es el redondeo a 4 decimales) y el **mismo eje doble reescalado** que usa el código de los autores. Lo único que no replican es lo que las figuras no muestran: las estrellas (sección 5).

### 4.5 Fig. 7 — Gramos de NOx y PM por GSE (`fig7_emissions_seg.png`)

**Qué es.** Las mismas diferencias de la Fig. 6, expresadas en **gramos adicionales de NOx y PM por mes** respecto de AB.

| | D+E | C3 | C2 | C1b | C1a | AB |
|---|---:|---:|---:|---:|---:|---:|
| NOx (g) | −16,1 | 22,8 | 39,5 | **70,8** | 59,5 | 0 |
| PM (g) | −3,0 | 4,2 | 7,3 | **13,2** | 11,1 | 0 |

**Qué se deduce (según el paper).** C1b queda expuesto a 70,8 g de NOx y 13,2 g de PM adicionales al mes respecto de AB. Es una cifra **ilustrativa**, no una medición de lo que alguien inhala.

**Qué hay detrás (hallazgo de la réplica).** Cada barra es **una constante por el efecto OLS `K̃>0` de la Tabla 4**: ≈ 0,1824 g de NOx y ≈ 0,0339 g de PM por metro marginal (por ejemplo, 388,32 × 0,18241 = 70,8). El paper no da los factores de emisión, ni la categoría de vehículo ni el multiplicador que lleva a "al mes", y el paquete de los autores tampoco los contiene (H36, O7).

**En qué difiere y por qué.** La réplica **reproduce las 12 etiquetas**, pero con constantes que **deducimos de esas mismas etiquetas**. Es decir, la figura es **idéntica por construcción**, pero **no es una estimación independiente de emisiones** y no sirve para auditar los factores de la fuente (EMEP/EEA).

**Cuidados al explicarla.**

- Las barras **heredan** la forma de la columna roja (OLS `K̃>0`); no aportan información nueva sobre exposición.
- El "60,6 % de aumento" que cita el paper **no sale de los gramos**: es el coeficiente 0,6061 del modelo log leído como porcentaje (×100). Leído como corresponde a un modelo logarítmico, `exp(0,6061) − 1` ≈ **83 %** (D9). Son dos modelos distintos y conviene no mezclarlos.

---

## 5. Las estrellas, en detalle

### 5.1 Tres juegos de estrellas distintos

Para no confundirse, hay **tres** conjuntos de estrellas:

1. **Las impresas en el paper** (Tablas 4 y 5).
2. **Las que calcula nuestra réplica**, con el método declarado: cluster por comuna (variante `paper_text`), o como lo hace el script de los autores (variante `authors_script`, que difiere solo en el ZINB estático).
3. **Las de las tablas que regeneraron los autores** con su propio código (`00_out/reference_tables_42wed/`).

| Comparación | Tabla 4 (dinámico) | Tabla 5 (estático) |
|---|---:|---:|
| Réplica frente a las **regeneradas por los autores** | **44/44** (`paper_text`) | **44/44** (`authors_script`) |
| Réplica frente a las **impresas** | 23/44 (`paper_text`) | 38/44 (`authors_script`); 27/44 (`paper_text`) |
| Regeneradas por los autores frente a las impresas | 23/44 | 38/44 |

Lectura: **nuestro cálculo coincide con el de los autores en las 88 celdas**; lo que no coincide es lo **impreso** en el paper, y eso ocurre también con el código de los autores.

### 5.2 Por qué las impresas no coinciden

- **Los propios autores lo reconocen** (primer error que admiten): las estrellas de la Tabla 4 impresa "parecen venir de una corrida distinta" y no logran reproducirlas con ningún script. Su hipótesis: se usó por error, al finalizar el paper, una base de prueba de **2 miércoles**.
- **Nuestra prueba:** con esa base de 2 miércoles (solo como diagnóstico aislado, **no es una réplica**) las estrellas coinciden 78/88, mucho más que con la base correcta (61/88). Es coherente con su explicación, pero **no la prueba** (quedan 10 celdas distintas).
- **Dirección del error:** en la Tabla 4, de las 21 celdas que difieren, la impresa tiene **más** estrellas que el método correcto en 17. Es decir, **el paper impreso aparenta más significancia de la que hay**.
- **Consecuencia:** que nuestra réplica no iguale las estrellas impresas **no es una falla de la réplica**; con el método correcto (el que declara el paper) las estrellas son otras.

### 5.3 El caso del ZINB estático: un error en el código de los autores

En el script estático de los autores, la variable del cluster queda vacía (`NULL`) porque el archivo de demografía estática no trae la comuna. `vcovCL(…, cluster = NULL)` toma entonces **cada fila como su propio cluster**: errores robustos **sin agrupar**. Resultado:

| Cluster | Estrellas del ZINB estático |
|---|---|
| Sin agrupar (`NULL`, el error) | **11/11** con `***` (las que imprime el paper) |
| Por comuna (lo que dice el paper) | 4/11 con alguna estrella y **ninguna** `***` |

Es la regla del cluster en acción: **sin agrupar, todo parece significativo**. Por eso el C1b estático (−14,28) aparece con `***` en el paper, pero con cluster por comuna no se distingue de cero (p ≈ 0,48). Los autores **no mencionaron** este punto; está entre las consultas de la segunda ronda.

### 5.4 Qué efectos son realmente robustos (con el método declarado)

| Conclusión | ¿Respaldo estadístico? |
|---|---|
| U invertida por GSE (dinámico) | ✅ `***` en OLS `K̃>0` para C1a, C1b, C2 y C3; en el ZINB `***` en C1a, C2 y C3 y `*` en C1b |
| Pico en 25–34 años | ✅ `***` en el ZINB y en OLS `K̃>0` |
| C1b: de más expuesto (dinámico) a menos (estático) | ⚠️ **Débil**: no significativo en el estático |
| Hombres ~24 % más expuestos | ❌ **No se sostiene** (en el modelo log, p = 0,116; los autores lo reconocen). En el conteo dinámico, `Male` sí es `***`; el cambio de signo estático no es significativo |

---

## 6. Las tablas generadas y cómo difieren de las impresas

Las tablas de la réplica están en `outputs/as_published/tables/` (no se versionan). Esta sección dice cuáles mirar, cómo leerlas y en qué se diferencian de lo impreso.

### 6.1 Qué tablas tiene el paper y cuáles replicamos

| Paper | Contenido | Réplica | Archivos de la réplica |
|---|---|---|---|
| **Tabla 1** | Revisión de literatura | No aplica | — |
| **Tabla 2** | Descriptivos de la población flotante (media, desviación, %, Wasserstein, ranking) | ✅ Mean, Std y % · 🟡 Wasserstein y ranking | `table2.csv`, `table2_with_mobility.csv`, `table2_mobility_seeds.csv`, `comparison_table2.csv` |
| **Tabla 3** | Descriptivos de los datos de GPS | 🚫 No se replica | — |
| **Tabla 4** | Efectos marginales, enfoque dinámico | ✅ valores · 🟡 estrellas | `table4_complete_no_stars.csv`, `table4_vs_paper_paper_text.md`, `comparison_table4.csv`, `inference_dynamic_*.csv`, `stars_dynamic_*.csv` |
| **Tabla 5** | Efectos marginales, enfoque estático | ✅ valores · 🟡 estrellas | `table5_complete_no_stars.csv`, `table5_vs_paper_*.md`, `comparison_table5.csv`, `inference_static_*.csv`, `stars_static_*.csv` |

### 6.2 Tabla 2: descriptivos de la población flotante

**Qué muestra.** Para cada grupo (sexo, edad, GSE), sobre los hexágono-horas: la **media** y la **desviación estándar** de su población (`Mean`, `Std`), su **proporción media** y la desviación de esa proporción (`Mean (%)`, `Std (%)`), y la **movilidad** (Wasserstein y ranking).

**Qué se deduce.** La población media por celda es 472,8 personas, pero con una desviación de 938,6: está **muy concentrada** en pocas celdas. Las proporciones de cada grupo varían mucho entre celdas (AB: media del 3,5 % y desviación del 9,7 %; C1b: 7,4 % y 11,1 %), es decir, la composición social es muy **desigual en el espacio**.

**Qué coincide.** `Mean`, `Std`, `Mean (%)` y `Std (%)` coinciden con el paper en **las 62 celdas**, al redondeo que imprime (diferencia máxima 0,005 en la media y la desviación y 0,05 en los porcentajes; `comparison_table2.csv`).

**Qué no coincide: Wasserstein y ranking.** El valor impreso proviene de una **muestra aleatoria de 5.000 hexágonos sin semilla** (H24), así que es una sola extracción que no se puede repetir. Por eso la réplica no entrega un número, sino la **banda de 200 semillas** (`table2_mobility_seeds.csv`):

| Grupo | Impreso | Mediana de 200 semillas | Banda del 95 % | ¿Dentro? |
|---|---:|---:|---:|:-:|
| Hombre | 1,024 | 1,027 | 1,017–1,038 | ✅ |
| Mujer | 0,976 | 0,973 | 0,962–0,983 | ✅ |
| <25 | 0,920 | 0,943 | 0,903–0,986 | ✅ |
| 25–34 | 0,998 | 0,989 | 0,967–1,015 | ✅ |
| 35–44 | 1,002 | 1,014 | 0,991–1,040 | ✅ |
| 45–54 | 1,122 | 1,100 | 1,049–1,148 | ✅ |
| 55–64 | 1,055 | 1,025 | 0,988–1,086 | ✅ |
| 65+ | 0,726 | 0,706 | 0,672–0,759 | ✅ |
| AB | 1,337 | 1,246 | 1,070–1,476 | ✅ |
| C1a | 0,604 | 0,566 | 0,467–0,667 | ✅ |
| C1b | 0,508 | 0,463 | 0,386–0,556 | ✅ |
| C2 | 1,000 | 0,888 | 0,749–1,000 | ✅ |
| C3 | 1,066 | 1,011 | 1,000–1,110 | ✅ |
| D | 0,968 | 1,019 | 1,000–1,104 | ❌ |
| E | 1,157 | 1,023 | 0,989–1,138 | ❌ |

- **13 de 15 dentro de la banda.** D y E quedan fuera (E con z = 2,7).
- Lo **estable** (cierto en prácticamente todas las semillas): hombre más móvil que mujer, 45–54 el grupo más móvil y 65+ el menos móvil, AB el más móvil y C1b el menos móvil en GSE.
- Lo **no estable**: el orden exacto entre C2, C3, D y E, que están casi empatados. Los 15 rankings impresos se reproducen **a la vez** en solo 1 de las 200 semillas.
- `table2_with_mobility.csv` trae además la lectura **determinista** del texto del paper (transporte óptimo con los 11.144 hexágonos): error máximo 0,14 respecto de lo impreso y 12 de 15 rankings. Es la que describe el texto del paper; los autores aclararon después que su cálculo real usa la muestra.

### 6.3 Tabla 3: descriptivos del GPS (no replicada)

La Tabla 3 del paper (3.345,74 vehículos por día, 334,23 empresas por día, 5.023.366,51 puntos GPS por día, 41 miércoles, 100,88 km por vehículo por día, 802,29 puntos por vehículo, p90 de 5,45 min entre puntos) se calcula **desde el GPS crudo**, que no tenemos (solo disponemos de un día filtrado, el 27-11-2024, y de las medianas ya agregadas por los autores). Sus cifras se guardan en `reference/paper_tables/table3_vehicle_dataset.csv` solo como referencia. Un matiz: el paper dice 41 miércoles, mientras que los conteos usan 42 (con el feriado del 2024-05-01) y la distancia 41 (H3).

### 6.4 Tablas 4 y 5: los efectos marginales

**Cómo se lee una fila:** una fila por grupo y, por cada modelo, `valor + estrellas`. Es la misma tabla que imprime el paper.

**Archivos, del más cómodo al más técnico:**

| Archivo | Para qué sirve |
|---|---|
| `table{4,5}_vs_paper_<variante>.md` | **El que conviene abrir.** Réplica y paper lado a lado, con marcas donde difieren (`‡` valor, `†` estrellas) y un resumen por columna. Lo genera `scripts/17_paper_format_tables.py` |
| `table{4,5}_complete_no_stars.csv` | Los valores de la réplica (4 decimales), sin estrellas |
| `inference_{dynamic,static}_<variante>.csv` | Por cada modelo: error estándar (`_se`), p-valor (`_p`) y estrellas (`_sig`) |
| `stars_{dynamic,static}_<variante>.csv` | Comparación celda a celda de las estrellas con las **impresas**: `computed`, `paper`, `p`, `ok` |
| `comparison_table{4,5}.csv` | Por columna: celdas comparadas, celdas dentro de tolerancia y diferencia máxima de **valores** |

Variantes: `paper_text` (cluster por comuna), `authors_script` (como el script de los autores) e `iid` (sin cluster, solo referencia). Si en `outputs/` hay archivos `*_cluster.csv` (del 6 de octubre), son de una versión anterior del mismo script, cuando esa variante aún se llamaba `cluster`; tienen las mismas estrellas que `paper_text` y se pueden borrar.

**Diferencias con el paper impreso, en dos capas.**

*Capa 1, los valores: no hay diferencia.* Las 52 celdas de cada tabla coinciden dentro del redondeo que imprime el paper (6·10⁻⁵):

| Columna | Tabla 4, diferencia máx. | Tabla 5, diferencia máx. |
|---|---:|---:|
| ZINB | 5,7·10⁻⁵ | 4,4·10⁻⁵ |
| OLS | 4,3·10⁻⁵ | 4,9·10⁻⁵ |
| OLS `K̃>0` | 4,7·10⁻⁵ | 4,9·10⁻⁵ |
| Log OLS | 4,9·10⁻⁵ | 4,8·10⁻⁵ |

*Capa 2, las estrellas: sí hay diferencia.* Estrellas iguales a las impresas, de 11 por columna:

| Qué se compara con lo impreso | ZINB | OLS | OLS `K̃>0` | Log OLS | Total |
|---|---:|---:|---:|---:|---:|
| Tabla 4, `paper_text` | 8 | 5 | 7 | 3 | **23/44** |
| Tabla 5, `authors_script` | 11 | 9 | 10 | 8 | **38/44** |
| Tabla 5, `paper_text` | 0 | 9 | 10 | 8 | **27/44** |

Contra las **tablas regeneradas por los autores**, en cambio, coinciden **44/44** en la Tabla 4 (`paper_text`) y 44/44 en la Tabla 5 (`authors_script`); la Tabla 5 con cluster por comuna en todo da 33/44, porque el ZINB estático de los autores no agrupa (sección 5.3).

**Ejemplos de celdas donde las estrellas difieren** (Tabla 4, réplica con cluster por comuna frente a lo impreso):

| Celda | Réplica | Impreso |
|---|:-:|:-:|
| Hombre, OLS | `.` | `*` |
| Hombre, OLS `K̃>0` | `**` | `***` |
| 35–44 años, OLS `K̃>0` | sin estrellas | `***` |
| Hombre, Log OLS (el "24 %") | sin estrellas | `***` |
| 45–54 años, OLS `K̃>0` | `.` | sin estrellas |
| 45–54 años, Log OLS | `***` | sin estrellas |
| C1b, ZINB | `*` | sin estrellas |

**Cómo leer las diferencias.** De las 21 celdas distintas en la Tabla 4, **17** tienen **menos** estrellas en la réplica y 4 más. Las impresas aparentan más significancia que la que da el método correcto. Pero esas diferencias no tocan los **valores** (signo y magnitud), que son lo que dibujan las figuras; solo cambia el respaldo estadístico (sección 5.4).

**Diferencias de fondo entre lo impreso y lo que reproducimos** (detalle en la sección 7.3):

- La columna **"ZINB"** es la binomial negativa (π̂ = 0).
- La columna **"OLS `K̃>0`"** es el modelo de dos partes.
- La columna **Log OLS** imprime el coeficiente crudo (los autores lo leen ×100 como porcentaje).
- Las **estrellas impresas** no salen del método correcto (los autores lo reconocen).
- El ZINB estático de los autores **no agrupa** por comuna: sus `***` no son comparables con el método declarado.

### 6.5 Tablas de apoyo (no están en el paper o reproducen cifras del texto)

| Archivo | Qué contiene | Cómo leerlo |
|---|---|---|
| `cameron_trivedi.csv` | Test de sobredispersión (dinámico y estático) | `dispersion` = 7,750; `paper` = 7,73; `abs_diff` 0,02 y su `limit` (1 %). El estático (7,494) no tiene contraparte impresa |
| `moran.csv` | Las 12 lecturas del I de Moran | Columnas `estilo` (W o B), `agregacion`, `rol` (**principal** = la lectura literal; el resto son sensibilidades), `moran_i`, `paper` y `etiqueta` (exacto, aproximado o no reproduce). Las principales dan 0,419 y 0,430 (**no reproduce**) |
| `zero_inflation.csv` y `zero_inflation_profile.csv` | Diagnóstico de π | `pi_hat` = 0, `en_frontera` = True, `lr` = 0 y `pvalue_frontera` = 1, con el IC del 95 %. El perfil muestra qué tan empinada es la verosimilitud: π = 0,001 ya queda rechazado (`lr` = 50 y 88) |
| `table2_mobility_seeds.csv` y `mobility_seeds_raw_km.csv` | Wasserstein con 200 semillas (resumen y valores crudos por semilla) | Ver 6.2 |
| `median_counts_check.csv` y `median_distance_check.csv` | Comprobación de que las medianas reconstruidas desde los archivos diarios son idénticas a las de la base del paper | `identical` = True en las 178.304 filas (`max_abs_diff` 0 en conteos y 3·10⁻¹¹ en distancia, ruido de punto flotante) |
| `fig1_scales.csv` | Extremos de la escala de color de la Fig. 1 | `ours_max` frente a `paper_max` y su cociente (0,9446 y 1,0105) |

### 6.6 Sensibilidad en hora local (`outputs/local_time/tables/`)

Esta es una tabla **nuestra**: no existe en el paper. Rehace las Tablas 4 y 5 con los camiones convertidos a la hora de `America/Santiago`, y la compara con la versión publicada **restringida a las mismas horas** (7 a 19, las únicas completas en hora local).

| Archivo | Qué contiene |
|---|---|
| `results_published_7_19_*.csv` y `results_local_7_19_*.csv` | Las Tablas 4 o 5 de cada versión, con valores, p-valores y estrellas |
| `comparison_*.csv` | Celda a celda: `base` (publicada 7–19), `alt` (local 7–19), cambio relativo y si cambió el signo o las estrellas |
| `comparison_summary_*.csv` | Resumen por columna |
| `fit_summary.csv` | Ajuste de cada versión (π̂ = 0 en las cuatro) |
| `robustness.csv` | Las 4 conclusiones del paper, evaluadas en tres versiones |

Resumen de la tabla dinámica (publicada 7–19 frente a local 7–19, 11 celdas por columna):

| Modelo | Cambios de signo | Cambios de estrellas | Cambio relativo mediano |
|---|---:|---:|---:|
| ZINB | 1 | 1 | 8 % |
| OLS | 1 | 1 | 12 % |
| OLS `K̃>0` | 1 | 2 | 9 % |
| Log OLS | 0 | 6 | 32 % |

En la tabla dinámica, todos los cambios de signo ocurren en celdas no significativas en ambas versiones. Las 4 conclusiones del paper (U invertida por GSE, pico en 25–34, hombres con signo opuesto en el estático, y C1b de positivo a negativo) se cumplen en las tablas impresas, en la publicada 7–19 y en la local 7–19 (`robustness.csv`). El modelo log es el más sensible al cambio de hora.

### 6.7 Cómo regenerarlas

```bash
python scripts/03_zinb_tables.py            # valores de las Tablas 4 y 5 (minutos)
python scripts/06_inference.py              # estrellas (minutos)
python scripts/17_paper_format_tables.py    # tablas lado a lado con el paper (segundos)
python scripts/16_run_all.py                # todo lo demás, con el informe de reproducción
```

---

## 7. Qué replicamos exacto, qué difiere y por qué

### 7.1 Replicado exactamente (o a la precisión impresa)

| Qué | Resultado | Cómo se comprueba |
|---|---|---|
| **Tabla 2** (medias, desviaciones y porcentajes) | Exacta | `scripts/01_table2.py` |
| **Tablas 4 y 5, columnas OLS** | Al 4.º decimal, en las 3 columnas × 2 tablas (diferencia máx. 5·10⁻⁵) | `02` y `03` |
| **Tablas 4 y 5, columna ZINB** | A la precisión impresa (diferencia máx. 5,7·10⁻⁵ y 4,4·10⁻⁵). Es la NB (π̂ = 0) | `03` |
| **Medianas de conteo** (42 miércoles) y de **distancia y tiempo** (41) | **Idénticas** en las 178.304 filas | `04`, `11` |
| **Estrellas** frente a las tablas regeneradas por los autores | **88/88** | `06` |
| **Test de Cameron–Trivedi** (sobredispersión) | 7,750 frente a 7,73 (0,26 %) | `08` |
| **Figs. 6, 8, 9 y 10** | Mismos puntos (≤ 1·10⁻⁴) | `14` |
| **Conclusión por conclusión** | Las 4 conclusiones predefinidas se mantienen en las tablas impresas, en la publicada restringida a 7–19 y en la de hora local | `13` |

**Por qué se replica tan bien:** se reprodujo **tal cual el paquete de los autores**, incluidas decisiones que el paper no describe (ver 7.3). Donde el paper y su código difieren, el código es lo que produjo las tablas.

### 7.2 No se reproduce exactamente

| Qué | Nuestro resultado | Por qué difiere |
|---|---|---|
| **Estrellas impresas** | 23/44 (Tabla 4) y 38/44 (Tabla 5) | Las impresas no salen del método correcto; los autores lo reconocen (5.2). Es un problema del original, no de la réplica |
| **I de Moran** (0,4694 y 0,4756) | 0,419 y 0,430 (lectura literal); 0,466 y 0,470 (promedio de mapas) | El paper **no define la matriz de pesos ni cómo promedia en el tiempo**, y el paquete no trae código. Probamos las lecturas directas y ninguna da el cuarto decimal. No se fuerza. Todas confirman correlación espacial positiva (I ≫ 0) |
| **Wasserstein** (movilidad, Tabla 2) | 13 de 15 valores dentro de la banda del 95 % de 200 semillas | Su script toma una **muestra aleatoria de 5.000 hexágonos sin semilla**: los valores impresos son **una sola extracción**. Lo reproducible son los extremos (hombre > mujer; 45–54 el más móvil y 65+ el menos; AB el más móvil y C1b el menos) |
| **Fig. 1, extremos de color** | 1.511 / 7.073 frente a 1600 / 7000 | Desconocido; hipótesis no probada (4.1) |
| **Fig. 2** | Sustituto rotulado | Falta el GPS crudo |
| **Fig. 7** | Reproduce las 12 etiquetas | Con factores derivados de ellas mismas (4.5) |

### 7.3 Dónde el paper (o su código) hace algo distinto de lo que dice, y qué hicimos

Estas son las diferencias **del original**, que importa distinguir de las nuestras:

| Qué | Qué ocurre | Qué hicimos | Hallazgo |
|---|---|---|---|
| **Hora UTC en los camiones frente a hora local en la población** | Al juntar las dos fuentes hay un desfase de 3 a 4 horas. Los autores lo reconocen (segundo error que admiten) | Replicamos tal cual **y** hicimos una sensibilidad en hora local: las 4 conclusiones se mantienen y los coeficientes cambian ~8–12 % en mediana; ningún cambio de signo afecta a un efecto significativo | H1, H33 |
| **Mediana solo sobre los días con camiones** | El paper dice mediana entre los miércoles; el código omite los días sin vehículos (no los cuenta como 0), lo que sesga hacia arriba | Replicamos el código; la variante "ausentes = 0" cambia el 41 % de las filas | H2 |
| **Distancia: recorte frente a descarte** | El paper (Fig. 5) recorta los tramos por hexágono; el código **descarta** los que cruzan hexágono u hora | Replicamos el código | H4 |
| **"OLS `K̃>0`" no es un OLS sobre positivos** | Es un modelo de dos partes | Lo replicamos así; un OLS simple da otras cifras (p. ej. C1b: 474,78 en vez de 388,32) | H7 |
| **La columna "ZINB" es la NB** | El ZINB colapsa en NB (π̂ = 0) | Se reporta el máximo de la verosimilitud | H23, H29 |
| **(1−π) aplicado dos veces** | Error del código en el efecto marginal; no afecta porque π̂ = 0 | Documentado; la sensibilidad usa la fórmula correcta | H10 |
| **Cluster `NULL` en el ZINB estático** | Ver 5.3 | Variantes `paper_text` y `authors_script` lado a lado | H26 |
| **Eje derecho reescalado** | Ver 4.4 | Replicado igual, con advertencia | H34 |
| **Cifra del 24 % de hombres** | Viene del modelo log (coef. leído como %) y deja de ser significativa | Documentada; los autores coinciden | H31, H32 |

### 7.4 Lo que agregamos nosotros (no está en el paper)

Para no confundirlo con la réplica: la **sensibilidad en hora local** (Fase 5), el **diagnóstico de π** (π̂ = 0, sin objetivo del paper), las **200 semillas** del Wasserstein, el **diagnóstico de las estrellas** con la base de 2 miércoles (aislado; no es una réplica), el **sustituto de la Fig. 2** y las **tablas lado a lado** (`scripts/17_paper_format_tables.py`).

---

## 8. Qué se puede y qué no se puede concluir

**Se puede decir:**

- Las celdas con más proporción de clase media (C1a a C3) y de 25–34 años tienden a tener **más actividad de reparto** que las de AB, D+E, menores de 25 y mayores de 65. Esto se mantiene al corregir la hora.
- Medir la población **presente** (dinámica) en lugar de la residencial **cambia** el diagnóstico en C1b y en sexo: es el argumento metodológico del paper.

**No se puede decir (el propio paper lo advierte en parte):**

- **Que una persona de C1b "recibe X gramos más"**: el análisis es **ecológico** (celdas, no individuos), **correlacional** (no causal) y mide **co-ocurrencia**, no concentraciones ni dosis (§4, §5.1, §6.2).
- Que los hombres están **24 % más expuestos**: no se sostiene.
- Que **todas las estrellas impresas** son correctas.
- Que la **magnitud entre las dos líneas** de una misma figura sea comparable (eje reescalado).
- Que la réplica es **independiente**: se parte de los datos intermedios de los autores; no tenemos el GPS crudo ni los datos de Entel.

Otras cautelas: SimpliRoute no cubre a todos los proveedores logísticos; el GSE es una probabilidad por zona de residencia; los datos son de miércoles de marzo a noviembre de 2024 en Santiago; con 51 comunas la inferencia por cluster es razonable pero gruesa.

---

## 9. Cómo explicarlo a alguien (guion)

**En una frase.** "Cruzamos dónde está la gente cada hora con dónde están los camiones de reparto y vimos qué grupos coinciden más con los camiones. La clase media, sobre todo los de 25 a 34 años, coincide más; y si se miran solo las residencias en vez de la gente presente de día, la conclusión cambia."

**En un minuto.**

1. *Qué se mide:* en cada hexágono de 400 m y cada hora, cuántos vehículos hay y cuántos metros recorren, y qué proporción de la población es de cada grupo.
2. *Qué se hace:* una regresión que pregunta si, cuando sube la proporción de un grupo, sube también el reparto, contra una categoría de referencia (el grupo AB, las mujeres, los mayores de 65).
3. *Qué se ve:* (Fig. 6) una U invertida por nivel socioeconómico; (Fig. 8) un pico a los 25–34 años; (Fig. 9) con demografía estática, C1b pasa de la cima al fondo.
4. *Qué significan las estrellas:* cuánta confianza hay en que el efecto no es ruido, descontando que hexágonos vecinos se parecen.
5. *Qué tenemos nosotros:* reproducimos los números exactos del paper; las estrellas impresas no salen, porque ni los autores las reproducen, y las que sí salen con su código coinciden 88/88 con las nuestras.

**Preguntas que probablemente te harán**

- *¿Por qué el eje derecho llega a 400 y el izquierdo a 2,8?* Porque no son comparables: el derecho se reescala para que los picos queden a la misma altura. Solo se comparan formas.
- *¿Qué es "0" en las figuras?* La categoría de referencia (AB o 65+), con la que se compara.
- *¿Por qué las figuras no tienen estrellas?* Muestran puntos; la significancia está en las tablas (y es la parte que se mantuvo con reservas).
- *¿Si la hora de los camiones estaba mal, no se cae todo?* No: la sensibilidad con la hora corregida mantiene las 4 conclusiones; los coeficientes cambian ~8–12 %.
- *¿Entonces el paper está mal?* Su conclusión cualitativa se sostiene; fallan tres cosas puntuales: las estrellas impresas, la cifra del 24 % para hombres y que la diferencia estática de C1b dependa de un cluster omitido.
- *¿La Fig. 7 mide emisiones?* No de forma independiente: son los metros de la Fig. 6 multiplicados por una constante.
- *¿Por qué se llama ZINB si la inflación de ceros es cero?* Porque ese es el modelo que describe el paper. Con estos datos la probabilidad de cero estructural estimada es 0 y el modelo equivale a una binomial negativa; el 29,6 % de ceros lo explica el azar del conteo (sección 3.2).
- *¿La columna "OLS `K̃>0`" es una regresión sobre las celdas con recorrido?* No: es un modelo de dos partes, que combina la probabilidad de que haya recorrido con cuántos metros hay si lo hay (sección 3.4).
- *¿Qué tabla abro para comparar con el paper?* `table4_vs_paper_paper_text.md` y `table5_vs_paper_authors_script.md` (y `table5_vs_paper_paper_text.md` para ver el cluster por comuna): réplica y paper lado a lado, con los valores iguales y las estrellas marcadas donde difieren (sección 6.4).
- *¿Los valores de la réplica coinciden con las tablas del paper?* Sí, en las 104 celdas de las Tablas 4 y 5, dentro del redondeo que imprime el paper. Lo que difiere son las estrellas impresas, que no salen del método correcto (secciones 5 y 6.4).

---

## 10. Dónde mirar cada cosa

| Quiero ver… | Archivo |
|---|---|
| Las figuras | `docs/figures/` (versionadas) y `outputs/as_published/figures/` (todas, con PDF) |
| Las tablas lado a lado con el paper | `outputs/as_published/tables/table4_vs_paper_paper_text.md`, `table5_vs_paper_paper_text.md`, `table5_vs_paper_authors_script.md` |
| Qué coincide y qué no, resumido | `outputs/reproduction/report.md` (publicado en `docs/reproduction_report.md`) |
| Si las conclusiones se sostienen | `docs/conclusiones.md` |
| Dónde está cada ecuación en el código | `docs/paper_map.md` |
| El detalle de cada hallazgo (H*, D*, O*) | `AGENTS.md`, §7 |
| Cómo está implementado cada modelo | `src/lastmile_exposure/models/` (`zinb.py`, `two_part.py`, `ols.py`, `marginal_effects.py`) y `inference/` |
| Las tablas de apoyo (Cameron–Trivedi, Moran, π, hora local) | `outputs/as_published/tables/` y `outputs/local_time/tables/` (sección 6.5 y 6.6) |
