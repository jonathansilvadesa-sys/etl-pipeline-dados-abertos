"""
IBGE SIDRA API Extractor
========================
Extrai dados das APIs públicas do IBGE (Sistema IBGE de Recuperação Automática).

Documentação da API: https://servicodados.ibge.gov.br/api/docs/agregados
Autor: Jonathan Silva de Sá
"""

import requests
import pandas as pd
from time import sleep
from datetime import datetime
from typing import Optional


class IBGEExtractor:
    """Extrator de dados da API SIDRA do IBGE com retry automático."""

    BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

    def __init__(self, max_retries: int = 3, timeout: int = 30):
        self.max_retries = max_retries
        self.timeout = timeout

    # ──────────────────────────────────────────────
    # IPCA — Índice Nacional de Preços ao Consumidor
    # Tabela 1737 | Variável 2266
    # ──────────────────────────────────────────────
    def extrair_ipca(self, ano_inicio: int = 2020, ano_fim: Optional[int] = None) -> pd.DataFrame:
        """
        Extrai IPCA mensal acumulado no mês (variação %).
        Retorna DataFrame com: periodo, localidade, ipca_pct
        """
        if ano_fim is None:
            ano_fim = datetime.now().year

        periodos = f"{ano_inicio}01-{ano_fim}12"
        url = f"{self.BASE_URL}/1737/periodos/{periodos}/variaveis/2266"
        params = {
            "localidades": "N1[all]",
            "classificacao": "315[7169]"
        }

        data = self._get_com_retry(url, params)
        return self._parsear_series(data, "ipca_pct")

    # ──────────────────────────────────────────────
    # PIB Municipal — Tabela 5938
    # ──────────────────────────────────────────────
    def extrair_pib_municipal(self, ano: int = 2021) -> pd.DataFrame:
        """
        Extrai PIB per capita dos municípios brasileiros.
        Retorna DataFrame com: cod_municipio, nome, pib_per_capita
        """
        url = f"{self.BASE_URL}/5938/periodos/{ano}/variaveis/37"
        params = {"localidades": "N6[all]"}

        data = self._get_com_retry(url, params)
        return self._parsear_municipios(data)

    # ──────────────────────────────────────────────
    # Taxa de Desemprego — Tabela 6318 (PNADC)
    # ──────────────────────────────────────────────
    def extrair_desemprego(self, periodos: str = "20221-20244") -> pd.DataFrame:
        """
        Extrai taxa de desemprego trimestral por UF (PNADC).
        Formato de período: YYYYT (ex: 20221 = 1º tri 2022)
        """
        url = f"{self.BASE_URL}/6318/periodos/{periodos}/variaveis/4099"
        params = {"localidades": "N3[all]"}  # N3 = estados

        data = self._get_com_retry(url, params)
        return self._parsear_series(data, "taxa_desemprego_pct")

    # ──────────────────────────────────────────────
    # MÉTODOS PRIVADOS
    # ──────────────────────────────────────────────
    def _get_com_retry(self, url: str, params: dict) -> list:
        """Realiza GET com retry exponencial."""
        for tentativa in range(self.max_retries):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                print(f"[IBGE] HTTP {e.response.status_code} — tentativa {tentativa+1}/{self.max_retries}")
            except requests.RequestException as e:
                print(f"[IBGE] Erro de conexão: {e} — tentativa {tentativa+1}/{self.max_retries}")

            if tentativa < self.max_retries - 1:
                sleep(2 ** tentativa)

        raise ConnectionError(f"Falha ao conectar com IBGE após {self.max_retries} tentativas: {url}")

    def _parsear_series(self, data: list, col_valor: str) -> pd.DataFrame:
        """Parseia resposta padrão de séries temporais da API SIDRA."""
        registros = []
        for bloco in data:
            for resultado in bloco.get("resultados", []):
                for serie in resultado.get("series", []):
                    localidade = serie["localidade"]["nome"]
                    cod_localidade = serie["localidade"]["id"]
                    for periodo, valor in serie["serie"].items():
                        registros.append({
                            "periodo": periodo,
                            "cod_localidade": cod_localidade,
                            "localidade": localidade,
                            col_valor: float(valor) if valor not in ("...", "-", "") else None
                        })

        df = pd.DataFrame(registros)
        print(f"[IBGE] {len(df):,} registros extraídos para '{col_valor}'")
        return df

    def _parsear_municipios(self, data: list) -> pd.DataFrame:
        """Parseia resposta de dados municipais."""
        registros = []
        for bloco in data:
            for resultado in bloco.get("resultados", []):
                for serie in resultado.get("series", []):
                    for periodo, valor in serie["serie"].items():
                        registros.append({
                            "periodo": periodo,
                            "cod_municipio": serie["localidade"]["id"],
                            "nome_municipio": serie["localidade"]["nome"],
                            "pib_per_capita": float(valor) if valor not in ("...", "-", "") else None
                        })

        df = pd.DataFrame(registros)
        # Extrai código do estado a partir do código IBGE do município
        df["cod_uf"] = df["cod_municipio"].str[:2]
        print(f"[IBGE] {len(df):,} municípios extraídos")
        return df


# ──────────────────────────────────────────────
# USO DIRETO (teste rápido)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    extractor = IBGEExtractor()

    print("Extraindo IPCA 2022-2024...")
    df_ipca = extractor.extrair_ipca(2022, 2024)
    print(df_ipca.head(10))
    print(f"Shape: {df_ipca.shape}\n")

    print("Extraindo desemprego por estado (2023-2024)...")
    df_desemp = extractor.extrair_desemprego("20231-20244")
    print(df_desemp.head(10))
    print(f"Shape: {df_desemp.shape}")
