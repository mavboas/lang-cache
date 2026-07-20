# lang-cache

A demo of **semantic caching** in front of a **LangChain agent** that simulates
a bank's customer-support backend: instead of caching on exact prompt string
match, it caches on *meaning* — a new question that's semantically similar
enough to one already asked gets served from cache instead of paying for
another agent run against Google Gemini.

## How it works

1. An incoming question is embedded with `sentence-transformers/all-MiniLM-L6-v2`
   (384-dim vectors).
2. Two caches are checked in order, both KNN vector searches (cosine
   distance, threshold `0.30`, tunable via `DISTANCE_THRESHOLD`) against Valkey (`app/semantic_cache.py`):
   - **Specific cache** — filtered by a `scope_id` TAG (the requester's
     `account_id`) before the KNN search runs, so it only ever returns that
     same customer's own previously-cached answers.
   - **General cache** — no filter, shared by every customer.
3. **Cache hit** (either tier) — the stored answer is returned in a few ms,
   no agent/LLM call.
4. **Cache miss** — a LangChain agent (`app/bank_agent.py`) backed by Gemini
   is run. The agent has tools (`app/bank_tools.py`) to look up **mock**
   account data (`app/mock_bank_data.py`): balance, recent transactions, card
   status, and blocking a card. If the agent actually called one of those
   tools to answer, the response is stored in the **specific** cache, scoped
   to that `account_id`; otherwise it's stored in the **general** cache,
   reusable by any customer. Either way the response is returned.

Every request — hit or miss — is recorded per browser session: the chat UI
generates a `session_id` on load (shown in the header) and sends it with each
`/ask` call. The server appends one row per request to
`sessions/<session_id>.csv` (timestamp, question, cache hit/scope, latency,
token counts), so token/latency savings per session can be inspected
afterwards.

This is a **simulation**: all account/balance/transaction data in
`app/mock_bank_data.py` is fake, in-memory, and reset on restart. No real
banking systems, money, or PII are involved.

## Stack

| Component | Role |
|---|---|
| FastAPI (`app/server.py`) | HTTP API + serves the chat UI |
| LangChain (`app/bank_agent.py`, `app/bank_tools.py`) | Tool-calling agent that answers from mock bank data instead of hallucinating |
| Valkey (`valkey/valkey-bundle`) | Vector store for the semantic cache (Redis-compatible fork) |
| Google Gemini (`langchain-google-genai`) | The LLM behind the agent, cached in front of |
| `sessions/*.csv` (`app/session_store.py`) | Per-session log of every request's cache result, latency, and token counts |

## Running it

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY

docker compose up -d --build
```

| URL | What |
|---|---|
| http://localhost:8000 | Chat UI (with a cache on/off toggle for side-by-side comparison) |
| http://localhost:8000/docs | Swagger UI for the API |

## API

- `POST /ask` — `{ "question": "...", "account_id": "demo-001", "use_cache": true, "session_id": "..." }`
  → answer + cache hit/miss + `cache_scope` (`"specific"` | `"general"` | `""`)
  + latency + token counts. `account_id` selects which mock customer's data
  the agent can see (defaults to `demo-001`); `use_cache: false` bypasses
  both the cache read and write, for a clean uncached baseline. When
  `session_id` is set, the request's metrics are also appended to
  `sessions/<session_id>.csv`.
- `GET /accounts` — lists the available mock `account_id`s for the demo (the
  chat UI's "Logged in as" selector, top-left, is populated from this).
- `GET /stats` — running summary (hits, misses, avg latency, tokens saved).
- `GET /health` — liveness check.

## Local development (without Docker)

```bash
pip install -r requirements.txt
# a Valkey/Redis instance must be reachable at REDIS_URL (see app/config.py)
python main.py
```

## Tuning the semantic cache

The embedding model and hit threshold are set in `app/config.py` and can be
overridden with the `EMBEDDING_MODEL` and `DISTANCE_THRESHOLD` env vars.
The defaults (`all-mpnet-base-v2`, threshold `0.30`) were picked from measured
cosine distances against "What is my current balance?":

| Question | MiniLM-L6-v2 | mpnet-base-v2 |
|---|---|---|
| What's my account balance? | 0.162 | 0.147 |
| How much money do I have in my account? | 0.434 | 0.230 |
| What are my recent transactions? *(different intent)* | 0.627 | 0.478 |
| What is my credit card limit? *(different intent)* | 0.649 | 0.424 |

With MiniLM there is no threshold that catches all same-intent paraphrases
without creeping into different-intent territory; mpnet keeps paraphrases
below ~0.23 and different intents above ~0.42, so `0.30` sits safely in the
gap. Every cache miss logs the closest distance found, which makes it easy
to spot near misses and re-tune. Changing the embedding model starts a fresh
index automatically (the vector dimension is part of the index name).
