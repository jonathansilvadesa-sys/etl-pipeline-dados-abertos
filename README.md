# 🔄 ETL Pipeline — Dados Abertos Brasileiros

> Pipeline em Python que extrai indicadores públicos da API do IBGE, valida a qualidade dos dados e carrega um modelo estrela em DuckDB, pronto para consumo no Power BI.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=flat-square&logo=duckdb&logoColor=black)
[![testes](https://github.com/jonathansilvadesa-sys/etl-pipeline-dados-abertos/actions/workflows/testes.yml/badge.svg)](https://github.com/jonathansilvadesa-sys/etl-pipeline-dados-abertos/actions/workflows/testes.yml)

---

## ▶️ Como executar

```bash
git clone https://github.com/jonathansilvadesa-sys/etl-pipeline-dados-abertos && cd etl-pipeline-dados-abertos
pip install -r requirements.txt
python -m src.pipeline --exportar-csv data/export
```

O banco fica em `data/indicadores.duckdb` e os CSVs (separador `;`) em `data/export/`, prontos para importar no Power BI.

Outras opções:

```bash
python -m src.pipeline --indicadores ipca desocupacao --inicio 2022   # só alguns indicadores
python -m src.pipeline --help                                         # todas as opções
```

---

## 📊 Indicadores

| Indicador | Tabela SIDRA | Periodicidade | Recorte | Unidade |
|-----------|--------------|---------------|---------|---------|
| IPCA — variação mensal | [1737](https://sidra.ibge.gov.br/tabela/1737), variável 63 | Mensal | Brasil | % |
| Taxa de desocupação (PNAD Contínua) | [4099](https://sidra.ibge.gov.br/tabela/4099), variável 4099 | Trimestral | UF | % |
| PIB a preços correntes | [5938](https://sidra.ibge.gov.br/tabela/5938), variável 37 | Anual | Município | R$ mil |

Novos indicadores entram adicionando uma linha em `src/config.py`.

---

## 🏗️ Como funciona

```
API do IBGE ──► extract ──► transform ──► validação ──► load (DuckDB) ──► CSV / Power BI
                 retry       datas e       duplicatas,    modelo estrela,
                 timeout     símbolos      faixa, vazio   idempotente
```

**Extração** (`src/extract/ibge_api.py`)
- Monta a URL da API de agregados a partir da tabela, variável, nível territorial e períodos.
- Retry com backoff exponencial (1s, 2s, 4s) só em erros temporários: 429 e 5xx. Um erro 404 falharia igual na próxima tentativa, então falha na hora.
- Achata o JSON aninhado do SIDRA em uma linha por localidade e período.

**Transformação** (`src/transform/limpeza.py`)
- Converte o código de período em data: `202403` → mar/2024, `202402` trimestral → abr/2024, `2021` → jan/2021.
- Trata os símbolos do IBGE: `-` significa **zero**; `..`, `...` e `X` significam dado ausente.

**Validação** (`src/transform/validacao.py`)
- Interrompe a carga se houver duplicatas na chave, resultado vazio ou valores fora da faixa esperada. Melhor não atualizar o banco do que gravar um dado errado no dashboard.
- Um indicador com falha não impede a carga dos outros; o pipeline termina com código de erro para o agendador perceber.

**Carga** (`src/load/`)
- Modelo estrela em DuckDB: um banco analítico em arquivo único, sem servidor.
- Idempotente: a chave primária da fato faz o `INSERT OR REPLACE` atualizar o que existe e inserir o que é novo. Rodar duas vezes não duplica nada.

---

## 📐 Modelo de dados

```
dim_indicador ──┐
                │
dim_localidade ─┼── fato_indicadores (id_indicador, cod_localidade, data_referencia, valor)
                │
dim_tempo ──────┘
```

| Tabela | Grão | Destaques |
|--------|------|-----------|
| `fato_indicadores` | Indicador × localidade × período | Chave primária composta, data da carga |
| `dim_indicador` | Indicador | Nome, unidade, periodicidade e códigos do SIDRA |
| `dim_localidade` | Código IBGE | Nível (Brasil, UF, Município) e código da UF, para filtrar municípios por estado |
| `dim_tempo` | Mês | Ano, trimestre, mês e `ano_mes` |

DDL completo em [`src/load/schema.sql`](src/load/schema.sql).

---

## ✅ Testes

```bash
pip install -r requirements-dev.txt
pytest -v
```

- 30 testes que rodam sem internet, usando respostas reais da API salvas em `tests/fixtures/`.
- Cobrem o parser, o retry, a conversão de períodos e símbolos, as regras de validação e o pipeline de ponta a ponta (incluindo idempotência).
- No GitHub Actions, cada push roda os testes e, em seguida, o pipeline de verdade contra a API do IBGE.

---

## 📁 Estrutura

```
etl-pipeline-dados-abertos/
├── src/
│   ├── config.py               # catálogo de indicadores
│   ├── pipeline.py             # orquestrador (linha de comando)
│   ├── extract/ibge_api.py     # cliente da API e parser
│   ├── transform/
│   │   ├── limpeza.py          # datas, símbolos e tipagem
│   │   └── validacao.py        # checagens de qualidade
│   └── load/
│       ├── schema.sql          # modelo estrela
│       └── duckdb_loader.py    # carga e exportação
├── tests/                      # pytest + respostas reais da API
├── .github/workflows/          # CI
├── requirements.txt
└── requirements-dev.txt
```

---

## 📌 Contexto profissional

- **Icatu Seguros:** ETLs integrando GR5, Excel e Azure para análise jurídica
- **Ipiranga:** ingestão de dados para o ambiente de DataViz no Azure
- **Grupo Dupla:** launcher em Python com bots de extração e tratamento de dados de várias fontes

---

## 📬 Contato

**Jonathan Silva de Sá** · [LinkedIn](https://linkedin.com/in/jonathan-de-sa) · jonathansilvadesa@gmail.com
