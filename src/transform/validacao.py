"""
Checagens de qualidade antes da carga.

Se algum problema for encontrado, a carga é interrompida: é melhor
não atualizar o banco do que gravar um dado errado no dashboard.
"""

import pandas as pd

from src.config import Indicador

CHAVE = ["id_indicador", "cod_localidade", "data_referencia"]


class DadosInvalidos(Exception):
    pass


def validar(df: pd.DataFrame, indicador: Indicador) -> dict:
    """Devolve um relatório de qualidade; levanta DadosInvalidos se houver problema."""
    problemas = []

    if df.empty:
        problemas.append("nenhum registro retornado")

    duplicadas = int(df.duplicated(subset=CHAVE).sum())
    if duplicadas:
        problemas.append(f"{duplicadas} linhas duplicadas na chave {CHAVE}")

    minimo, maximo = indicador.faixa_valida
    fora_da_faixa = df[df["valor"].notna() & ~df["valor"].between(minimo, maximo)]
    if not fora_da_faixa.empty:
        exemplo = fora_da_faixa.iloc[0]
        problemas.append(
            f"{len(fora_da_faixa)} valores fora da faixa [{minimo}, {maximo}] "
            f"(ex.: {exemplo['localidade']} {exemplo['data_referencia']:%Y-%m}: {exemplo['valor']})"
        )

    relatorio = {
        "indicador": indicador.id,
        "linhas": len(df),
        "localidades": df["cod_localidade"].nunique(),
        "nulos": int(df["valor"].isna().sum()),
        "periodo_min": df["data_referencia"].min() if not df.empty else None,
        "periodo_max": df["data_referencia"].max() if not df.empty else None,
        "problemas": problemas,
    }
    if problemas:
        raise DadosInvalidos(f"{indicador.id}: " + "; ".join(problemas))
    return relatorio
