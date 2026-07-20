# Relatório Consolidado de Latência — Comparação de Sessões

**Sessão A (sem cache):** `cb0d862b-9624-4043-b2f0-7031b1104a0d.csv`
**Sessão B (com semantic cache):** `2df7f896-6f73-48d4-83fd-7e160df68047.csv`

## Dados brutos

### Sessão A — todas as requisições sem cache (`cache_hit = False`)

| # | Pergunta | Latência (ms) | Prompt Tokens | Output Tokens | Total Tokens |
| --- | --- | --- | --- | --- | --- |
| 1 | What is my current balance? | 6754.56 | 994 | 61 | 1055 |
| 2 | What is my current balance? | 4632.05 | 994 | 61 | 1055 |
| 3 | What's my account balance? | 4632.95 | 1002 | 46 | 1048 |
| 4 | How much money do I have in my account? | 4414.66 | 1002 | 46 | 1048 |
| 5 | What are my recent transactions? | 5817.78 | 1063 | 146 | 1209 |
| 6 | Can you show me my last transactions? | 5760.21 | 1067 | 143 | 1210 |
| **Total** | — | — | **6122** | **503** | **6625** |

### Sessão B — com semantic cache (`cache_scope = specific`)

| # | Pergunta | Cache Hit | Latência (ms) | Prompt Tokens | Output Tokens | Total Tokens | Tokens Salvos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | What is my current balance? | False | 4908.34 | 994 | 49 | 1043 | 0 |
| 2 | What is my current balance? | True | 72.09 | 0 | 0 | 0 | 1043 |
| 3 | What's my account balance? | True | 106.22 | 0 | 0 | 0 | 1043 |
| 4 | How much money do I have in my account? | True | 62.39 | 0 | 0 | 0 | 1043 |
| 5 | What are my recent transactions? | False | 7250.22 | 1063 | 146 | 1209 | 0 |
| 6 | Can you show me my last transactions? | True | 69.68 | 0 | 0 | 0 | 1209 |
| **Total** | — | — | — | **2057** | **195** | **2252** | **4338** |

## Consolidado de Latência

| Métrica | Sessão A (sem cache) | Sessão B (com cache) |
| --- | --- | --- |
| Latência média geral | 5335.37 ms | 2078.16 ms |
| Latência média (cache miss) | 5335.37 ms | 6079.28 ms |
| Latência média (cache hit) | — | 77.60 ms |
| Latência mínima | 4414.66 ms | 62.39 ms |
| Latência máxima | 6754.56 ms | 7250.22 ms |
| Taxa de acerto de cache | 0% | 66.7% (4 de 6) |

## Consolidado de Tokens

| Métrica | Sessão A (sem cache) | Sessão B (com cache) |
| --- | --- | --- |
| Total prompt tokens | 6122 | 2057 |
| Total output tokens | 503 | 195 |
| Total tokens consumidos (API) | 6625 | 2252 |
| Tokens totais economizados (cache) | 0 | 4338 |
| Tokens médios por requisição (real) | 1104.17 | 375.33 |
| Redução de consumo de tokens vs Sessão A | — | -66,0% |

## Observações

- **Redução de latência em cache hits:** as respostas servidas via cache semântico na Sessão B caem de uma faixa de ~4.4–7.3 s (miss) para ~62–106 ms (hit), uma redução de **~98,6%** na latência média.
- **Latência média geral 61% menor:** mesmo considerando os 2 misses da Sessão B, a média geral (2078 ms) é bem inferior à Sessão A (5335 ms), evidenciando o ganho líquido do cache.
- **Misses na Sessão B são levemente mais lentos** que os da Sessão A (6079 ms vs 5335 ms) — possivelmente overhead de checagem/gravação no cache semântico antes de retornar a resposta, mas esse custo é amplamente compensado pelos hits subsequentes.
- **Reuso semântico funcionando:** perguntas com fraseado diferente ("What's my account balance?", "How much money do I have in my account?") geraram cache hit na Sessão B, confirmando correspondência semântica (não apenas exata) do cache com `cache_scope = specific`.
