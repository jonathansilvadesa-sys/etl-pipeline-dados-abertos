-- Modelo estrela do pipeline (DuckDB)
-- Grão da fato: um valor por indicador, localidade e período.

CREATE TABLE IF NOT EXISTS dim_indicador (
    id_indicador    VARCHAR PRIMARY KEY,
    nome            VARCHAR NOT NULL,
    unidade         VARCHAR NOT NULL,
    periodicidade   VARCHAR NOT NULL,
    nivel           VARCHAR NOT NULL,
    tabela_sidra    INTEGER NOT NULL,
    variavel_sidra  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_localidade (
    cod_localidade  VARCHAR PRIMARY KEY,   -- código IBGE (1 = Brasil, 33 = RJ, 3303302 = Niterói)
    nome            VARCHAR NOT NULL,
    nivel           VARCHAR NOT NULL,      -- Brasil | UF | Município
    cod_uf          VARCHAR               -- 2 primeiros dígitos do código; nulo para Brasil
);

CREATE TABLE IF NOT EXISTS dim_tempo (
    data            DATE PRIMARY KEY,      -- primeiro dia do mês
    ano             INTEGER NOT NULL,
    trimestre       INTEGER NOT NULL,
    mes             INTEGER NOT NULL,
    ano_mes         VARCHAR NOT NULL       -- 'AAAA-MM'
);

CREATE TABLE IF NOT EXISTS fato_indicadores (
    id_indicador    VARCHAR NOT NULL,
    cod_localidade  VARCHAR NOT NULL,
    data_referencia DATE    NOT NULL,
    valor           DOUBLE,
    carregado_em    TIMESTAMP NOT NULL,
    PRIMARY KEY (id_indicador, cod_localidade, data_referencia)
);
