"""Genera las tablas .tex de la presentación a partir de los resultados de la réplica.

Lee `outputs/as_published/tables/` y `reference/paper_tables/` (solo cifras agregadas: coeficientes,
medias, I de Moran; nada por fila ni por hexágono) y escribe `tablas/*.tex` junto a este archivo.
Antes hay que haber corrido los scripts 01, 03, 06, 09, 12 y 17 (ver el README del repositorio).

Uso, desde la raíz del repositorio:
    .venv/Scripts/python.exe entregables/replica_vs_paper/generar_tablas.py
"""

import pathlib
import re
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "tablas"
TABLES = ROOT / "outputs" / "as_published" / "tables"
REFERENCE = ROOT / "reference" / "paper_tables"

STAR = re.compile(r"^(-?\d+(?:\.\d+)?)(\*+|\.)?$")
MODELS = {
    "zinb": "ZINB",
    "ols_k": "OLS",
    "ols_kpos": r"OLS $\tilde K>0$",
    "ols_logk": r"Log OLS",
}


def num(value, decimals=2):
    text = f"{value:.{decimals}f}".replace(".", ",")
    return text.replace("-", "$-$")


def cell(raw, mark=False):
    """`3.5569***` -> `3,5569$^{***}$`; la cruz marca estrellas distintas de las impresas."""
    match = STAR.match(str(raw).strip())
    if match is None:
        return str(raw)
    value, stars = match.group(1), match.group(2) or ""
    out = value.replace(".", ",").replace("-", "$-$")
    sup = r"\cdot" if stars == "." else stars
    if mark:
        sup += r"\,\dagger"
    return out + (f"$^{{{sup}}}$" if sup else "")


def write(name, body):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(body, encoding="utf-8")
    print("escrito", name)


