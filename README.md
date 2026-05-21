# 🔄 ETL Pipeline — Dados Abertos Brasileiros

> Pipeline ETL completo em Python: extração de APIs públicas (IBGE/IPEA), transformação e enriquecimento com pandas, e carga em banco de dados PostgreSQL — pronto para consumo em dashboards Power BI.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=flat-square&logo=powerbi&logoColor=black)

---

## 🎯 Objetivo

Construir um pipeline ETL robusto e reproduzível que:
1. **Extrai** dados de APIs públicas (IBGE SIDRA, IPEA Data, dados.gov.br)
2. **Transforma** e padroniza os dados com pandas (limpeza, enriquecimento, tipagem)
3. **Carrega** em PostgreSQL seguindo modelagem dimensional (esquema estrela)
4. **Documenta** o processo para facilitar manutenção e expansão

---

## 🏗️ Arquitetura do Pipeline

```
┌─────────────────────────────────────────────────────┐
│                   EXTRAÇÃO (E)                       │
│  API IBGE SIDRA  │  IPEA Data API  │  CSV Gov.br     │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│                 TRANSFORMAÇÃO (T)                    │
│  Limpeza  │  Tipagem  │  Enriquecimento  │  Validação│
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│                    CARGA (L)                         │
│        PostgreSQL — Modelo Estrela (Star Schema)     │
│   fato_indicadores  │  dim_tempo  │  dim_localidade  │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│                    CONSUMO                           │
│       Power BI via DirectQuery / Import Mode         │
└─────────────────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
etl-pipeline-dados-abertos/
│
├── src/
│   ├── extract/
│   │   ├── ibge_api.py          # Extração IBGE SIDRA
│   │   ├── ipea_api.py          # Extração IPEA Data
│   │   └── base_extractor.py   # Classe base abstrata
│   │
│   ├── transform/
│   │   ├── limpeza.py           # Funções de limpeza e padronização
│   │   ├── enriquecimento.py    # Joins com tabelas de referência
│   │   └── validacao.py        # Testes de qualidade de dados
│   │
│   ├── load/
│   │   ├── database.py          # Conexão e operações no PostgreSQL
│   │   └── schema.sql          # DDL do banco (tabelas fato/dimensão)
│   │
│   └── pipeline.py             # Orquestrador principal do ETL
│
├── config/
│   ├── settings.py             # Configurações e constantes
│   └── .env.example            # Template de variáveis de ambiente
│
├── tests/
│   └── test_transformacoes.py  # Testes unitários
│
├── requirements.txt
└── README.md
```

---

## 📊 Dados Processados

| Fonte | Indicador | Granularidade | Volume |
|-------|-----------|---------------|--------|
| IBGE SIDRA (T8418) | IPCA mensal | Mensal / Nacional | ~360 linhas/ano |
| IBGE SIDRA (T6318) | Taxa de desemprego | Trimestral / UF | ~108 por trimestre |
| IPEA Data (PNAD) | Renda média domiciliar | Anual / Região | ~50 por ano |
| CAGED (dados.gov.br) | Empregos formais | Mensal / Município | ~5.500/mês |

---

## 🔧 Instalação e Uso

```bash
# Clone o repositório
git clone https://github.com/jonathansilvadesa-sys/etl-pipeline-dados-abertos
cd etl-pipeline-dados-abertos

# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp config/.env.example config/.env
# Edite .env com suas credenciais do PostgreSQL

# Execute o pipeline completo
python src/pipeline.py --source all --periodo 2024

# Ou execute etapas individuais
python src/pipeline.py --source ibge --etapa extract
python src/pipeline.py --source ibge --etapa transform
python src/pipeline.py --source ibge --etapa load
```

---

## 💻 Principais Trechos de Código

### Extração com retry e tratamento de erros

