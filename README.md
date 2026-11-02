# ENEM 2025 por escola — características estruturais e desempenho

Trabalho prático de CMP263 (PPGC/UFRGS, 2026/2). Grupo: Artur Mariano, Emerson Herrera e Yaser Husein. Ideia original de Artur Mariano.

**Pergunta:** as características estruturais de uma escola (infraestrutura, rede, localização, tamanho, docentes) predizem o desempenho médio dos seus alunos no ENEM 2025?

**Tarefa:** regressão (decidida pelo grupo em 20/10/2026). **Unidade de análise:** escola com pelo menos 10 candidatos presentes nas 4 provas. **Alvo:** `nota_media`, a média por escola da média das 5 notas (CN, CH, LC, MT, redação).

**Entrega:** código e artigo em 22/11/2026.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `src/enem_school/config.py` | Fontes, anos, limiar de alunos, lista de atributos e chaves de agrupamento |
| `src/enem_school/data.py` | Agregação por escola e cruzamento com o Censo |
| `src/enem_school/eda.py` | Resumos descritivos (faltantes, escala, correlações, inconsistências) |
| `scripts/build_dataset.py` | Gera `data/processed/schools_enem2025_censo2024.parquet` e o `.json` de metadados |
| `scripts/eda.py` | Gera `reports/eda.md` e as figuras em `reports/figures/` |
| `reports/eda.md` | Análise exploratória com tabelas e figuras |
| `notebooks/01_regressao_linear.ipynb` | Regressão linear (variantes A/B/C e baselines) com validação cruzada agrupada por município |
| `reports/results/` | Métricas por dobra e resumo de cada modelo, gravadas pelos notebooks |
| `tests/` | Testes do pipeline de dados e das regras de inconsistência |
| `data/` | Dados brutos e processados (fora do git) |

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

No Google Colab, abra o notebook pelo GitHub e execute tudo: a primeira célula clona o repositório, instala `requirements.txt` e, se a tabela não existir, roda `build_dataset.py`. Todos os modelos usam o mesmo pré-processamento (`build_preprocessor`) e as mesmas 5 dobras por `CO_MUNICIPIO` (`assign_folds`, com `config.SEED`), ambos de `src/enem_school/preprocessing.py`, para que as métricas sejam comparáveis.

## Fontes

- ENEM 2025 (microdados, `RESULTADOS_2025.csv`): <https://download.inep.gov.br/microdados/microdados_enem_2025.zip>
- Censo Escolar 2024 (`microdados_ed_basica_2024.csv`): <https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2024.zip>. O Censo 2025 ainda não foi publicado pelo INEP (conferido em 20/10/2026).
