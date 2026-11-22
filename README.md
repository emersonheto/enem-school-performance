# ENEM 2025 por escola — características estruturais e desempenho

Trabalho prático de CMP263 (PPGC/UFRGS, 2026/2). Grupo: Artur Mariano, Emerson Herrera e Yaser Husein. Ideia original de Artur Mariano.

**Pergunta:** as características estruturais de uma escola (infraestrutura, rede, localização, tamanho, docentes) predizem o desempenho médio dos seus alunos no ENEM 2025?

**Tarefa:** regressão. **Unidade de análise:** escola com pelo menos 10 candidatos presentes nas 4 provas. **Alvo:** `nota_media`, a média por escola da média das 5 notas (CN, CH, LC, MT, redação).

O código-fonte do artigo (template SBC, LaTeX) está em `article/`.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `src/enem_school/config.py` | Fontes, anos, limiar de alunos, lista de atributos e chaves de agrupamento |
| `src/enem_school/data.py` | Agregação por escola e cruzamento com o Censo |
| `src/enem_school/eda.py` | Resumos descritivos (faltantes, escala, correlações, inconsistências) |
| `src/enem_school/preprocessing.py` | Pré-processamento e dobras compartilhados por todos os modelos: `build_preprocessor`, `assign_folds` |
| `src/enem_school/evaluation.py` | Avaliação: `spot_check` (validação cruzada repetida), `nested_cv` (otimização com CV aninhada) e `compare_algorithms` (Friedman + Nemenyi) |
| `scripts/build_dataset.py` | Gera `data/processed/schools_enem2025_censo2024.parquet` e o `.json` de metadados |
| `scripts/eda.py` | Gera `reports/eda.md` e as figuras em `reports/figures/` |
| `reports/eda.md` | Análise exploratória com tabelas e figuras |
| `notebooks/01_regressao_linear.ipynb` | Regressão linear (variantes A/B/C e baselines) com validação cruzada agrupada por município |
| `notebooks/02_spot_checking.ipynb` | Spot-checking de 6 algoritmos com hiperparâmetros padrão (3×5 dobras por município), com teste de Friedman e pós-teste de Nemenyi |
| `notebooks/03_otimizacao.ipynb` | Otimização de hiperparâmetros com nested CV (3×5 dobras por município) da árvore, SVR, Floresta e Gradient Boosting, com Friedman e Nemenyi |
| `notebooks/04_interpretacao.ipynb` | Interpretação do Gradient Boosting ajustado: SHAP, variantes A/B/C (sem rede e sem merenda) e resíduos por rede e região |
| `reports/results/` | Métricas por dobra e resumo de cada modelo, gravadas pelos notebooks |
| `article/` | Código-fonte LaTeX do artigo (template SBC); as tabelas em `article/tables/` são geradas por `article/scripts/make_tables.py` |
| `tests/` | Testes do pipeline de dados e das regras de inconsistência |
| `data/` | Dados brutos e processados (fora do git) |

## Requisitos

- **Download:** o zip do ENEM 2025 tem cerca de 1 GB (o do Censo 2024, cerca de 34 MB). Em `data/raw/` ficam ≈ 1,1 GB; a tabela por escola (`data/processed/`) tem menos de 1 MB. No Colab, cada sessão nova baixa tudo de novo.
- **Memória:** o `RESULTADOS_2025.csv` é lido em blocos de 200 mil linhas (`read_enem_results`), sem carregar o arquivo inteiro. Não medimos o consumo de RAM.
- **Colab:** depois de instalar as versões fixadas de pandas/numpy, o Colab pode pedir para reiniciar a sessão; reinicie e execute tudo de novo.

## Reproduzir

