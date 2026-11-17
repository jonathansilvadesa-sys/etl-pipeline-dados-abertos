"""
Extração da API de agregados do IBGE (SIDRA).

Documentação da API: https://servicodados.ibge.gov.br/api/docs/agregados?versao=3
"""

import logging
import time

import pandas as pd
import requests

from src.config import Indicador

log = logging.getLogger(__name__)

BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Só vale tentar de novo quando o erro é temporário:
# 429 = muitas requisições; 5xx = falha do servidor.
# Um 400 ou 404 vai falhar igual na próxima tentativa.
STATUS_COM_RETRY = {429, 500, 502, 503, 504}


class IBGEClient:
    """Cliente HTTP da API do IBGE com timeout e retry com backoff exponencial."""

    def __init__(self, max_tentativas: int = 3, timeout: int = 60, espera_base: float = 1.0,
                 session: requests.Session | None = None):
        self.max_tentativas = max_tentativas
        self.timeout = timeout
        self.espera_base = espera_base
        self.session = session or requests.Session()

    def get_json(self, url: str, params: dict | None = None) -> list:
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as erro:
                motivo = f"erro de conexão: {erro}"
            else:
                if resp.ok:
                    return resp.json()
                if resp.status_code not in STATUS_COM_RETRY:
                    resp.raise_for_status()
                motivo = f"HTTP {resp.status_code}"

            if tentativa == self.max_tentativas:
                raise ConnectionError(
                    f"IBGE indisponível após {self.max_tentativas} tentativas ({motivo}): {url}"
                )
            espera = self.espera_base * 2 ** (tentativa - 1)   # 1s, 2s, 4s...
            log.warning("Tentativa %d/%d falhou (%s). Nova tentativa em %.0fs.",
                        tentativa, self.max_tentativas, motivo, espera)
            time.sleep(espera)


def montar_periodos(indicador: Indicador, ano_inicio: int, ano_fim: int) -> str:
    """
    Intervalo de períodos no formato do SIDRA.
    A API devolve só os períodos que existem dentro do intervalo,
    então pedir até o fim do ano corrente é seguro.
    """
    if indicador.periodicidade == "mensal":
        return f"{ano_inicio}01-{ano_fim}12"
    if indicador.periodicidade == "trimestral":
        return f"{ano_inicio}01-{ano_fim}04"     # trimestre = AAAA0T
    if indicador.periodicidade == "anual":
        return f"{ano_inicio}-{ano_fim}"
    raise ValueError(f"Periodicidade desconhecida: {indicador.periodicidade}")


def extrair(indicador: Indicador, ano_inicio: int, ano_fim: int,
            client: IBGEClient | None = None) -> pd.DataFrame:
    """Baixa um indicador e devolve os dados brutos em formato tabular."""
    client = client or IBGEClient()
    periodos = montar_periodos(indicador, ano_inicio, ano_fim)
    url = f"{BASE_URL}/{indicador.tabela}/periodos/{periodos}/variaveis/{indicador.variavel}"
    params = {"localidades": f"{indicador.nivel}[all]"}

    log.info("Extraindo %s (tabela %d, períodos %s)", indicador.id, indicador.tabela, periodos)
    dados = client.get_json(url, params)
    df = parsear_resposta(dados)
    log.info("%s: %d registros extraídos", indicador.id, len(df))
    return df


def parsear_resposta(dados: list) -> pd.DataFrame:
    """
    Achata o JSON do SIDRA em uma linha por (localidade, período).

    Estrutura da resposta:
    [ {variavel, resultados: [ {series: [ {localidade, serie: {periodo: valor}} ]} ]} ]

    O valor fica como texto: a conversão (e o tratamento dos símbolos
    especiais do IBGE) é responsabilidade da etapa de transformação.
    """
    registros = [
        {
            "periodo": periodo,
            "cod_localidade": serie["localidade"]["id"],
            "localidade": serie["localidade"]["nome"],
            "nivel": serie["localidade"]["nivel"]["id"],
            "valor_bruto": valor,
        }
        for variavel in dados
        for resultado in variavel.get("resultados", [])
        for serie in resultado.get("series", [])
        for periodo, valor in serie["serie"].items()
    ]
    colunas = ["periodo", "cod_localidade", "localidade", "nivel", "valor_bruto"]
    return pd.DataFrame(registros, columns=colunas)
