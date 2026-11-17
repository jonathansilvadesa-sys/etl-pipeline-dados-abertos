"""
Carga no DuckDB: um banco analítico em um único arquivo, sem servidor.

A carga é idempotente: rodar o pipeline duas vezes para o mesmo período
não duplica linhas. A chave primária da fato (indicador, localidade, data)
faz o INSERT OR REPLACE atualizar o que já existe e inserir o que é novo.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.config import Indicador

log = logging.getLogger(__name__)

SCHEMA = Path(__file__).with_name("schema.sql")


def conectar(caminho_banco: str | Path) -> duckdb.DuckDBPyConnection:
    Path(caminho_banco).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(caminho_banco))
    con.execute(SCHEMA.read_text(encoding="utf-8"))
    return con


def carregar(con: duckdb.DuckDBPyConnection, df: pd.DataFrame, indicador: Indicador) -> int:
    """Grava dimensões e fato de um indicador. Devolve o número de linhas da fato gravadas."""
    con.execute(
        "INSERT OR REPLACE INTO dim_indicador VALUES (?, ?, ?, ?, ?, ?, ?)",
        [indicador.id, indicador.nome, indicador.unidade, indicador.periodicidade,
         indicador.nivel, indicador.tabela, indicador.variavel],
    )

    localidades = (df[["cod_localidade", "localidade", "nivel"]]
                   .drop_duplicates("cod_localidade"))
    con.register("stg_localidade", localidades)
    con.execute("""
        INSERT OR REPLACE INTO dim_localidade
        SELECT cod_localidade,
               localidade,
               nivel,
               CASE WHEN nivel = 'Brasil' THEN NULL ELSE LEFT(cod_localidade, 2) END
        FROM stg_localidade
    """)

    con.register("stg_fato", df)
    con.execute("""
        INSERT OR REPLACE INTO fato_indicadores
        SELECT id_indicador, cod_localidade, CAST(data_referencia AS DATE), valor, now()
        FROM stg_fato
    """)
    con.unregister("stg_localidade")
    con.unregister("stg_fato")

    log.info("%s: %d linhas gravadas na fato", indicador.id, len(df))
    return len(df)


def atualizar_dim_tempo(con: duckdb.DuckDBPyConnection) -> None:
    """Recria o calendário mensal cobrindo todo o intervalo de datas da fato."""
    con.execute("""
        CREATE OR REPLACE TABLE dim_tempo AS
        WITH limites AS (
            SELECT MIN(data_referencia) AS inicio, MAX(data_referencia) AS fim
            FROM fato_indicadores
        )
        SELECT CAST(d AS DATE)          AS data,
               year(d)                  AS ano,
               quarter(d)               AS trimestre,
               month(d)                 AS mes,
               strftime(d, '%Y-%m')     AS ano_mes
        FROM limites,
             generate_series(inicio, fim, INTERVAL 1 MONTH) AS t(d)
    """)


def exportar_csv(con: duckdb.DuckDBPyConnection, pasta: str | Path) -> list[Path]:
    """Exporta as 4 tabelas em CSV (UTF-8, separador ;) para importar no Power BI."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for tabela in ["dim_indicador", "dim_localidade", "dim_tempo", "fato_indicadores"]:
        destino = pasta / f"{tabela}.csv"
        con.execute(f"COPY {tabela} TO '{destino.as_posix()}' (HEADER, DELIMITER ';')")
        arquivos.append(destino)
    log.info("Tabelas exportadas para %s", pasta)
    return arquivos
