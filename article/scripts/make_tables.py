"""Gera article/tables/*.tex a partir dos CSV em reports/results/."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
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