def table2():
    ours = pd.read_csv(TABLES / "table2.csv")
    paper = pd.read_csv(REFERENCE / "table2_floating_population.csv")
    both = ours.merge(paper, on=["variable", "group"], suffixes=("_r", "_p"))
    rows = []
    for _, r in both.iterrows():
        rows.append(
            f"{r['variable']} & {num(r['mean_r'])} & {num(r['mean_p'])} & "
            f"{num(r['std_r'])} & {num(r['std_p'])} \\\\"
        )
    head = (
        "\\begin{tabular}{lrrrr}\\toprule\n"
        " & \\multicolumn{2}{c}{Media} & \\multicolumn{2}{c}{Desviación} \\\\\n"
        "Variable & Réplica & Paper & Réplica & Paper \\\\\\midrule\n"
    )
    write("t2_mean_std.tex", head + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")

    pct = both.dropna(subset=["mean_pct_r"])
    rows = [
        f"{r['variable']} & {num(r['mean_pct_r'], 1)} & {num(r['mean_pct_p'], 1)} & "
        f"{num(r['std_pct_r'], 1)} & {num(r['std_pct_p'], 1)} \\\\"
        for _, r in pct.iterrows()
    ]
    head = (
        "\\begin{tabular}{lrrrr}\\toprule\n"
        " & \\multicolumn{2}{c}{Media (\\%)} & \\multicolumn{2}{c}{Desviación (\\%)} \\\\\n"
        "Variable & Réplica & Paper & Réplica & Paper \\\\\\midrule\n"
    )
    write("t2_pct.tex", head + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")


def wasserstein():
    df = pd.read_csv(TABLES / "table2_mobility_seeds.csv")

    def block(sub):
        rows = []
        for _, r in sub.iterrows():
            inside = "sí" if r["inside_band"] else "\\textbf{no}"
            rows.append(
                f"{r['group']} & {num(r['published'], 3)} & {num(r['seed_median'], 3)} & "
                f"{num(r['band_low'], 3)}--{num(r['band_high'], 3)} & {inside} \\\\"
            )
        head = (
            "\\begin{tabular}{lrrcc}\\toprule\n"
            "Grupo & Impreso & Mediana & Banda 95\\,\\% & ¿Dentro? \\\\\\midrule\n"
        )
        return head + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n"

    gse = ["AB", "C1a", "C1b", "C2", "C3", "D", "E"]
    write("wasserstein_sexo_edad.tex", block(df[~df["group"].isin(gse)]))
    write("wasserstein_gse.tex", block(df[df["group"].isin(gse)]))


def effects(name, csv, columns, title):
    df = pd.read_csv(csv, dtype=str, keep_default_na=False)
    df = df[~df["label"].isin(["65+", "AB"])]
    spec = "l" + "rr" * len(columns)
    head = f"\\begin{{tabular}}{{{spec}}}\\toprule\n"
    head += (
        " & " + " & ".join(f"\\multicolumn{{2}}{{c}}{{{MODELS[c]}}}" for c in columns) + " \\\\\n"
    )
    head += "Variable" + " & Réplica & Paper" * len(columns) + " \\\\\\midrule\n"
    rows = []
    for _, r in df.iterrows():
        parts = [r["label"]]
        for c in columns:
            parts.append(cell(r[f"{c}_replica"], mark=r[f"{c}_stars_ok"] == "False"))
            parts.append(cell(r[f"{c}_paper"]))
        rows.append(" & ".join(parts) + " \\\\")
    write(name, head + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")


def moran():
    df = pd.read_csv(TABLES / "moran.csv")
    style = {"W": "W", "B": "B"}
    agg = {
        "mean_of_hourly": "promedio de las 16 I horarias",
        "stacked": "horas apiladas",
        "mean_map": "mapa promediado entre horas",
    }
    rows = []
    for (e, a), sub in df.groupby(["estilo", "agregacion"], sort=False):
        d = sub[sub["variable"] == "distancia"].iloc[0]
        v = sub[sub["variable"] == "vehiculos"].iloc[0]
        label = f"{agg[a]} ({style[e]})"
        line = f"{label} & {num(d['moran_i'], 3)} & {num(v['moran_i'], 3)} \\\\"
        if d["rol"] == "principal":
            bold = [f"\\textbf{{{x}}}" for x in (label, num(d["moran_i"], 3), num(v["moran_i"], 3))]
            line = " & ".join(bold) + " \\\\"
        rows.append(line)
    paper = df.iloc[0]["paper"], df[df["variable"] == "vehiculos"].iloc[0]["paper"]
    head = (
        "\\begin{tabular}{lrr}\\toprule\n"
        "Lectura (anillo 1 de H3) & Distancia & Vehículos \\\\\\midrule\n"
    )
    foot = (
        f"\\midrule\n\\textbf{{Paper}} & \\textbf{{{num(paper[0], 4)}}} & "
        f"\\textbf{{{num(paper[1], 4)}}} \\\\\n\\bottomrule\\end{{tabular}}\n"
    )
    write("moran.tex", head + "\n".join(rows) + "\n" + foot)


def main():
    missing = [
        p
        for p in (
            TABLES / "table2.csv",
            TABLES / "table4_vs_paper_paper_text.csv",
            TABLES / "table5_vs_paper_authors_script.csv",
            TABLES / "moran.csv",
            TABLES / "table2_mobility_seeds.csv",
        )
        if not p.exists()
    ]
    if missing:
        print("faltan resultados de la réplica:", *[m.name for m in missing], sep="\n  ")
        sys.exit(2)
    table2()
    wasserstein()
    effects("t4_a.tex", TABLES / "table4_vs_paper_paper_text.csv", ["zinb", "ols_k"], "4")
    effects("t4_b.tex", TABLES / "table4_vs_paper_paper_text.csv", ["ols_kpos", "ols_logk"], "4")
    effects("t5_a.tex", TABLES / "table5_vs_paper_authors_script.csv", ["zinb", "ols_k"], "5")
    effects(
        "t5_b.tex", TABLES / "table5_vs_paper_authors_script.csv", ["ols_kpos", "ols_logk"], "5"
    )
    moran()


if __name__ == "__main__":
    main()
