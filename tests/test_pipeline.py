"""Testes de ponta a ponta: pipeline completo com as respostas salvas da API."""

import duckdb

from src.pipeline import executar, ler_argumentos


def _rodar(tmp_path, cliente, *extras):
    args = ler_argumentos(["--banco", str(tmp_path / "teste.duckdb"), *extras])
    return executar(args, client=cliente)


def _contar(tmp_path, sql):
    with duckdb.connect(str(tmp_path / "teste.duckdb"), read_only=True) as con:
        return con.execute(sql).fetchone()[0]


def test_pipeline_carrega_os_tres_indicadores(tmp_path, cliente_falso):
    assert _rodar(tmp_path, cliente_falso) == 0
    # 6 meses de IPCA + 2 UFs x 2 trimestres + 2 municípios x 1 ano
    assert _contar(tmp_path, "SELECT COUNT(*) FROM fato_indicadores") == 6 + 4 + 2
    assert _contar(tmp_path, "SELECT COUNT(*) FROM dim_indicador") == 3
    assert _contar(tmp_path, "SELECT COUNT(*) FROM dim_localidade") == 1 + 2 + 2


def test_pipeline_e_idempotente(tmp_path, cliente_falso):
    _rodar(tmp_path, cliente_falso)
    _rodar(tmp_path, cliente_falso)
    assert _contar(tmp_path, "SELECT COUNT(*) FROM fato_indicadores") == 12


def test_municipio_recebe_codigo_da_uf(tmp_path, cliente_falso):
    _rodar(tmp_path, cliente_falso)
    assert _contar(tmp_path, "SELECT cod_uf FROM dim_localidade WHERE cod_localidade = '3303302'") == "33"
    assert _contar(tmp_path, "SELECT cod_uf FROM dim_localidade WHERE cod_localidade = '1'") is None


def test_dim_tempo_cobre_todo_o_intervalo(tmp_path, cliente_falso):
    _rodar(tmp_path, cliente_falso)
    # da menor data (2021-01, PIB) à maior (2024-06, IPCA): 42 meses
    assert _contar(tmp_path, "SELECT COUNT(*) FROM dim_tempo") == 42


def test_exporta_csv(tmp_path, cliente_falso):
    pasta = tmp_path / "export"
    _rodar(tmp_path, cliente_falso, "--exportar-csv", str(pasta))
    assert sorted(p.name for p in pasta.glob("*.csv")) == [
        "dim_indicador.csv", "dim_localidade.csv", "dim_tempo.csv", "fato_indicadores.csv"]


def test_falha_em_um_indicador_nao_impede_os_outros(tmp_path, cliente_falso):
    class ClienteComFalha(type(cliente_falso)):
        def get_json(self, url, params=None):
            if "/1737/" in url:
                raise ConnectionError("IBGE fora do ar")
            return super().get_json(url, params)

    assert _rodar(tmp_path, ClienteComFalha()) == 1          # sinaliza a falha
    assert _contar(tmp_path, "SELECT COUNT(*) FROM fato_indicadores") == 4 + 2
