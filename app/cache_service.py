import time
from typing import NamedTuple

from app import config, session_store
from app.bank_agent import TokenUsageCallback, build_bank_agent_executor, run_bank_agent
from app.metrics import MetricsCollector, RequestMetric
from app.semantic_cache import KnnSemanticCache


class AskOutcome(NamedTuple):
    response: str
    metric: RequestMetric


class CacheService:
    """The heart of the article: checks two semantic caches before falling
    back to the (LangChain + mock-data) bank support agent.

    - `specific_cache` is scoped per account_id -- only reusable by the same
      customer, for answers that came from that customer's own account data.
    - `general_cache` is shared across every customer -- for answers that
      don't depend on anyone's account (general FAQ, off-topic questions),
      so one customer's question can serve as a cache hit for a completely
      different one.

    Which store an answer lands in after a MISS is decided automatically,
    based on whether the agent actually used an account tool to answer it
    (see `bank_agent.AgentRunResult.used_account_data`) -- not guessed up
    front from the wording of the question."""

    def __init__(self, general_cache: KnnSemanticCache, specific_cache: KnnSemanticCache, metrics: MetricsCollector):
        self.general_cache = general_cache
        self.specific_cache = specific_cache
        self.metrics = metrics

    def ask_llm(
        self,
        user_prompt: str,
        account_id: str = config.DEFAULT_ACCOUNT_ID,
        use_cache: bool = True,
        session_id: str = "",
    ) -> AskOutcome:
        start_time = time.time()

        if not use_cache:
            # Cache bypassed from the UI toggle -- skip both the read and the
            # write so this request gives a clean, uncached baseline for
            # side-by-side comparison against cached runs.
            print(f"\n🚫 Cache disabled -- calling the bank agent directly for: '{user_prompt}'...")
            return self._handle_cache_miss(user_prompt, account_id, start_time, session_id, store=False)

        # 1. CHECK THE ACCOUNT-SPECIFIC CACHE FIRST
        print(f"\n🔍 Checking specific cache (account={account_id}) for: '{user_prompt}'...")
        specific_result = self.specific_cache.check(prompt=user_prompt, scope_id=account_id)
        if specific_result:
            return self._handle_cache_hit(user_prompt, specific_result, start_time, session_id, cache_scope="specific")

        # 2. FALL BACK TO THE SHARED GENERAL CACHE
        print(f"🔍 Checking general cache for: '{user_prompt}'...")
        general_result = self.general_cache.check(prompt=user_prompt)
        if general_result:
            return self._handle_cache_hit(user_prompt, general_result, start_time, session_id, cache_scope="general")

        return self._handle_cache_miss(user_prompt, account_id, start_time, session_id)

    def _handle_cache_hit(
        self, user_prompt: str, cache_result, start_time: float, session_id: str, cache_scope: str
    ) -> AskOutcome:
        cache_time = (time.time() - start_time) * 1000  # in milliseconds
        print(f"⚡ [CACHE HIT / {cache_scope.upper()}] Response found in cache in {cache_time:.2f} ms!")

        # Tokens NOT spent on this hit = tokens the original agent run
        # consumed, which we stored in the cache metadata at store() time.
        cached_metadata = cache_result[0].get("metadata") or {}
        tokens_saved = int(cached_metadata.get("total_tokens", 0) or 0)
        metric = RequestMetric(
            question=user_prompt,
            cache_hit=True,
            latency_ms=cache_time,
            cache_scope=cache_scope,
            tokens_saved=tokens_saved,
        )
        self._record(session_id, metric)
        return AskOutcome(response=cache_result[0]["response"], metric=metric)

    def _handle_cache_miss(
        self, user_prompt: str, account_id: str, start_time: float, session_id: str, store: bool = True
    ) -> AskOutcome:
        print(f"🥊 [CACHE MISS] No similarity found. Calling the bank agent (Gemini + tools) for account={account_id}...")

        agent_start = time.time()
        agent = build_bank_agent_executor(account_id)
        usage_callback = TokenUsageCallback()
        run_result = run_bank_agent(agent, user_prompt, usage_callback)
        agent_call_time = (time.time() - agent_start) * 1000  # in milliseconds
        agent_response = run_result.response

        total_time = (time.time() - start_time) * 1000  # in milliseconds
        print(f"🧠 Agent responded in {total_time:.2f} ms (agent run: {agent_call_time:.2f} ms).")

        prompt_tokens = usage_callback.prompt_tokens
        output_tokens = usage_callback.output_tokens
        total_tokens = usage_callback.total_tokens
        print(f"🔢 Tokens used -> prompt: {prompt_tokens}, output: {output_tokens}, total: {total_tokens}")

        cache_scope = "specific" if run_result.used_account_data else "general"

        # 3. SAVE TO THE RIGHT CACHE FOR FUTURE QUERIES
        # Store the token counts so a future HIT can report how many were saved.
        if store:
            metadata = {
                "provider": "GOOGLE_GEMINI_LANGCHAIN_AGENT",
                "account_id": account_id,
                "timestamp": str(time.time()),
                "prompt_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }
            if run_result.used_account_data:
                self.specific_cache.store(prompt=user_prompt, response=agent_response, metadata=metadata, scope_id=account_id)
                print(f"💾 Saved to the SPECIFIC cache (account={account_id}) -- used personal account data.")
            else:
                self.general_cache.store(prompt=user_prompt, response=agent_response, metadata=metadata)
                print("💾 Saved to the GENERAL cache -- answer didn't depend on account data, reusable by any customer.")

        metric = RequestMetric(
            question=user_prompt,
            cache_hit=False,
            latency_ms=total_time,
            cache_scope=cache_scope if store else "",
            llm_call_latency_ms=agent_call_time,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        self._record(session_id, metric)
        return AskOutcome(response=agent_response, metric=metric)

    def _record(self, session_id: str, metric: RequestMetric) -> None:
        self.metrics.record(metric)
        if session_id:
            session_store.record(session_id, metric)
