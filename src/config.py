"""
Catálogo dos indicadores extraídos da API de agregados do IBGE (SIDRA).

Cada indicador aponta para uma tabela e uma variável do SIDRA. Os códigos
foram conferidos nos metadados oficiais:
https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Indicador:
    id: str               # chave usada no pipeline e no banco
    nome: str
    tabela: int           # tabela (agregado) do SIDRA
    variavel: int         # variável dentro da tabela
    nivel: str            # nível territorial: N1 Brasil, N3 UF, N6 município
    periodicidade: str    # mensal | trimestral | anual
    unidade: str
    faixa_valida: tuple   # (mínimo, máximo) aceitos na validação


INDICADORES = {
    "ipca": Indicador(
        id="ipca",
        nome="IPCA - variação mensal",
        tabela=1737,
        variavel=63,
        nivel="N1",
        periodicidade="mensal",
        unidade="%",
        # Cobre até a hiperinflação dos anos 80/90 (picos de ~80% ao mês).
        # Pega o erro de pedir o número-índice (variável 2266, valores na casa dos milhares).
        faixa_valida=(-5.0, 100.0),
    ),
    "desocupacao": Indicador(
        id="desocupacao",
        nome="Taxa de desocupação (PNAD Contínua)",
        tabela=4099,
        variavel=4099,
        nivel="N3",
        periodicidade="trimestral",
        unidade="%",
        faixa_valida=(0.0, 100.0),
    ),
    "pib_municipal": Indicador(
        id="pib_municipal",
        nome="PIB a preços correntes",
        tabela=5938,
        variavel=37,
        nivel="N6",
        periodicidade="anual",
        unidade="R$ mil",
        faixa_valida=(0.0, float("inf")),
    ),
}

NOMES_NIVEL = {"N1": "Brasil", "N3": "UF", "N6": "Município"}
