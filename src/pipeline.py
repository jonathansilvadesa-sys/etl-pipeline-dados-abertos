"""
Orquestrador do ETL: extrai do IBGE, transforma, valida e carrega no DuckDB.

Uso:
    python -m src.pipeline                              # todos os indicadores, 2018 até hoje
    python -m src.pipeline --indicadores ipca desocupacao --inicio 2022
    python -m src.pipeline --exportar-csv data/export   # também gera CSVs para o Power BI
"""

import argparse
import logging
import sys
from datetime import date

from src.config import INDICADORES
from src.extract.ibge_api import IBGEClient, extrair
from src.load.duckdb_loader import atualizar_dim_tempo, carregar, conectar, exportar_csv
from src.transform.limpeza import transformar
from src.transform.validacao import DadosInvalidos, validar

log = logging.getLogger("pipeline")


def ler_argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL de indicadores públicos do IBGE")
    parser.add_argument("--indicadores", nargs="+", choices=sorted(INDICADORES),
                        default=sorted(INDICADORES), help="quais indicadores rodar (padrão: todos)")
    parser.add_argument("--inicio", type=int, default=2018, help="ano inicial (padrão: 2018)")
    parser.add_argument("--fim", type=int, default=date.today().year, help="ano final (padrão: ano atual)")
    parser.add_argument("--banco", default="data/indicadores.duckdb", help="arquivo do DuckDB")
    parser.add_argument("--exportar-csv", metavar="PASTA", help="exporta as tabelas em CSV nessa pasta")
    args = parser.parse_args(argv)
    if args.inicio > args.fim:
        parser.error("--inicio não pode ser maior que --fim")
    return args


def executar(args: argparse.Namespace, client: IBGEClient | None = None) -> int:
    client = client or IBGEClient()
    con = conectar(args.banco)
    falhas = []

    for id_indicador in args.indicadores:
        indicador = INDICADORES[id_indicador]
        try:
            bruto = extrair(indicador, args.inicio, args.fim, client)
            tratado = transformar(bruto, indicador)
            relatorio = validar(tratado, indicador)
            carregar(con, tratado, indicador)
            log.info("%s: %d linhas, %d localidades, %s a %s", indicador.id,
                     relatorio["linhas"], relatorio["localidades"],
                     f"{relatorio['periodo_min']:%Y-%m}", f"{relatorio['periodo_max']:%Y-%m}")
        except (ConnectionError, DadosInvalidos, ValueError) as erro:
            # Um indicador com problema não impede a carga dos outros.
            log.error("%s: carga interrompida — %s", indicador.id, erro)
            falhas.append(indicador.id)

    if len(falhas) < len(args.indicadores):
        atualizar_dim_tempo(con)
        if args.exportar_csv:
            exportar_csv(con, args.exportar_csv)

    total = con.execute("SELECT COUNT(*) FROM fato_indicadores").fetchone()[0]
    con.close()
    log.info("Fim. fato_indicadores tem %d linhas em %s", total, args.banco)

    if falhas:
        log.error("Indicadores com falha: %s", ", ".join(falhas))
        return 1
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S")
    return executar(ler_argumentos(argv))


if __name__ == "__main__":
    sys.exit(main())
