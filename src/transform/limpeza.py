"""
Transformação: converte os dados brutos do SIDRA em registros tipados,
com data de referência e valor numérico.
"""

import logging

import pandas as pd

from src.config import NOMES_NIVEL, Indicador

log = logging.getLogger(__name__)

# Símbolos especiais que o IBGE usa no lugar de números:
#   "-"   valor numérico igual a zero, não resultante de arredondamento
#   ".."  não se aplica
#   "..." valor não disponível
#   "X"   valor omitido para não identificar o informante
# Atenção: "-" é ZERO, não ausência de dado.
SIMBOLOS_ZERO = {"-"}
SIMBOLOS_NULOS = {"..", "...", "X", ""}


def converter_valor(valor_bruto: str | None) -> float | None:
    if valor_bruto is None:
        return None
    texto = str(valor_bruto).strip()
    if texto in SIMBOLOS_ZERO:
        return 0.0
    if texto in SIMBOLOS_NULOS:
        return None
    return float(texto)


def periodo_para_data(periodo: str, periodicidade: str) -> pd.Timestamp:
    """
    Converte o código de período do SIDRA no primeiro dia do período.
      mensal      202403 -> 2024-03-01
      trimestral  202402 -> 2024-04-01 (2º trimestre, formato AAAA0T)
      anual       2021   -> 2021-01-01
    """
    p = str(periodo)
    if periodicidade == "mensal" and len(p) == 6:
        return pd.Timestamp(int(p[:4]), int(p[4:]), 1)
    if periodicidade == "trimestral" and len(p) == 6:
        trimestre = int(p[4:])
        if not 1 <= trimestre <= 4:
            raise ValueError(f"Trimestre inválido no período {p}")
        return pd.Timestamp(int(p[:4]), 3 * (trimestre - 1) + 1, 1)
    if periodicidade == "anual" and len(p) == 4:
        return pd.Timestamp(int(p), 1, 1)
    raise ValueError(f"Período '{p}' não é válido para periodicidade {periodicidade}")


def transformar(df_bruto: pd.DataFrame, indicador: Indicador) -> pd.DataFrame:
    """Tipagem, datas e padronização das colunas para a carga."""
    df = df_bruto.copy()
    df["id_indicador"] = indicador.id
    df["data_referencia"] = df["periodo"].map(
        lambda p: periodo_para_data(p, indicador.periodicidade)
    )
    df["valor"] = df["valor_bruto"].map(converter_valor).astype("float64")
    df["cod_localidade"] = df["cod_localidade"].astype(str)
    df["nivel"] = df["nivel"].map(NOMES_NIVEL).fillna(df["nivel"])

    nulos = int(df["valor"].isna().sum())
    if nulos:
        log.info("%s: %d valores sem dado no IBGE (mantidos como nulo)", indicador.id, nulos)

    colunas = ["id_indicador", "cod_localidade", "localidade", "nivel",
               "data_referencia", "valor"]
    return (df[colunas]
            .sort_values(["cod_localidade", "data_referencia"])
            .reset_index(drop=True))
