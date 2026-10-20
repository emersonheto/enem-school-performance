"""Exploratory analysis of the school table: writes reports/eda.md and reports/figures/*.png.

Usage (from the repository root): uv run python scripts/eda.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enem_school import config  # noqa: E402
from enem_school import eda  # noqa: E402

FIGURES = config.REPORTS_DIR / "figures"
TARGET_LABEL = "Nota média da escola (ENEM 2025)"


def save(fig: plt.Figure, name: str) -> str:
    fig.tight_layout()
    fig.savefig(FIGURES / name, dpi=150)
    plt.close(fig)
    return f"figures/{name}"


def table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return df.to_markdown(floatfmt=floatfmt)


def plot_target(schools: pd.DataFrame, cutoff: float) -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(schools[eda.TARGET], bins=60, color="#4C72B0")
    ax.axvline(cutoff, color="#C44E52", linestyle="--", label=f"Quartil superior (≥ {cutoff:.1f})")
    ax.set(xlabel=TARGET_LABEL, ylabel="Escolas")
    ax.legend()
    return save(fig, "target_hist.png")


def plot_target_by(schools: pd.DataFrame, column: str, labels: dict[int, str], name: str, xlabel: str) -> str:
    order = eda.target_by(schools, column, labels).index
    groups = [schools.loc[schools[column].map(labels) == g, eda.TARGET] for g in order]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.boxplot(groups, tick_labels=order, showfliers=False)
    ax.set(xlabel=xlabel, ylabel=TARGET_LABEL)
    return save(fig, name)


def plot_count_features(schools: pd.DataFrame) -> str:
    fig, axes = plt.subplots(3, 3, figsize=(10, 8))
    for ax, column in zip(axes.flat, config.SIZE_FEATURES):
        values = schools[column]
        ax.hist(values[values != eda.INEP_EXTREME_VALUE].dropna(), bins=50, color="#55A868")
        ax.set_yscale("log")
        ax.set_title(column, fontsize=9)
    return save(fig, "count_features_hist.png")


def plot_correlations(corr: pd.Series) -> str:
    fig, ax = plt.subplots(figsize=(7, 10))
    ax.barh(corr.index, corr.to_numpy(), color=["#C44E52" if v < 0 else "#4C72B0" for v in corr])
    ax.set(xlabel=f"Spearman com {eda.TARGET}")
    ax.tick_params(axis="y", labelsize=7)
    return save(fig, "feature_target_spearman.png")


def plot_noise(noise: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(noise.index.astype(str), noise["desvio"], color="#8172B2")
    ax.set(xlabel="Candidatos da escola no ENEM", ylabel=f"Desvio-padrão de {eda.TARGET}")
    return save(fig, "target_std_by_school_size.png")


def main() -> int:
    schools = pd.read_parquet(config.SCHOOL_TABLE)
    metadata = json.loads(config.SCHOOL_TABLE_METADATA.read_text())
    FIGURES.mkdir(parents=True, exist_ok=True)

    target = schools[eda.TARGET]
    cutoff = target.quantile(0.75)
    missing = eda.missing_rates(schools)
    prevalence = eda.binary_prevalence(schools)
    counts = eda.count_feature_profile(schools)
    corr = eda.spearman_with_target(schools)
    pairs = eda.correlated_pairs(schools)
    noise = eda.noise_by_school_size(schools)
    inconsistencies = eda.find_inconsistencies(schools)
    by_dependencia = eda.target_by(schools, "TP_DEPENDENCIA", eda.DEPENDENCIA_LABELS)
    by_regiao = eda.target_by(schools, "CO_REGIAO", eda.REGIAO_LABELS)
    by_localizacao = eda.target_by(schools, "TP_LOCALIZACAO", eda.LOCALIZACAO_LABELS)
    near_constant = prevalence[(prevalence < 0.02) | (prevalence > 0.98)]

    figures = {
        "target": plot_target(schools, cutoff),
        "dependencia": plot_target_by(
            schools, "TP_DEPENDENCIA", eda.DEPENDENCIA_LABELS, "target_by_dependencia.png", "Rede"
        ),
        "regiao": plot_target_by(schools, "CO_REGIAO", eda.REGIAO_LABELS, "target_by_regiao.png", "Região"),
        "counts": plot_count_features(schools),
        "corr": plot_correlations(corr),
        "noise": plot_noise(noise),
    }

    lines = [
        "# EDA — tabela por escola (ENEM 2025 + Censo Escolar 2024)",
        "",
        "Gerado por `scripts/eda.py` a partir de `data/processed/schools_enem2025_censo2024.parquet`. "
        "Todos os números deste arquivo saem do script; a interpretação fica para o grupo.",
        "",
        "## Dados",
        "",
        f"- Escolas: **{len(schools):,}** ({metadata['joined_schools'] / metadata['enem_schools_above_threshold']:.1%} "
        f"das {metadata['enem_schools_above_threshold']:,} escolas com ≥ {metadata['min_students_per_school']} "
        "candidatos no ENEM).",
        f"- Candidatos válidos: {metadata['valid_candidates']:,}.",
        f"- Atributos: {len(config.FEATURES)}; chaves de agrupamento (não são atributos): {', '.join(config.GROUP_KEYS)}.",
        "",
        table(eda.feature_types().set_index("grupo")),
        "",
        "## Alvo",
        "",
        table(target.describe().to_frame().T, ".1f"),
        "",
        f"- Assimetria: {target.skew():.3f}.",
        f"- Quartil superior (alternativa de classificação): `{eda.TARGET}` ≥ {cutoff:.1f}, "
        f"{(target >= cutoff).mean():.1%} das escolas (desbalanceamento 1:3).",
        "",
        f"![Distribuição do alvo]({figures['target']})",
        "",
        "### Por rede (`TP_DEPENDENCIA`)",
        "",
        table(by_dependencia, ".1f"),
        "",
        f"![Alvo por rede]({figures['dependencia']})",
        "",
        "### Por região e localização",
        "",
        table(by_regiao, ".1f"),
        "",
        table(by_localizacao, ".1f"),
        "",
        f"![Alvo por região]({figures['regiao']})",
        "",
        "### Ruído da média por tamanho da escola",
        "",
        table(noise, ".1f"),
        "",
        f"![Desvio do alvo por tamanho]({figures['noise']})",
        "",
        "## Valores faltantes",
        "",
        f"- Atributos com algum faltante: {(missing > 0).sum()} de {len(missing)}; máximo {missing.max():.2%} "
        f"(`{missing.index[0]}`).",
        f"- Escolas com pelo menos um faltante: {schools[config.FEATURES].isna().any(axis=1).sum():,}.",
        "",
        table(missing[missing > 0].to_frame("faltantes"), ".4f"),
        "",
        "## Atributos binários (infraestrutura)",
        "",
        "Proporção de escolas com o recurso:",
        "",
        table(prevalence.to_frame("proporção"), ".3f"),
        "",
        f"- Quase constantes (< 2% ou > 98%): {', '.join(f'`{c}`' for c in near_constant.index) or 'nenhum'}.",
        "",
        "## Atributos de contagem (escala e outliers)",
        "",
        f"O Censo marca valores extremos com o código {eda.INEP_EXTREME_VALUE} (dicionário de dados: "
        '"registro com marcação de valor extremo"). Esses registros ficam fora das estatísticas de escala '
        "e são contados na coluna `marcados_88888`.",
        "",
        "Verificação contra as fontes originais (16/10/2026):",
        "",
        "- **Fonte oficial:** INEP, *Microdados do Censo Escolar da Educação Básica 2024*, Anexo I – Dicionário de "
        "Dados, aba `microdados_unidade_coleta`, linhas 215 (`QT_DESKTOP_ALUNO`) e 217 (`QT_COMP_PORTATIL_ALUNO`): "
        '"88888 - registro com marcação de valor extremo (valor superior ao limite máximo de 4 equipamentos para '
        'cada 3 matrículas - foram marcados apenas valores>3)". O zip usado é idêntico ao publicado pelo INEP '
        "(SHA-256 no `.json` de metadados).",
        "- **CSV completo do Censo (215.545 escolas):** o código aparece em 26 colunas `QT_` (computadores, "
        "equipamentos e profissionais) e nenhum outro valor chega a 10.000; as escolas marcadas são pequenas "
        "(mediana de 12 a 19 matrículas).",
        "- **Limitação:** o limite de 4 equipamentos para cada 3 matrículas não se reproduz com as colunas "
        "públicas: entre 17 e 42 escolas sem marca (conforme a contagem de matrículas usada) ficam acima dele. "
        "Ou seja, nem todo valor extremo está marcado.",
        "- **Tratamento:** decisão do grupo (faltante com imputação, ou faltante + indicador binário de valor "
        "extremo marcado).",
        "",
        table(counts.set_index("atributo"), ".2f"),
        "",
        f"![Distribuição das contagens]({figures['counts']})",
        "",
        "## Correlação com o alvo (Spearman)",
        "",
        table(corr.to_frame("spearman"), ".3f"),
        "",
        f"![Correlação com o alvo]({figures['corr']})",
        "",
        "### Pares de atributos muito correlacionados (|Spearman| ≥ 0,8)",
        "",
        table(pairs.set_index(["a", "b"])) if len(pairs) else "Nenhum.",
        "",
        "## Inconsistências",
        "",
        table(inconsistencies.set_index("rule")),
        "",
    ]
    report = config.REPORTS_DIR / "eda.md"
    report.write_text("\n".join(lines))
    print(f"Wrote {report} and {len(figures)} figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