Requisito: [`uv`](https://docs.astral.sh/uv/) (instala o Python 3.12 se faltar). A partir da raiz do repositório:

```bash
uv sync                                   # cria .venv com as versões exatas de uv.lock
uv run pytest                             # testes
uv run python scripts/build_dataset.py    # baixa os dados do INEP e gera a tabela por escola
uv run python scripts/eda.py              # gera reports/eda.md e as figuras
```

Na primeira execução, `build_dataset.py` baixa os microdados para `data/raw/` (o ENEM 2025 tem cerca de 1 GB); depois reaproveita os arquivos. O `.json` de metadados registra a URL e o SHA-256 de cada fonte, as contagens de cada etapa e as versões das bibliotecas.

Sem `uv`: `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

### Notebooks

```bash
uv sync --group notebooks                 # adiciona Jupyter ao .venv
uv run jupyter lab                        # abrir notebooks/ e rodar "Restart Kernel and Run All"
```

Todos os modelos usam o mesmo pré-processamento (`build_preprocessor`) e as mesmas 5 dobras por `CO_MUNICIPIO` (`assign_folds`, com `config.SEED`), ambos de `src/enem_school/preprocessing.py`, para que as métricas sejam comparáveis.

**Determinismo:** as sementes são fixas (`config.SEED = 42`; a repetição `r` da validação cruzada usa `42 + r`), então as métricas se reproduzem exatamente. Só os tempos de treino dependem do hardware.

### Notebooks no Colab

> **Não é preciso executar nada para ver os resultados:** os quatro notebooks estão salvos com todas as saídas (tabelas, figuras e testes) e podem ser lidos direto no GitHub; as métricas por dobra estão em `reports/results/`. Reexecutar é opcional e demora no Colab gratuito (poucos núcleos): o 02 levou ≈ 30 min e o 03 deve passar de 1 h.

Abra o notebook pelo GitHub e execute tudo: a primeira célula clona o repositório e instala `requirements.txt`. A tabela por escola (`data/processed/schools_enem2025_censo2024.parquet`, ≈ 800 KB) e seus metadados estão versionados no repositório, porque o servidor do INEP recusa downloads de fora do Brasil, como os do Colab; os notebooks conferem os SHA-256 dos arquivos de origem registrados nos metadados. Para regenerar a tabela a partir dos microdados, rode `build_dataset.py` numa máquina no Brasil. Rode na ordem 01 → 04. Os tempos abaixo são aproximados (Mac com 12 núcleos; o Colab gratuito tem menos núcleos e é mais lento).

| Ordem | Notebook | Saídas | Tempo | Depende de |
|---|---|---|---|---|
| 1 | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/emersonheto/enem-school-performance/blob/main/notebooks/01_regressao_linear.ipynb) `01_regressao_linear` | `reports/results/linear_regression_folds.csv`, `linear_regression_summary.csv`; `reports/figures/linreg_coefficients.png`, `linreg_residuals.png` | alguns minutos | só da tabela por escola |
| 2 | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/emersonheto/enem-school-performance/blob/main/notebooks/02_spot_checking.ipynb) `02_spot_checking` | `reports/results/spot_checking.csv`, `spot_checking_summary.csv`; `reports/figures/spot_checking_rmse.png` | ≈ 3 min (Mac) · ≈ 30 min (Colab) | só da tabela por escola |
| 3 | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/emersonheto/enem-school-performance/blob/main/notebooks/03_otimizacao.ipynb) `03_otimizacao` | `reports/results/otimizacao.csv`, `otimizacao_summary.csv` | ≈ 17 min (Mac, CV aninhada) · > 1 h no Colab (estimado) | **02** (lê `spot_checking_summary.csv`) |
| 4 | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/emersonheto/enem-school-performance/blob/main/notebooks/04_interpretacao.ipynb) `04_interpretacao` | `reports/results/shap_importance.csv`, `interpretacao_variantes.csv`; `reports/figures/shap_beeswarm.png`, `interpretacao_residuos.png` | ≈ 15 min (Mac) | só da tabela por escola (hiperparâmetros do Gradient Boosting fixos no código) |

Os notebooks gravam as saídas em `reports/` dentro do clone; no Colab, baixe-as antes de encerrar a sessão.

## Resultados esperados

Valores para conferir se a reprodução está correta (de `reports/results/` e `reports/eda.md`):

| Item | Valor |
|---|---|
| Escolas na análise | 23.374 |
| Baseline: média (RMSE) | 62,4 |
| Baseline: rede (RMSE) | 39,7 |
| Spot-checking, hiperparâmetros padrão (RMSE) | SVR 30,77; Floresta 30,99; Gradient Boosting 31,65 |
| Friedman (notebook 02) | p = 2,3e-14 |
| Gradient Boosting ajustado (notebook 03) | RMSE 30,63; R² 0,76 |

## Regenerar as tabelas do artigo

Depois de rodar os notebooks, a partir da raiz do repositório:

```bash
uv run --group notebooks python article/scripts/make_tables.py
```

O `uv run` simples falha por falta do `jinja2`, que só entra com o grupo `notebooks`.

## Fontes

- ENEM 2025 (microdados, `RESULTADOS_2025.csv`): <https://download.inep.gov.br/microdados/microdados_enem_2025.zip>
- Censo Escolar 2024 (`microdados_ed_basica_2024.csv`): <https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2024.zip>. O Censo 2025 ainda não foi publicado pelo INEP (conferido em 20/10/2026).
