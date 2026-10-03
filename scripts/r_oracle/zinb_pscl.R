# Contraste en R: ZINB con pscl::zeroinfl, replicando la ruta de los autores
# (summary_results_cluster.R / summary_results_static_cluster.R). Solo punto estimado.
lib <- Sys.getenv("R_LIBS_USER")
.libPaths(c(lib, .libPaths()))
suppressMessages(library(pscl))

args <- commandArgs(trailingOnly = TRUE)
root <- args[1]   # .../data/replication_package/00_data
out  <- args[2]   # carpeta de salida

vars <- c("genero_masc", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3", "gse_de",
          "edad_menor_25", "edad_25_34", "edad_35_44", "edad_45_54", "edad_55_64")
fml <- as.formula(paste("vehicles ~", paste(vars, collapse = " + "), "| 1"))

counts <- read.csv(file.path(root, "hexagon_model_median_wednesdays_RM.csv"), fileEncoding = "UTF-8")
counts$vehicles <- round(counts$median_vehicles, 0)       # round() de R: mitades al par

fit_and_report <- function(d, tag) {
  t0 <- Sys.time()
  m <- zeroinfl(fml, dist = "negbin", data = d)
  coefs <- coef(m, model = "count")
  zero_prob <- plogis(coef(m, model = "zero")[1])
  avg_fitted <- mean(predict(m, type = "response"), na.rm = TRUE)
  mu_mean <- mean(predict(m, type = "count"), na.rm = TRUE)
  res <- data.frame(
    variable = vars,
    coef = as.numeric(coefs[vars]),
    ame_authors = as.numeric(coefs[vars] * avg_fitted * (1 - zero_prob)),
    ame_eq4 = as.numeric(coefs[vars] * (1 - zero_prob) * mu_mean)
  )
  write.csv(res, file.path(out, paste0("pscl_", tag, "_coefs.csv")), row.names = FALSE)
  info <- data.frame(
    tag = tag, loglik = as.numeric(logLik(m)), theta = m$theta,
    zero_intercept = as.numeric(coef(m, model = "zero")[1]), zero_prob = as.numeric(zero_prob),
    count_intercept = as.numeric(coefs["(Intercept)"]), avg_fitted = avg_fitted, mu_mean = mu_mean,
    optim_convergence = m$optim$convergence, n_obs = m$n,
    seconds = as.numeric(difftime(Sys.time(), t0, units = "secs"))
  )
  write.csv(info, file.path(out, paste0("pscl_", tag, "_info.csv")), row.names = FALSE)
  print(info)
}

# --- dinamico: demografia por hora (como en el paquete)
dyn <- counts
dyn$gse_de <- dyn$gse_d + dyn$gse_e
fit_and_report(dyn, "dynamic")

# --- estatico: shares de datosxhexagono.csv (GSE / 100), merge por hex
st <- read.csv(file.path(root, "datosxhexagono.csv"), fileEncoding = "UTF-8")
for (g in c("gse_ab", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3", "gse_d", "gse_e")) st[[g]] <- st[[g]] / 100
st$gse_de <- st$gse_d + st$gse_e
stat <- merge(counts[, c("hex", "hour", "vehicles")], st, by = "hex", all.x = TRUE)
fit_and_report(stat, "static")
