# Relatório Consolidado de Latência e Tokens — Comparação de Sessões (2)

**Sessão A (sem cache):** `259c3ce3-7fe1-423f-a535-d7330c5200f4.csv`
**Sessão B (com semantic cache):** `51b70b90-fec9-4b8d-b375-33e0ce3c88ad.csv`

## Dados brutos

### Sessão A — todas as requisições sem cache (`cache_hit = False`)

| # | Pergunta | Latência (ms) | Prompt Tokens | Output Tokens | Total Tokens |
| --- | --- | --- | --- | --- | --- |
| 1 | What is my current balance? | 5212.99 | 994 | 61 | 1055 |
| 2 | What is my current balance? | 4604.60 | 994 | 61 | 1055 |
| 3 | What's my account balance? | 4968.28 | 994 | 63 | 1057 |
| 4 | Do you offer a savings account? | 6777.71 | 481 | 288 | 769 |
| 5 | What is my current balance? | 4544.65 | 994 | 49 | 1043 |
| 6 | Do you offer a savings account? | 8248.05 | 481 | 388 | 869 |
| 7 | What are my recent transactions? | 6080.35 | 1063 | 146 | 1209 |
| 8 | What are my recent transactions? | 5798.00 | 1031 | 121 | 1152 |
| 9 | Please block my card, I lost it. | 4942.02 | 1011 | 117 | 1128 |
| 10 | Can you show me my last transactions? | 5833.43 | 1067 | 143 | 1210 |
| **Total** | — | — | **9110** | **1437** | **10547** |

### Sessão B — com semantic cache (`cache_scope` = `specific`/`general`)

| # | Pergunta | Cache Hit | Escopo | Latência (ms) | Prompt Tokens | Output Tokens | Total Tokens | Tokens Salvos |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | What is my current balance? | False | specific | 5512.25 | 994 | 61 | 1055 | 0 |
| 2 | What is my current balance? | False | specific | 4938.49 | 994 | 49 | 1043 | 0 |
| 3 | What's my account balance? | True | specific | 64.99 | 0 | 0 | 0 | 1055 |
| 4 | Do you offer a savings account? | False | general | 6780.17 | 481 | 271 | 752 | 0 |
| 5 | What is my current balance? | True | specific | 76.46 | 0 | 0 | 0 | 1043 |
| 6 | Do you offer a savings account? | True | general | 144.92 | 0 | 0 | 0 | 752 |
| 7 | What are my recent transactions? | False | specific | 6609.19 | 1063 | 146 | 1209 | 0 |
| 8 | What are my recent transactions? | False | specific | 5986.16 | 1031 | 121 | 1152 | 0 |
| 9 | Please block my card, I lost it. | False | specific | 5068.24 | 1011 | 116 | 1127 | 0 |
| 10 | Can you show me my last transactions? | True | specific | 58.81 | 0 | 0 | 0 | 1209 |
| **Total** | — | — | — | **5574** | **764** | **6338** | **4059** |

## Consolidado de Latência

| Métrica | Sessão A (sem cache) | Sessão B (com cache) |
| --- | --- | --- |
| Latência média geral | 5701.01 ms | 3523.97 ms |
| Latência média (cache miss) | 5701.01 ms | 5815.75 ms |
| Latência média (cache hit) | — | 86.30 ms |
| Latência mínima | 4544.65 ms | 58.81 ms |
| Latência máxima | 8248.05 ms | 6780.17 ms |
| Taxa de acerto de cache | 0% | 40% (4 de 10) |

## Consolidado de Tokens

| Métrica | Sessão A (sem cache) | Sessão B (com cache) |
| --- | --- | --- |
| Total prompt tokens | 9110 | 5574 |
| Total output tokens | 1437 | 764 |
| Total tokens consumidos (API) | 10547 | 6338 |
| Tokens totais economizados (cache) | 0 | 4059 |
| Tokens médios por requisição (real) | 1054.70 | 633.80 |
| Redução de consumo de tokens vs Sessão A | — | -39,9% |

## Observações

- **Redução de latência em cache hits:** as respostas servidas via cache semântico na Sessão B caem de uma faixa de ~4.9–6.8 s (miss) para ~59–145 ms (hit), uma redução de **~98,5%** na latência média.
- **Latência média geral 38% menor:** mesmo com 6 dos 10 pedidos ainda sendo miss, a média geral (3524 ms) fica bem abaixo da Sessão A (5701 ms).
- **Escopo `general` também se beneficia:** a pergunta "Do you offer a savings account?" (escopo geral) teve hit em 144.92 ms contra ~6.8 s no primeiro miss, mostrando que o cache semântico funciona tanto para perguntas específicas de conta quanto para perguntas gerais de produto.
- **Pergunta sem correspondência de cache:** "Please block my card, I lost it." não teve hit em nenhuma das sessões dentro da amostra — indica que essa intenção ainda não tinha sido cacheada antes da consulta.
- **Consumo de tokens 39,9% menor:** mesmo com taxa de acerto de apenas 40%, a Sessão B consumiu 6338 tokens reais de API contra 10547 da Sessão A, além de 4059 tokens adicionais evitados via cache (não cobrados/gerados pelo modelo).
