# 🔄 ETL Pipeline — Dados Abertos Brasileiros

> Pipeline em Python para extrair indicadores públicos do IBGE, tratar com pandas e carregar em banco analítico para consumo no Power BI. **Em desenvolvimento:** a etapa de extração está implementada; transformação e carga estão no roteiro abaixo.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)

---

## 🎯 Objetivo

Construir um pipeline reproduzível que:

1. **Extrai** séries da API de agregados do IBGE (SIDRA)
2. **Transforma** e valida os dados com pandas
3. **Carrega** em um modelo estrela pronto para o Power BI

---

## ✅ O que já funciona: extração

`src/extract/ibge_api.py` contém a classe `IBGEExtractor`, com três métodos:

| Método | Indicador | Recorte |
|--------|-----------|---------|
| `extrair_ipca` | IPCA mensal | Brasil |
| `extrair_desemprego` | Taxa de desocupação (PNAD Contínua) | Trimestral, por UF |
| `extrair_pib_municipal` | PIB dos municípios | Anual, por município |

Como funciona:

- **Retry com backoff exponencial:** se a API falhar, tenta de novo após 1s, 2s e 4s antes de desistir.
- **Timeout** em toda requisição, para o pipeline não travar esperando a API.
- **Parser do JSON do SIDRA:** achata a resposta aninhada (resultados → séries → período: valor) em um DataFrame, tratando os marcadores de dado ausente (`...` e `-`) como nulo.

---

## ▶️ Como executar

```bash
git clone https://github.com/jonathansilvadesa-sys/etl-pipeline-dados-abertos
cd etl-pipeline-dados-abertos

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Teste rápido: extrai IPCA e desemprego e mostra as primeiras linhas
python src/extract/ibge_api.py
```

---

## 📁 Estrutura

```
etl-pipeline-dados-abertos/
├── src/
│   └── extract/
│       └── ibge_api.py     # Extrator da API do IBGE
├── requirements.txt
└── README.md
```

---

## 🚧 Próximos passos

- [ ] `src/transform/`: limpeza, tipagem e checagens de qualidade (nulos, duplicatas, faixas válidas)
- [ ] `src/load/`: carga em DuckDB em modelo estrela (`fato_indicadores`, `dim_tempo`, `dim_localidade`)
- [ ] `pipeline.py`: orquestrador com argumentos de linha de comando e logging
- [ ] Testes com pytest usando respostas da API salvas em arquivo
- [ ] GitHub Actions rodando os testes a cada push

---

## 📌 Contexto profissional

- **Icatu Seguros:** ETLs integrando GR5, Excel e Azure para análise jurídica
- **Ipiranga:** ingestão de dados para o ambiente de DataViz no Azure
- **Grupo Dupla:** launcher em Python com bots de extração e tratamento de dados de várias fontes

---

## 📬 Contato

**Jonathan Silva de Sá** · [LinkedIn](https://linkedin.com/in/jonathan-de-sa) · jonathansilvadesa@gmail.com
