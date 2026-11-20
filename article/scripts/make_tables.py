"""Gera article/tables/*.tex a partir dos CSV em reports/results/."""
from pathlib import Path

import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from enem_school.evaluation import compare_algorithms  # noqa: E402

RESULTS = ROOT / "reports" / "results"
TABLES = ROOT / "article" / "tables"


NAMES = {
    "Árvore": "Decision Tree", "Floresta": "Random Forest", "Baseline: média": "Baseline: mean",
    "Baseline: rede": "Baseline: network", "Linear A (com rede)": "Linear A (with network)",
    "Linear B (sem rede)": "Linear B (without network)",
    "Linear C (sem rede e sem merenda)": "Linear C (without network and school meals)",
}


def write(df, name, fmt="{:.2f}"):
    TABLES.mkdir(exist_ok=True)
    df = df.replace(NAMES)
    body = df.to_latex(index=False, float_format=fmt.format, escape=False)
    (TABLES / f"{name}.tex").write_text(body)
    print(f"article/tables/{name}.tex  ({len(df)} linhas)")


def mean_std(df, col):
    return df[(col, "mean")].map("{:.2f}".format) + " $\\pm$ " + df[(col, "std")].map("{:.2f}".format)


def summary_table(path):
    df = pd.read_csv(path, header=[0, 1], index_col=0).dropna(how="all")
    out = pd.DataFrame({"Model": df.index})
    for col, label in [("rmse", "RMSE"), ("mae", "MAE"), ("r2", "$R^2$")]:
        out[label] = mean_std(df, col).to_numpy()
    return out, df


spot, spot_raw = summary_table(RESULTS / "spot_checking_summary.csv")
spot["Train time (s)"] = spot_raw[("segundos_treino", "mean")].to_numpy()
write(spot, "spot_checking")

tuned = pd.read_csv(RESULTS / "otimizacao_summary.csv")
tuned = tuned.rename(columns={
    "algoritmo": "Model", "RMSE padrão": "RMSE default", "RMSE ajustado": "RMSE tuned",
    "desvio ajustado": "Std (tuned)", "R² padrão": "$R^2$ default",
    "R² ajustado": "$R^2$ tuned", "ganho (pontos)": "Gain (RMSE)",
})
write(tuned, "otimizacao", "{:.3f}")

folds = pd.read_csv(RESULTS / "interpretacao_variantes.csv")
agg = folds.groupby(["variante", "algoritmo"])[["rmse", "r2"]].agg(["mean", "std"])
variants = pd.DataFrame({"Variant": [v for v, _ in agg.index], "Model": [m for _, m in agg.index]})
variants["RMSE"] = mean_std(agg, "rmse").to_numpy()
variants["$R^2$"] = mean_std(agg, "r2").to_numpy()
write(variants, "variantes")

linear, _ = summary_table(RESULTS / "linear_regression_summary.csv")
write(linear, "linear_regression")


def cd_diagram(results, name, w=1.0):
    """Nemenyi critical-difference diagram (Demšar, 2006) as a TikZ picture; rank 1 on the left."""
    res = compare_algorithms(results)
    ranks, cd = res["ranks"], res["critical_difference"]
    ranks.index = ranks.index.map(lambda a: {**NAMES, "kNN": "$k$-NN"}.get(a, a))
    k, x = len(ranks), lambda r: round((r - 1) * w, 3)
    out = [f"\\begin{{tikzpicture}}[x=1cm,y=1cm,font=\\small]",
           f"\\draw (0,0) -- ({x(k)},0);"]
    for t in range(1, k + 1):
        out.append(f"\\draw ({x(t)},0) -- ({x(t)},0.1) node[above]{{{t}}};")
    out.append(f"\\draw[|-|,thick] (0,0.9) -- ({cd:.3f},0.9) node[midway,above]{{CD = {cd:.2f}}};")
    items = list(ranks.items())
    for i, (algo, r) in enumerate(items):
        left = i < k / 2
        y = -0.7 - 0.5 * (i if left else k - 1 - i)
        xe = -0.3 if left else x(k) + 0.3
        out.append(f"\\draw ({x(r)},0) -- ({x(r)},{y:.2f}) -- ({xe},{y:.2f}) "
                   f"node[{'left' if left else 'right'}]{{{algo} ({r:.2f})}};")
    # maximal groups of consecutive algorithms whose rank spread is below CD
    groups = {(i, max(j for j in range(i, k) if items[j][1] - items[i][1] < cd)) for i in range(k)}
    groups = [g for g in groups if g[1] > g[0] and not any(h != g and h[0] <= g[0] and g[1] <= h[1] for h in groups)]
    for level, (i, j) in enumerate(sorted(groups)):
        y = -0.15 - 0.15 * level
        out.append(f"\\draw[line width=1.6pt] ({round(x(items[i][1]) - 0.04, 2)},{y:.2f}) -- ({round(x(items[j][1]) + 0.04, 2)},{y:.2f});")
    out.append("\\end{tikzpicture}")
    TABLES.mkdir(exist_ok=True)
    (TABLES / f"{name}.tex").write_text("\n".join(out) + "\n")
    print(f"article/tables/{name}.tex  ranks={ranks.round(2).to_dict()} CD={cd:.3f} p={res['friedman_p']:.2e}")


spot_folds = pd.read_csv(RESULTS / "spot_checking.csv")
cd_diagram(spot_folds[spot_folds["algoritmo"] != "Baseline: média"], "cd_spot_checking")
