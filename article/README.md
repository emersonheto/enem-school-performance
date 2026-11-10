# Artigo (template SBC, LaTeX)

Esqueleto do artigo do trabalho prático. As seções em `sections/` contêm só comentários `% TODO:` com o que deve ir em cada uma; o texto é escrito pelo grupo.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `main.tex` | Documento principal (template SBC, uma coluna, inglês) |
| `sections/` | Uma seção por arquivo, incluída com `\input` |
| `tables/` | Tabelas `.tex` **geradas** a partir de `../reports/results/*.csv` (não editar à mão) |
| `scripts/make_tables.py` | Gera as tabelas |
| `references.bib` | Referências (vazio por enquanto) |
| `sbc-template.sty`, `sbc.bst` | Arquivos do template SBC |

As figuras são lidas de `../reports/figures/` (via `\graphicspath`), sem cópia.

## Compilar

Com LaTeX instalado, a partir de `article/`:

```bash
latexmk -pdf main.tex
```

No Overleaf: envie a pasta `article/` e, dentro dela, a pasta `reports/figures/` (o `\graphicspath` também procura `reports/figures/` a partir da raiz do projeto).

## Regenerar as tabelas

Depois de rodar os notebooks (que atualizam `reports/results/`), a partir da raiz do repositório:

```bash
uv run --no-project --with pandas python article/scripts/make_tables.py
```

## Limite

Até 20 páginas, incluindo referências. Ainda não compilado: nenhum LaTeX foi testado no ambiente em que o esqueleto foi criado.
