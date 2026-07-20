# Test Script — Semantic Cache (lang-cache)

Goal: exercise the bank-support demo (`app/bank_agent.py` + mock accounts in
`app/mock_bank_data.py`) to observe, in practice, how the **specific**
(per-account) and **general** (shared) caches reduce token usage and response
latency. Use the chat UI's cache on/off toggle, or the raw `curl` calls below,
to compare the same questions with and without cache.

Prerequisite: service running (`docker compose up -d --build`), API at
`http://localhost:8000`.

Standard call:

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "YOUR_QUESTION_HERE", "account_id": "demo-001", "use_cache": true, "session_id": "test-session"}'
```

Mock accounts available (`app/mock_bank_data.py`): `demo-001` (Alice Silva,
checking), `demo-002` (Marcus Chen, savings), `demo-003` (Priya Nair,
checking), `demo-004` (Diego Alvarez, savings).

## How to measure

1. Check `GET /stats` before starting.
2. Run **Block A (baseline, cache OFF)** — all questions with
   `use_cache: false`. Record `total_tokens` and `latency_ms` for each response.
3. Run **Block B (cache ON)** — same questions, same order, with
   `use_cache: true`. The first occurrence of each "question family" per
   account should be a MISS (written to cache, `cache_scope: "specific"`
   when it used account data); an exact repeat or close paraphrase from the
   **same** account should come back as a HIT.
4. Compare cumulative `tokens_saved` and `latency_ms` (a hit is typically
   orders of magnitude faster than a real Gemini call) via `GET /stats`, or
   by inspecting the per-session log at `sessions/<session_id>.csv`.

---

## Block 1 — Same user, same question repeated (trivial specific-cache HIT)

All calls use `account_id: "demo-001"`.

1. "What is my current balance?" ← MISS, LLM call, stored in the **specific**
   cache scoped to `demo-001`
2. "What is my current balance?" ← HIT (exact repeat)

## Block 2 — Same user, paraphrases (tests semantic match, not just string match)

Still `account_id: "demo-001"`.

3. "What's my account balance?" ← expected HIT of #1 (paraphrase)
4. "How much money do I have in my account?" ← expected HIT of #1
5. "What are my recent transactions?" ← MISS (new question family), stored specific
6. "Can you show me my last transactions?" ← expected HIT of #5
7. "Is my card active?" ← MISS, stored specific
8. "Please block my card, I lost it." ← MISS (different intent — triggers the
   block-card tool), stored specific

## Block 3 — Different users asking the *same* question (specific cache isolation)

Same wording as Block 1/2, but a **different** `account_id`. Because the
specific cache is scoped by `account_id`, these must MISS even though the
question text is identical/similar to one already cached for `demo-001`.

9. "What is my current balance?" with `account_id: "demo-002"` ← MISS
   (isolated from #1 — different account's specific cache)
10. "What is my current balance?" with `account_id: "demo-002"` (repeat) ←
    HIT (now cached for `demo-002` specifically)
11. "What is my current balance?" with `account_id: "demo-003"` ← MISS again
    (a third, still-isolated account)

## Block 4 — General questions shared across users (general-cache HIT across accounts)

Questions that don't require looking up any specific account's data land in
the **general** cache, so a different customer's identical question can be
served as a HIT even though they're a different `account_id`.

12. "Do you offer a savings account?" with `account_id: "demo-001"` ← MISS,
    stored in the **general** cache (no account tool was used)
13. "Do you offer a savings account?" with `account_id: "demo-002"` ← HIT
    (served from the general cache, even though it's a different customer)
14. "What documents do I need to open an account?" with `account_id: "demo-003"`
    ← MISS, stored general
15. "What documents do I need to open an account?" with `account_id: "demo-004"`
    ← HIT (general cache reused across accounts again)

## Block 5 — Related but distinct questions (should be MISS, false-positive check)

16. "How do I close my account?" (any `account_id`) ← should MISS against
    Block 4's "open an account" question — different intent, same topic
17. "What's the difference between checking and savings accounts?" ← MISS,
    distinct from #12

---

## "Production" scenario (mixed accounts, realistic load)

Simulates concurrent customers hitting FAQ-style and account-specific
questions throughout the day. Suggested order (12 calls), all
`use_cache: true`, one shared `session_id` per simulated user:

1. `demo-001`: "What is my current balance?" (MISS, specific, stored)
2. `demo-002`: "What is my current balance?" (MISS, specific — isolated from #1)
3. `demo-001`: "What's my account balance?" (HIT — same as #1)
4. `demo-003`: "Do you offer a savings account?" (MISS, general, stored)
5. `demo-002`: "What is my current balance?" (HIT — same as #2)
6. `demo-004`: "Do you offer a savings account?" (HIT — general cache from #4)
7. `demo-001`: "What are my recent transactions?" (MISS, specific, stored)
8. `demo-003`: "What are my recent transactions?" (MISS — isolated from #7)
9. `demo-002`: "Please block my card, I lost it." (MISS, specific, stored)
10. `demo-001`: "Can you show me my last transactions?" (HIT — same as #7)
... continue mixing accounts and question families up to 12+, varying order.

At the end, compare in `GET /stats`:
- `hits_specific` vs `hits_general`
- cumulative `tokens_saved` vs. tokens that would have been spent if every
  call had been a MISS (Block A baseline)
- `avg_hit_latency_ms` vs `avg_miss_latency_ms`
- and cross-check against each session's row-by-row log in `sessions/*.csv`

## Fine-tuning (optional)

- `config.DISTANCE_THRESHOLD` controls how "similar" a question must be to
  count as a HIT. Testing with a higher threshold should turn Block 5's
  questions into false-positive HITs against Block 4 — a good regression
  test for tuning the ideal value in production.
