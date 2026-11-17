import pytest
import requests

from src.config import INDICADORES
from src.extract import ibge_api
from src.extract.ibge_api import IBGEClient, montar_periodos, parsear_resposta
from tests.conftest import carregar_fixture


# ---------- parser ----------

def test_parser_gera_uma_linha_por_localidade_e_periodo():
    df = parsear_resposta(carregar_fixture("desocupacao_4099_v4099.json"))
    assert len(df) == 4                      # 2 UFs x 2 trimestres
    assert set(df["cod_localidade"]) == {"33", "35"}
    linha = df[(df["cod_localidade"] == "33") & (df["periodo"] == "202401")].iloc[0]
    assert linha["localidade"] == "Rio de Janeiro"
    assert linha["nivel"] == "N3"
    assert linha["valor_bruto"] == "10.3"


def test_parser_resposta_vazia_devolve_dataframe_com_colunas():
    df = parsear_resposta([])
    assert df.empty
    assert list(df.columns) == ["periodo", "cod_localidade", "localidade", "nivel", "valor_bruto"]


# ---------- períodos ----------

@pytest.mark.parametrize("indicador, esperado", [
    ("ipca", "202201-202412"),
    ("desocupacao", "202201-202404"),
    ("pib_municipal", "2022-2024"),
])
def test_montar_periodos(indicador, esperado):
    assert montar_periodos(INDICADORES[indicador], 2022, 2024) == esperado


# ---------- retry ----------

class RespostaFalsa:
    def __init__(self, status, corpo=None):
        self.status_code = status
        self.ok = status < 400
        self._corpo = corpo

    def json(self):
        return self._corpo

    def raise_for_status(self):
        raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = 0

    def get(self, url, params=None, timeout=None):
        self.chamadas += 1
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(ibge_api.time, "sleep", lambda segundos: None)


def test_retry_recupera_de_erro_temporario():
    sessao = SessaoFalsa([RespostaFalsa(503), requests.ConnectionError("caiu"), RespostaFalsa(200, [{"ok": 1}])])
    cliente = IBGEClient(max_tentativas=3, session=sessao)
    assert cliente.get_json("http://x") == [{"ok": 1}]
    assert sessao.chamadas == 3


def test_erro_4xx_nao_tenta_de_novo():
    sessao = SessaoFalsa([RespostaFalsa(404), RespostaFalsa(200, [])])
    cliente = IBGEClient(max_tentativas=3, session=sessao)
    with pytest.raises(requests.HTTPError):
        cliente.get_json("http://x")
    assert sessao.chamadas == 1


def test_desiste_depois_do_limite_de_tentativas():
    sessao = SessaoFalsa([RespostaFalsa(500)] * 3)
    cliente = IBGEClient(max_tentativas=3, session=sessao)
    with pytest.raises(ConnectionError, match="3 tentativas"):
        cliente.get_json("http://x")
    assert sessao.chamadas == 3
