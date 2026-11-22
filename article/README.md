# Artigo (template SBC, LaTeX)

Artigo do trabalho prático (template SBC, uma coluna, inglês). O texto de cada seção está em `sections/`; a versão entregue foi compilada no Overleaf (14 páginas).

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `main.tex` | Documento principal (template SBC, uma coluna, inglês) |
| `sections/` | Uma seção por arquivo, incluída com `\input` |
| `tables/` | Tabelas `.tex` **geradas** a partir de `../reports/results/*.csv` (não editar à mão) |
| `scripts/make_tables.py` | Gera as tabelas |
| `references.bib` | Referências (BibTeX, estilo `sbc.bst`) |
| `sbc-template.sty`, `sbc.bst` | Arquivos do template SBC |

As figuras são lidas de `../reports/figures/` (via `\graphicspath`), sem cópia.

## Compilar

Com LaTeX instalado, a partir de `article/`:

```bash
latexmk -pdf main.tex
# ou, sem instalar o TeX Live inteiro: tectonic -X compile main.tex
```

No Overleaf: envie a pasta `article/` e, dentro dela, a pasta `reports/figures/` (o `\graphicspath` também procura `reports/figures/` a partir da raiz do projeto).

## Regenerar as tabelas

Depois de rodar os notebooks (que atualizam `reports/results/`), a partir da raiz do repositório:

```bash
uv run --group notebooks python article/scripts/make_tables.py
```

## Limite

Até 20 páginas, incluindo referências (o artigo tem 14). Compila no Overleaf (pdfLaTeX) e localmente com `tectonic -X compile main.tex`.
