import pandas as pd
import pytest

from src.config import INDICADORES
from src.extract.ibge_api import parsear_resposta
from src.transform.limpeza import converter_valor, periodo_para_data, transformar
from src.transform.validacao import DadosInvalidos, validar
from tests.conftest import carregar_fixture


# ---------- valores e símbolos do IBGE ----------

@pytest.mark.parametrize("bruto, esperado", [
    ("0.42", 0.42),
    ("359632648", 359632648.0),
    ("-", 0.0),          # "-" no IBGE é zero, não dado ausente
    ("...", None),
    ("..", None),
    ("X", None),
])
def test_converter_valor(bruto, esperado):
    assert converter_valor(bruto) == esperado


# ---------- períodos ----------

@pytest.mark.parametrize("periodo, periodicidade, esperado", [
    ("202403", "mensal", "2024-03-01"),
    ("202401", "trimestral", "2024-01-01"),
    ("202404", "trimestral", "2024-10-01"),
    ("2021", "anual", "2021-01-01"),
])
def test_periodo_para_data(periodo, periodicidade, esperado):
    assert periodo_para_data(periodo, periodicidade) == pd.Timestamp(esperado)


def test_periodo_invalido_levanta_erro():
    with pytest.raises(ValueError):
        periodo_para_data("202405", "trimestral")


# ---------- transformação completa ----------

def test_transformar_ipca():
    bruto = parsear_resposta(carregar_fixture("ipca_1737_v63.json"))
    df = transformar(bruto, INDICADORES["ipca"])
    assert len(df) == 6
    assert df["valor"].dtype == "float64"
    assert df.loc[0, "data_referencia"] == pd.Timestamp("2024-01-01")
    assert df.loc[0, "valor"] == pytest.approx(0.42)
    assert set(df["nivel"]) == {"Brasil"}


# ---------- validação ----------

def _ipca_tratado():
    bruto = parsear_resposta(carregar_fixture("ipca_1737_v63.json"))
    return transformar(bruto, INDICADORES["ipca"])


def test_validacao_aprova_dados_reais():
    relatorio = validar(_ipca_tratado(), INDICADORES["ipca"])
    assert relatorio["linhas"] == 6
    assert relatorio["problemas"] == []


def test_validacao_barra_duplicatas():
    df = _ipca_tratado()
    with pytest.raises(DadosInvalidos, match="duplicadas"):
        validar(pd.concat([df, df.head(1)]), INDICADORES["ipca"])


def test_validacao_barra_numero_indice_no_lugar_da_variacao():
    # Erro real da primeira versão: a variável 2266 é o número-índice do IPCA
    # (valores na casa dos milhares), não a variação mensal em %.
    df = _ipca_tratado()
    df.loc[0, "valor"] = 6971.47
    with pytest.raises(DadosInvalidos, match="fora da faixa"):
        validar(df, INDICADORES["ipca"])


def test_validacao_barra_resultado_vazio():
    vazio = transformar(parsear_resposta([]), INDICADORES["ipca"])
    with pytest.raises(DadosInvalidos, match="nenhum registro"):
        validar(vazio, INDICADORES["ipca"])
