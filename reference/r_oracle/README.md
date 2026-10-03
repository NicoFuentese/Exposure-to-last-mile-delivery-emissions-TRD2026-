# Contraste en R (`pscl`) del ZINB

Parámetros del ZINB estimados con `pscl::zeroinfl` (la misma función que usa el código de los autores), para contrastar nuestro ZINB en Python. **No son cifras del paper**: son resultados nuestros sobre los datos confidenciales (14 parámetros por modelo, sin filas individuales).

| Archivo | Modelo |
|---|---|
| `zinb_pscl_dynamic.csv` | ZINB con demografía dinámica (Tabla 4) |
| `zinb_pscl_static.csv` | ZINB con demografía estática (Tabla 5) |

Formato: `name,value`.
- `inflate_const`: constante de la inflación (π = logística de este valor).
- `const` y los 11 regresores: coeficientes de la componente de conteo (log μ).
- `alpha`: dispersión en la parametrización de `statsmodels` (= 1/θ de `pscl`).
- `loglik`: log-verosimilitud que reporta `pscl` en su solución.
- `ame_authors:<regresor>`: efecto marginal con la fórmula del código de los autores.

**Origen:** `scripts/r_oracle/zinb_pscl.R`, ejecutado con R 4.6.1 y `pscl` 1.5.9 el 2026-10-03:

```bash
Rscript scripts/r_oracle/zinb_pscl.R data/replication_package/00_data <carpeta_de_salida>
```

Requiere `pscl` instalado en R (`install.packages("pscl")`). R solo se usa para este contraste; la réplica es Python.

**Qué muestran** (ver `AGENTS.md` §7, H21–H23): nuestra log-verosimilitud evaluada en estos parámetros coincide con la de R (mismo modelo), pero el máximo verdadero es algo más alto (`pscl` se detiene antes), y por eso ni R ni Python reproducen la columna ZINB del paper al 4.º decimal.
