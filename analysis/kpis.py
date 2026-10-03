"""Gera o relatório de KPIs a partir da base consolidada.

Uso:
    python -m analysis.kpis                      # usa o banco do .env
    python -m analysis.kpis sqlite:///minha.db   # ou uma URL explícita

Saída: docs/kpis_gerados.md
"""
import os
import sys

import pandas as pd
from sqlalchemy import create_engine

from anatel_pipeline.config import BASE_DIR, TABLE_NAME, load_settings

QUERIES = {
    "Licenças por UF": f"""
        SELECT SiglaUf AS uf, COUNT(*) AS licencas
        FROM {TABLE_NAME} GROUP BY SiglaUf ORDER BY licencas DESC
    """,
    # A mesma entidade aparece com grafias diferentes ("TELEFONICA BRASIL S.A." x
    # "Telefonica Brasil S.a."): agrupar pelo nome em maiúsculas unifica as variações
    "Top 15 entidades": f"""
        SELECT UPPER(TRIM(NomeEntidade)) AS entidade, COUNT(*) AS licencas
        FROM {TABLE_NAME} GROUP BY UPPER(TRIM(NomeEntidade)) ORDER BY licencas DESC LIMIT 15
    """,
    "Licenças por tecnologia": f"""
        SELECT COALESCE(Tecnologia, 'Não especificada') AS tecnologia, COUNT(*) AS licencas
        FROM {TABLE_NAME} GROUP BY Tecnologia ORDER BY licencas DESC
    """,
    "Top 10 frequências de transmissão (MHz)": f"""
        SELECT FreqTxMHz AS freq_mhz, COUNT(*) AS licencas
        FROM {TABLE_NAME} WHERE FreqTxMHz IS NOT NULL
        GROUP BY FreqTxMHz ORDER BY licencas DESC LIMIT 10
    """,
}


def add_share(df: pd.DataFrame, total: int) -> pd.DataFrame:
    df = df.copy()
    df["participacao_%"] = (df["licencas"] / total * 100).round(2)
    return df


def build_report(engine) -> str:
    total = pd.read_sql(f"SELECT COUNT(*) AS n FROM {TABLE_NAME}", engine)["n"].iloc[0]
    parts = ["# KPIs — Licenciamento Anatel\n", f"**Total de registros:** {total:,}".replace(",", ".") + "\n"]
    for title, sql in QUERIES.items():
        df = add_share(pd.read_sql(sql, engine), total)
        parts.append(f"## {title}\n\n{df.to_markdown(index=False)}\n")
    return "\n".join(parts)


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else load_settings().database_url
    report = build_report(create_engine(url))
    out = os.path.join(BASE_DIR, "docs", "kpis_gerados.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Relatório salvo em {out}")


if __name__ == "__main__":
    main()