```python
# src/extract/ibge_api.py
import requests
import pandas as pd
from time import sleep
from typing import Optional

class IBGEExtractor:
    BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

    def extrair_ipca(self, periodos: str = "202201-202412") -> pd.DataFrame:
        """
        Extrai IPCA mensal da API SIDRA do IBGE.
        Tabela 1737 — IPCA acumulado mensal
        """
        url = f"{self.BASE_URL}/1737/periodos/{periodos}/variaveis/2266"
        params = {"localidades": "N1[all]", "classificacao": "315[7169]"}

        for tentativa in range(3):
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return self._parsear_resposta(resp.json())
            except requests.RequestException as e:
                print(f"Tentativa {tentativa+1}/3 falhou: {e}")
                sleep(2 ** tentativa)

        raise ConnectionError("Falha ao conectar com a API do IBGE após 3 tentativas")

    def _parsear_resposta(self, data: list) -> pd.DataFrame:
        registros = []
        for item in data[0].get("resultados", []):
            for serie in item.get("series", []):
                for periodo, valor in serie["serie"].items():
                    registros.append({
                        "periodo": periodo,
                        "localidade": serie["localidade"]["nome"],
                        "valor": float(valor) if valor != "..." else None
                    })
        return pd.DataFrame(registros)
```

### Transformação com validação de qualidade

```python
# src/transform/limpeza.py
import pandas as pd
import numpy as np

def limpar_ipca(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e padroniza o DataFrame do IPCA."""
    df = df.copy()

    # Converter período YYYYMM para date
    df["data_referencia"] = pd.to_datetime(df["periodo"], format="%Y%m")
    df["ano"] = df["data_referencia"].dt.year
    df["mes"] = df["data_referencia"].dt.month

    # Remover nulos e outliers
    df = df.dropna(subset=["valor"])
    df = df[df["valor"].between(-5, 30)]  # Limites razoáveis para IPCA mensal

    # Renomear e selecionar colunas
    df = df.rename(columns={"valor": "ipca_mensal_pct"})
    df = df[["data_referencia", "ano", "mes", "localidade", "ipca_mensal_pct"]]

    return df.sort_values("data_referencia").reset_index(drop=True)

def validar_dataframe(df: pd.DataFrame, nome: str) -> dict:
    """Retorna relatório de qualidade do DataFrame."""
    return {
        "nome": nome,
        "total_linhas": len(df),
        "nulos_por_coluna": df.isnull().sum().to_dict(),
        "duplicatas": df.duplicated().sum(),
        "periodo_min": df["data_referencia"].min() if "data_referencia" in df else None,
        "periodo_max": df["data_referencia"].max() if "data_referencia" in df else None
    }
```

---

## 📐 Modelo de Dados (Star Schema)

```sql
-- Tabela Fato
CREATE TABLE fato_indicadores (
    id              BIGSERIAL PRIMARY KEY,
    sk_tempo        INT REFERENCES dim_tempo(sk_tempo),
    sk_localidade   INT REFERENCES dim_localidade(sk_localidade),
    indicador       VARCHAR(100),
    valor           NUMERIC(12,4),
    unidade         VARCHAR(50),
    fonte           VARCHAR(100),
    dt_carga        TIMESTAMP DEFAULT NOW()
);

-- Dimensão Tempo
CREATE TABLE dim_tempo (
    sk_tempo        SERIAL PRIMARY KEY,
    data            DATE,
    ano             INT,
    mes             INT,
    trimestre       INT,
    semestre        INT,
    nome_mes        VARCHAR(20),
    is_feriado      BOOLEAN DEFAULT FALSE
);

-- Dimensão Localidade
CREATE TABLE dim_localidade (
    sk_localidade   SERIAL PRIMARY KEY,
    cod_ibge        VARCHAR(10),
    nome            VARCHAR(100),
    uf              CHAR(2),
    regiao          VARCHAR(20),
    tipo            VARCHAR(20)  -- 'municipio', 'estado', 'regiao', 'pais'
);
```

---

## 📌 Contexto Profissional

Este pipeline reflete diretamente minha experiência com ETL em ambiente corporativo:

- **Icatu Seguros**: ETLs integrando GR5 + Excel + Azure para análise jurídica
- **Ipiranga**: Pipelines de ingestão de dados para o ambiente de DataViz no Azure
- A arquitetura estrela aqui replicada é a mesma que usei para estruturar modelos de Analysis Services

---

## 📬 Contato

**Jonathan Silva de Sá** · [LinkedIn](https://linkedin.com/in/jonathan-de-sa) · jonathansilvadesa@gmail.com
