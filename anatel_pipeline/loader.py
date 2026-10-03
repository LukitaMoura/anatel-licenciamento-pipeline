"""Carga: upsert em lotes com evolução automática de schema (SQLite ou MySQL)."""
import logging

import pandas as pd
from sqlalchemy import Column, Float, MetaData, String, Table, inspect, text

log = logging.getLogger(__name__)

# Limite de parâmetros por statement: SQLite aceita 999; no MySQL usamos uma
# margem segura para não estourar max_allowed_packet em lotes largos.
MAX_PARAMS = {"sqlite": 999, "mysql": 40_000}


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _sql_type(df: pd.DataFrame, col: str, dialect: str) -> str:
    if col == "_id":
        return "VARCHAR(255)"
    if pd.api.types.is_numeric_dtype(df[col]):
        return "DOUBLE" if dialect == "mysql" else "FLOAT"
    return "VARCHAR(500)"


def build_table(df: pd.DataFrame, table_name: str) -> Table:
    columns = []
    for col in df.columns:
        if col == "_id":
            # Algumas chaves compostas de SP passam de 200 caracteres
            columns.append(Column(col, String(255), primary_key=True))
        elif pd.api.types.is_numeric_dtype(df[col]):
            columns.append(Column(col, Float()))
        else:
            columns.append(Column(col, String(500)))
    return Table(table_name, MetaData(), *columns)


def evolve_schema(engine, df: pd.DataFrame, table_name: str) -> list:
    """Adiciona ao banco colunas que aparecem no CSV mas ainda não existem na tabela.

    Algumas UFs trazem campos extras (ex.: "meioAcesso" em RJ e RS). Sem isso o
    lote inteiro seria rejeitado no meio da execução.
    """
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return []
    existing = {c["name"] for c in inspector.get_columns(table_name)}
    added = []
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for col in df.columns:
            if col in existing:
                continue
            col_type = _sql_type(df, col, dialect)
            if dialect == "mysql":
                conn.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN `{col}` {col_type} NULL"))
            else:
                conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" {col_type}'))
            log.info("Coluna nova '%s' adicionada à tabela", col)
            added.append(col)
    return added


def _records(df: pd.DataFrame) -> list:
    # NaN/NaT viram None: o PyMySQL rejeita "nan" como valor
    records = df.to_dict(orient="records")
    for rec in records:
        for key, val in rec.items():
            if not isinstance(val, (list, dict)) and pd.isna(val):
                rec[key] = None
    return records


def upsert(df: pd.DataFrame, engine, table_name: str) -> int:
    """Insere ou atualiza (pela chave "_id") todas as linhas do DataFrame, em lotes."""
    evolve_schema(engine, df, table_name)
    table = build_table(df, table_name)
    table.metadata.create_all(engine)

    dialect = engine.dialect.name
    if dialect not in MAX_PARAMS:
        raise ValueError(f"Dialeto não suportado: {dialect}")
    chunk_size = max(1, MAX_PARAMS[dialect] // len(table.columns))
    records = _records(df)
    written = 0

    with engine.begin() as conn:
        for chunk in chunked(records, chunk_size):
            if dialect == "sqlite":
                from sqlalchemy.dialects.sqlite import insert
                stmt = insert(table).values(chunk)
                updates = {c.name: getattr(stmt.excluded, c.name) for c in table.columns if c.name != "_id"}
                stmt = stmt.on_conflict_do_update(index_elements=["_id"], set_=updates)
            else:
                from sqlalchemy.dialects.mysql import insert
                stmt = insert(table).values(chunk)
                updates = {c.name: getattr(stmt.inserted, c.name) for c in table.columns if c.name != "_id"}
                stmt = stmt.on_duplicate_key_update(updates)
            conn.execute(stmt)
            written += len(chunk)

    log.info("%d linhas inseridas/atualizadas em lotes de %d", written, chunk_size)
    return written
