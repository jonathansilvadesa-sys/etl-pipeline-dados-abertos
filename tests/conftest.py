import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Respostas reais da API do IBGE, salvas para os testes rodarem sem internet.
ARQUIVO_POR_TABELA = {
    1737: "ipca_1737_v63.json",
    4099: "desocupacao_4099_v4099.json",
    5938: "pib_municipal_5938_v37.json",
}


def carregar_fixture(nome: str) -> list:
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


class ClienteFalso:
    """Substitui o IBGEClient: devolve a resposta salva da tabela pedida na URL."""

    def __init__(self):
        self.urls = []

    def get_json(self, url, params=None):
        self.urls.append(url)
        tabela = int(url.split("/agregados/")[1].split("/")[0])
        return carregar_fixture(ARQUIVO_POR_TABELA[tabela])


@pytest.fixture
def cliente_falso():
    return ClienteFalso()
