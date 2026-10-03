# 📡 Pipeline de Licenciamento Anatel

Pipeline ETL que extrai do portal **Spectrum-E (Mosaico/Anatel)** a base de estações de telecomunicações licenciadas das **27 UFs**, limpa os dados e consolida tudo num banco único (SQLite ou MySQL). Inclui uma análise de KPIs sobre a base resultante.

| Indicador | Valor |
|---|---|
| Registros consolidados | **7.678.039** |
| Tempo total da automação | **2h38min** (~808 registros/s, contando download) |
| Tempo estimado do mesmo trabalho manual | 12 a 16 horas |
| Maior UF (SP) | 2.282.104 linhas, mais que o dobro do limite do Excel (1.048.576) |

## O problema

O portal da Anatel **não permite baixar a base nacional**. É preciso abrir "Filtros Adicionais", escolher a UF, esperar o portal compilar o arquivo (até 15 minutos em SP) e baixar um ZIP por vez. Depois disso, os CSVs ainda chegam com nomes de coluna que quebram SQL, nulos em formato de texto, colunas que existem só em algumas UFs e chaves com mais de 200 caracteres.

## A solução

```
┌──────────────┐   ┌────────────────┐   ┌──────────────────┐   ┌──────────────┐
│  scraper.py  │──▶│  transform.py  │──▶│    loader.py     │──▶│ SQLite/MySQL │
│  Playwright  │   │  pandas        │   │  upsert em lotes │   └──────┬───────┘
│  headless    │   │  limpeza/tipos │   │  schema evolutivo│          │
└──────────────┘   └────────────────┘   └──────────────────┘          ▼
        ▲                                                     analysis/kpis.py
        └──── progress.py: checkpoint por UF (retoma de onde parou)
```

### Decisões de engenharia

- **Upsert idempotente**: `ON DUPLICATE KEY UPDATE` (MySQL) e `ON CONFLICT DO UPDATE` (SQLite). Rodar de novo atualiza a base sem duplicar nada.
- **Lotes dimensionados pelo limite do banco**: o tamanho do lote é `limite_de_parâmetros ÷ nº_de_colunas` (999 no SQLite), o que evita estourar o driver em tabelas com 40 colunas.
- **Schema evolutivo**: se uma UF traz uma coluna nova (ex.: `meioAcesso` em RJ e RS), o loader executa `ALTER TABLE ADD COLUMN` em vez de falhar no meio da carga.
- **Checkpoint por UF**: o `progresso.json` guarda status, linhas e duração de cada estado. Se a execução cair em SP depois de 3 horas, a próxima pula as 26 UFs já concluídas.
- **Falha isolada**: um erro numa UF é registrado e o pipeline segue para a próxima.
- **Encoding seguro**: tenta UTF-8 e só cai para latin1 se o arquivo não for UTF-8 válido. Um teste garante que "SEGURANÇA" não vire "SEGURANÃA".

## Como rodar

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env           # STATE_FILTER=AC para testar com a menor UF; ALL para o Brasil

python -m anatel_pipeline      # extração + carga
python -m analysis.kpis        # gera docs/kpis_gerados.md
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest -v
```

Os testes rodam sem navegador e sem rede: limpeza, encoding, idempotência do upsert, atualização de registro, evolução de schema, lotes acima do limite do SQLite e retomada do checkpoint.

## Resultados da análise

O relatório completo está em [`docs/RELATORIO_KPIS.md`](docs/RELATORIO_KPIS.md), e o tempo e volume por UF em [`docs/execucao_por_uf.json`](docs/execucao_por_uf.json). Destaques:

- **SP concentra 29,7%** das licenças do país; SP e MG juntos somam quase metade.
- As três grandes operadoras móveis somam **32,9%**. Os outros ~67% são redes privadas: mineração, segurança pública, energia e papel e celulose.
- **4G (LTE)** lidera com 1,28 milhão de licenças, e o **5G (NR)** já passa de 214 mil.
- A faixa de **3,5 GHz** (5G standalone) aparece entre as cinco frequências mais licenciadas.

## Stack

Python · Playwright · pandas · SQLAlchemy 2 · SQLite / MySQL (PyMySQL) · pytest

> Dados públicos da Anatel. Este projeto não é afiliado à agência.
