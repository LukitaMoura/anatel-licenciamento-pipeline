"""Transformação: descompacta o ZIP e limpa o CSV bruto da Anatel."""
import logging
import os
import zipfile

import pandas as pd

log = logging.getLogger(__name__)

NUMERIC_COLUMNS = [
    "Latitude", "Longitude", "PotenciaTransmissorWatts", "GanhoAntena",
    "FreqTxMHz", "FreqRxMHz", "FrenteCostaAntena", "AlturaAntena",
]
NULL_LIKE = {"nan": None, "None": None, "": None}


def extract_zip(zip_path: str, extract_to: str) -> str:
    """Extrai o ZIP e devolve o caminho do primeiro arquivo (o CSV)."""
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("O arquivo baixado não é um ZIP válido.")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            raise ValueError("O arquivo ZIP está vazio.")
        zf.extractall(extract_to)
    return os.path.join(extract_to, names[0])


def read_raw_csv(csv_path: str) -> pd.DataFrame:
    """Lê o CSV do portal (separador pipe, tudo como texto).

    O arquivo vem em UTF-8 na maioria das UFs. Ler UTF-8 como latin1 não dá erro,
    mas corrompe os acentos ("SEGURANÇA" vira "SEGURANÃ\\x87A"). Por isso tenta
    UTF-8 primeiro e só cai para latin1 se o arquivo não for UTF-8 válido.
    """
    try:
        return pd.read_csv(csv_path, sep="|", encoding="utf-8", dtype=str)
    except UnicodeDecodeError:
        log.warning("CSV não é UTF-8, lendo como latin1: %s", csv_path)
        return pd.read_csv(csv_path, sep="|", encoding="latin1", dtype=str)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas, remove lixo e tipa as medidas físicas.

    - Pontos nos nomes de coluna viram "_" (quebram SQL).
    - Colunas 100% vazias são descartadas.
    - Strings "nan"/"None"/"" viram nulo real.
    - Linhas sem a chave "_id" são descartadas (antes e depois da limpeza,
      porque "nan" em texto só vira nulo depois do replace).
    """
    df = df.copy()
    df.columns = [c.replace(".", "_") for c in df.columns]
    if "_id" not in df.columns:
        raise KeyError("Coluna '_id' não encontrada no arquivo.")

    df = df.dropna(how="all", axis=1)
    df = df.dropna(subset=["_id"])

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip().replace(NULL_LIKE)

    before = len(df)
    df = df.dropna(subset=["_id"])
    if len(df) < before:
        log.warning("Removidas %d linhas cujo '_id' ficou nulo após a limpeza", before - len(df))

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)
