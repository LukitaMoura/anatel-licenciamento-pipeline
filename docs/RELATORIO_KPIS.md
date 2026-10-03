# Relatório de Ingestão e Análise de KPIs: Licenciamento Anatel

Este documento apresenta o balanço de execução do robô de raspagem, a comparação com o esforço manual correspondente e uma análise detalhada dos KPIs extraídos do banco de dados consolidado com as 27 Unidades Federativas do Brasil.

---

## 📊 1. Automação vs. Processo Manual

### Métricas de Execução da Automação
* **Tempo Total de Execução**: **9.496,60 segundos (2 horas e 38 minutos)**.
* **Volume de Dados Ingerido**: **7.678.039 registros** consolidados e validados.
* **Taxa de Ingestão Média**: ~**808 registros/segundo** (incluindo tempo de download, extração e tratamento dos dados no pipeline).

### Estimativa de Tempo de Processamento Manual (Humano)
Se um operador humano fosse realizar a mesma consolidação manualmente, o tempo gasto estimado seria de **12 a 16 horas** de trabalho ininterrupto e sujeito a erros:
1. **Download Manual (~3 horas)**: O portal da Anatel leva de 1 a 15 minutos para compilar o download dos arquivos ZIP para estados grandes (como SP, MG, RJ). Clicar, aguardar e organizar os 27 downloads manualmente consumiria mais de 3 horas.
2. **Limitação de Ferramentas (Excel) e Divisão de Dados (~4 horas)**: O arquivo CSV de São Paulo (`SP`) possui **2.282.104 linhas** e o de Minas Gerais (`MG`) possui **1.069.874 linhas**. Como o Microsoft Excel possui um limite rígido de **1.048.576 linhas**, o operador não conseguiria abrir as tabelas completas para tratamento visual, necessitando particioná-las manualmente por comandos de texto ou ferramentas auxiliares.
3. **Tratamento de Dados (~4 horas)**: Corrigir pontuações em cabeçalhos (como substituir pontos `.` por underscores `_` para evitar falha no SQL), remover colunas nulas, limpar caracteres invisíveis e converter representações inválidas de string (`"nan"`, `"None"`) em nulos reais de banco de dados para mais de 7,6 milhões de linhas.
4. **Resolução de Conflitos de Schema (~3 horas)**: Resolver manualmente falhas de inserção como o tamanho da chave primária `_id` (que atinge mais de 200 caracteres em SP) e novos campos adicionados dinamicamente em algumas UFs (como a coluna `meioAcesso` que aparece no RJ e RS, mas não em estados menores).

---

## 📈 2. Análise de KPIs da Base Consolidada

A base final de dados conta com **7.678.039 registros** (estações/licenças ativas), 100% sob o status `LIC-LIC-01` (Licenciamento Ativo).

### A. Concentração Geográfica (Top UFs por Licenças)
Os dados mostram uma altíssima concentração de infraestrutura de telecomunicações no Sudeste e Sul do país:

| Posição | UF | Quantidade de Licenças | Representatividade (%) |
| :---: | :---: | :---: | :---: |
| 1 | **SP** | 2.282.104 | 29,72% |
| 2 | **MG** | 1.069.874 | 13,93% |
| 3 | **RJ** | 508.492 | 6,62% |
| 4 | **PR** | 458.866 | 5,98% |
| 5 | **MA** | 324.992 | 4,23% |
| 6 | **BA** | 318.219 | 4,14% |
| 7 | **CE** | 290.896 | 3,79% |
| 8 | **RS** | 271.059 | 3,53% |
| 9 | **GO** | 262.769 | 3,42% |
| 10 | **PA** | 257.834 | 3,36% |
| - | **Outros** | 1.632.938 | 21,27% |
| **Total** | **BR** | **7.678.039** | **100,00%** |

*💡 **Insight**: Apenas o estado de São Paulo concentra quase **30%** de todas as licenças de transmissão de dados do Brasil, seguido por Minas Gerais com cerca de **14%**. Juntos, os dois estados somam quase a metade de toda a infraestrutura nacional.*

---

### B. Distribuição por Operadora / Entidade (Top 15)
Diferente do esperado para um mercado exclusivamente móvel comercial, as telecomunicações privadas (redes industriais, mineração, segurança pública e utilidades) representam uma parcela massiva da infraestrutura licenciada:

