from dataclasses import dataclass


@dataclass
class RequestMetric:
    question: str
    cache_hit: bool
    latency_ms: float
    # "specific" (scoped to one account_id) or "general" (shared across every
    # customer) -- empty string when the cache was bypassed (use_cache=False).
    cache_scope: str = ""
    llm_call_latency_ms: float = 0.0
    prompt_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tokens_saved: int = 0


class MetricsCollector:
    """Collects per-request metrics so cache HITs and real agent runs can be
    compared on latency and token consumption, broken down by whether the
    cache entry was account-specific or general/shared."""

    def __init__(self):
        self.records: list[RequestMetric] = []

    def record(self, metric: RequestMetric):
        self.records.append(metric)

    @staticmethod
    def _avg(values):
        return sum(values) / len(values) if values else 0.0

    def summary_dict(self) -> dict:
        """JSON-friendly aggregate, used by the GET /stats endpoint."""
        hits = [r for r in self.records if r.cache_hit]
        misses = [r for r in self.records if not r.cache_hit]
        specific_hits = [r for r in hits if r.cache_scope == "specific"]
        general_hits = [r for r in hits if r.cache_scope == "general"]

        avg_hit = self._avg([r.latency_ms for r in hits])
        avg_miss = self._avg([r.latency_ms for r in misses])

        return {
            "hits": len(hits),
            "misses": len(misses),
            "hits_specific": len(specific_hits),
            "hits_general": len(general_hits),
            "avg_hit_latency_ms": avg_hit,
            "avg_miss_latency_ms": avg_miss,
            "speedup": (avg_miss / avg_hit) if avg_hit else 0.0,
            "tokens_consumed": sum(r.total_tokens for r in misses),
            "tokens_saved": sum(r.tokens_saved for r in hits),
            "tokens_saved_specific": sum(r.tokens_saved for r in specific_hits),
            "tokens_saved_general": sum(r.tokens_saved for r in general_hits),
        }

    def print_summary(self):
        s = self.summary_dict()

        print("\n" + "=" * 60)
        print("METRICS SUMMARY (LATENCY & TOKENS)")
        print("=" * 60)
        print(f"{'':22}{'CACHE HIT':>16}{'AGENT RUN (MISS)':>18}")
        print(f"{'Requests':22}{s['hits']:>16}{s['misses']:>18}")
        print(f"{'  of which specific':22}{s['hits_specific']:>16}")
        print(f"{'  of which general':22}{s['hits_general']:>16}")
        print(f"{'Avg latency (ms)':22}{s['avg_hit_latency_ms']:>16.2f}{s['avg_miss_latency_ms']:>18.2f}")
        print(f"{'Tokens consumed':22}{0:>16}{s['tokens_consumed']:>18}")
        print(f"{'Tokens saved':22}{s['tokens_saved']:>16}{0:>18}")
        print("-" * 60)
        if s["avg_hit_latency_ms"] and s["avg_miss_latency_ms"]:
            print(f"Speedup (miss/hit): {s['speedup']:.1f}x faster on cache hit")
        print(f"Total tokens saved by cache: {s['tokens_saved']}")
        print("=" * 60)
