import os
import zipfile

import pandas as pd
import pytest
from sqlalchemy import create_engine, inspect, text

from anatel_pipeline import loader, transform
from anatel_pipeline.config import parse_states
from anatel_pipeline.progress import ProgressTracker

RAW_CSV = (
    "_id|NomeEntidade|SiglaUf|Tecnologia|FreqTxMHz|Latitude|Coluna.Vazia\n"
    "a1| CLARO S.A. |SP|LTE|788.0|-23.5|\n"
    "a2|TIM S.A.|SP|nan|2680,0|-23.6|\n"
    "|SEM ID|SP|GSM|900|-23.7|\n"
    "nan|ID TEXTO NAN|SP|GSM|900|-23.7|\n"
)


@pytest.fixture
def raw_df(tmp_path):
    path = tmp_path / "raw.csv"
    path.write_text(RAW_CSV, encoding="latin1")
    return transform.read_raw_csv(str(path))


def test_clean_normaliza_colunas_e_remove_lixo(raw_df):
    df = transform.clean(raw_df)
    assert "Coluna_Vazia" not in df.columns          # coluna 100% vazia descartada
    assert list(df["_id"]) == ["a1", "a2"]            # sem _id e "_id = nan" descartados
    assert df.loc[0, "NomeEntidade"] == "CLARO S.A."  # strip aplicado
    assert pd.isna(df.loc[1, "Tecnologia"])           # "nan" texto vira nulo real
    assert df["Latitude"].dtype.kind == "f"           # medida física tipada


def test_le_utf8_sem_corromper_acentos(tmp_path):
    path = tmp_path / "utf8.csv"
    path.write_text("_id|NomeEntidade\nx1|SECRETARIA DE SEGURANÇA PÚBLICA\n", encoding="utf-8")
    df = transform.read_raw_csv(str(path))
    assert df.loc[0, "NomeEntidade"] == "SECRETARIA DE SEGURANÇA PÚBLICA"


def test_cai_para_latin1_quando_nao_e_utf8(tmp_path):
    path = tmp_path / "latin1.csv"
    path.write_bytes("_id|Municipio\nx1|São Paulo\n".encode("latin1"))
    df = transform.read_raw_csv(str(path))
    assert df.loc[0, "Municipio"] == "São Paulo"


def test_clean_exige_chave(tmp_path):
    path = tmp_path / "sem_id.csv"
    path.write_text("A|B\n1|2\n", encoding="latin1")
    with pytest.raises(KeyError):
        transform.clean(transform.read_raw_csv(str(path)))


def test_extract_zip(tmp_path):
    zip_path = tmp_path / "uf.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dados.csv", RAW_CSV)
    csv = transform.extract_zip(str(zip_path), str(tmp_path / "out"))
    assert os.path.basename(csv) == "dados.csv"


def test_upsert_e_idempotente(raw_df):
    engine = create_engine("sqlite://")
    df = transform.clean(raw_df)
    loader.upsert(df, engine, "t")
    loader.upsert(df, engine, "t")  # rodar de novo não duplica
    with engine.connect() as conn:
        assert conn.execute(text("select count(*) from t")).scalar() == 2


def test_upsert_atualiza_registro_existente(raw_df):
    engine = create_engine("sqlite://")
    df = transform.clean(raw_df)
    loader.upsert(df, engine, "t")
    df.loc[df["_id"] == "a1", "NomeEntidade"] = "NOVO NOME"
    loader.upsert(df, engine, "t")
    with engine.connect() as conn:
        nome = conn.execute(text("select NomeEntidade from t where _id='a1'")).scalar()
    assert nome == "NOVO NOME"


def test_schema_evolui_quando_aparece_coluna_nova(raw_df):
    engine = create_engine("sqlite://")
    df = transform.clean(raw_df)
    loader.upsert(df, engine, "t")

    df2 = df.copy()
    df2["meioAcesso"] = "FIBRA"  # campo que só existe em algumas UFs
    loader.upsert(df2, engine, "t")

    cols = {c["name"] for c in inspect(engine).get_columns("t")}
    assert "meioAcesso" in cols


def test_lotes_respeitam_limite_do_sqlite():
    n = 2_000  # 2.000 linhas x 3 colunas passaria de 999 parâmetros num único INSERT
    df = pd.DataFrame({"_id": [f"id{i}" for i in range(n)], "a": ["x"] * n, "b": [1.0] * n})
    engine = create_engine("sqlite://")
    assert loader.upsert(df, engine, "t") == n


def test_parse_states():
    assert len(parse_states("ALL")) == 27
    assert parse_states("sp, rj") == ["SP", "RJ"]
    with pytest.raises(ValueError):
        parse_states("XX")


def test_progress_retoma(tmp_path):
    path = str(tmp_path / "p.json")
    p = ProgressTracker(path)
    p.record("AC", "success", 1.0, rows=10)
    p.record("SP", "failed", 2.0, error="timeout")
    p2 = ProgressTracker(path)
    assert p2.is_done("AC") and not p2.is_done("SP")