| Posição | Entidade / Operadora | Licenças Ativas | Categoria |
| :---: | :--- | :---: | :--- |
| 1 | **Telefonica Brasil S.A. (Vivo)** | 886.344 | Comercial Móvel |
| 2 | **CLARO S.A.** | 868.746 | Comercial Móvel |
| 3 | **TIM S.A.** | 767.427 | Comercial Móvel |
| 4 | **Vale S.A. (Somatório de Grafias)** | 446.787 | Mineração / Rede Privada |
| 5 | **Sec. de Estado de Segurança Pública (SSP)** | 185.493 | Segurança Pública |
| 6 | **Stocktotal Telecomunicações Ltda** | 181.058 | Locação / Redes Privadas |
| 7 | **Sec. da Segurança Pública e Defesa Social** | 155.896 | Segurança Pública |
| 8 | **Polícia Militar de Minas Gerais (PMMG)** | 134.151 | Segurança Pública |
| 9 | **Klabin S.A.** | 106.715 | Papel e Celulose / Privada |
| 10 | **Companhia Paulista de Força e Luz (CPFL)** | 65.157 | Energia Elétrica / Utilidades |
| 11 | **Cenibra S.A.** | 58.743 | Celulose / Privada |
| 12 | **Polícia Civil de São Paulo** | 57.808 | Segurança Pública |
| 13 | **CSN Mineração S.A.** | 53.798 | Mineração / Privada |
| 14 | **Companhia Siderúrgica Nacional (CSN)** | 52.998 | Siderurgia / Privada |

*💡 **Insight 1**: As 3 grandes operadoras de telefonia celular comercial (Vivo, Claro e Tim) somam juntas **2.522.517 licenças**, representando **32,85%** do total. Isso significa que mais de **67%** das licenças de radiotransmissão no Brasil pertencem a redes privadas de indústrias, mineradoras, forças policiais e concessionárias de serviços públicos.*
*💡 **Insight 2**: A mineradora **Vale S.A.** desponta como a maior operadora de telecomunicações privadas do país, possuindo quase **450.000 licenças** dedicadas para telemetria, comunicação de frotas e operações de mina.*

---

### C. Tecnologia de Transmissão Utilizada
A grande maioria dos registros corresponde a canais analógicos ou ponto-a-ponto sem tecnologias celulares padronizadas. No espectro móvel/dados móveis comerciais, as tecnologias se dividem da seguinte forma:

| Tecnologia | Licenças | Descrição |
| :---: | :---: | :--- |
| **Não Especificada / Nula** | 5.286.913 | Rádios VHF/UHF, enlaces de microondas e telemetria |
| **LTE** | 1.276.526 | 4G (Dados Móveis de alta velocidade comercial/privada) |
| **WCDMA** | 408.785 | 3G (Telefonia e Dados Móveis) |
| **GSM** | 405.035 | 2G (Voz e IoT de baixa velocidade) |
| **NR** | 214.271 | 5G (Nova Geração de redes de dados móveis) |
| **DMR** | 34.434 | Digital Mobile Radio (Comunicação de rádio bidirecional digital) |
| **TETRA** | 3.281 | Redes de comunicação crítica de segurança pública |

*💡 **Insight**: O **4G (LTE)** consolida-se como a principal rede móvel em atividade no país com mais de 1,2 milhão de licenças, enquanto o **5G (NR)** já passa de **214.000 licenças ativas**, superando de forma consolidada redes de comunicação digital exclusivas como o DMR ou TETRA.*

---

### D. Distribuição de Frequências (Top Freqs de Transmissão)
As frequências mais utilizadas mapeiam os principais canais de dados móveis (4G/5G) e serviços de cobertura regional no Brasil:

1. **788.0 MHz (124.058 licenças)**: Banda 28 LTE (700 MHz). Frequência crucial do 4G no Brasil devido ao seu alto alcance de cobertura interna e regional (antiga faixa de TV Analógica).
2. **2160.0 MHz (122.004 licenças)**: Utilizado em grande parte para portadoras de downlink de 3G/4G.
3. **2680.0 MHz (105.310 licenças)**: Faixa de capacidade do 4G (2.6 GHz), essencial para altas velocidades em centros urbanos adensados.
4. **874.5 MHz (101.695 licenças)**: Faixa de sub-1GHz utilizada por operadoras móveis em áreas rurais ou de interior.
5. **3450.0 MHz (70.048 licenças)**: A frequência "nobre" do **5G Standalone** no Brasil (3.5 GHz), concentrando os investimentos mais recentes em infraestrutura móvel de ultravelocidade.
