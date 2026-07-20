import json
import re
import time
from typing import Optional

from redis import Redis
from redis.commands.search.query import Query
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

from app import config

# RediSearch/Valkey Search TAG fields treat these characters as syntax, so
# any tag value containing them (e.g. account ids like "demo-001") must be
# backslash-escaped before being dropped into a query string.
_TAG_SPECIAL_CHARS = re.compile(r"""([,.<>{}\[\]"':;!@#$%^&*()\-+=~ ])""")


def _escape_tag(value: str) -> str:
    return _TAG_SPECIAL_CHARS.sub(r"\\\1", value)


class KnnSemanticCache:
    """redisvl's SemanticCache extension issues FT.SEARCH range queries
    (`VECTOR_RANGE`), which Valkey Search does not implement -- it only
    supports KNN queries. This is a drop-in replacement that does the
    same threshold-based lookup by running a KNN(1) query and comparing
    the returned vector distance to `distance_threshold` in Python.

    When `scoped=True`, every check()/store() call must pass a `scope_id`
    (e.g. an account_id) -- results are pre-filtered to that scope's TAG
    field before the KNN search runs, so entries from one scope can never
    be returned for another. When `scoped=False`, the cache is a single
    shared pool with no such filter."""

    def __init__(
        self,
        index: SearchIndex,
        vectorizer: HFTextVectorizer,
        distance_threshold: float,
        ttl: int,
        scoped: bool = False,
    ):
        self.index = index
        self.vectorizer = vectorizer
        self.distance_threshold = distance_threshold
        self.ttl = ttl
        self.scoped = scoped

    def check(self, prompt: str, scope_id: Optional[str] = None) -> list[dict]:
        if self.scoped and scope_id is None:
            raise ValueError("scope_id is required for a scoped cache")

        # Valkey Search errors on a KNN query against an empty index instead
        # of returning zero results, so short-circuit before that happens.
        if int(self.index.info().get("num_docs", 0)) == 0:
            return []

        vector = self.vectorizer.embed(prompt, as_buffer=True)

        # Valkey Search errors when RETURN/SORTBY reference the KNN score
        # alias, so we run a bare KNN query -- it comes back pre-sorted by
        # score and includes every hash field, including the alias -- and
        # pick out what we need in Python instead.
        if self.scoped:
            query_str = f"(@scope_id:{{{_escape_tag(scope_id)}}})=>[KNN 1 @prompt_vector $vector AS vector_distance]"
        else:
            query_str = "*=>[KNN 1 @prompt_vector $vector AS vector_distance]"

        query = Query(query_str).dialect(2).paging(0, 1)
        results = self.index.search(query, query_params={"vector": vector})
        if not results.docs:
            return []

        top = results.docs[0]
        distance = float(top.vector_distance)
        if distance > self.distance_threshold:
            print(
                f"🔍 Cache miss: closest entry at distance {distance:.4f} "
                f"> threshold {self.distance_threshold} for '{prompt[:60]}'"
            )
            return []

        return [
            {
                "response": top.response,
                "metadata": json.loads(top.metadata) if getattr(top, "metadata", None) else {},
            }
        ]

    def store(
        self, prompt: str, response: str, metadata: Optional[dict] = None, scope_id: Optional[str] = None
    ) -> None:
        if self.scoped and scope_id is None:
            raise ValueError("scope_id is required for a scoped cache")

        # HASH storage needs the vector as raw float32 bytes, not a Python list.
        vector = self.vectorizer.embed(prompt, as_buffer=True)
        doc = {
            "prompt": prompt,
            "prompt_vector": vector,
            "response": response,
            "metadata": json.dumps(metadata or {}),
            "inserted_at": time.time(),
        }
        if self.scoped:
            doc["scope_id"] = scope_id

        self.index.load([doc], ttl=self.ttl)


def _build_cache(vectorizer: HFTextVectorizer, index_name: str, scoped: bool) -> KnnSemanticCache:
    fields = [
        {"name": "prompt", "type": "text"},
        {"name": "response", "type": "text"},
        {"name": "metadata", "type": "text"},
        {"name": "inserted_at", "type": "numeric"},
        {
            "name": "prompt_vector",
            "type": "vector",
            "attrs": {
                "dims": vectorizer.dims,
                "distance_metric": "cosine",
                "algorithm": "flat",
                "datatype": "float32",
            },
        },
    ]
    if scoped:
        fields.append({"name": "scope_id", "type": "tag"})

    schema = {"index": {"name": index_name, "prefix": index_name}, "fields": fields}
    index = SearchIndex.from_dict(schema, redis_client=Redis.from_url(config.REDIS_URL))
    index.create(overwrite=False)

    return KnnSemanticCache(
        index=index,
        vectorizer=vectorizer,
        distance_threshold=config.DISTANCE_THRESHOLD,
        ttl=config.CACHE_TTL,
        scoped=scoped,
    )


def build_semantic_caches() -> tuple[KnnSemanticCache, KnnSemanticCache]:
    """Builds the two cache pools the app uses:
    - general: shared across every customer -- for answers that don't
      depend on anyone's personal account data (opening hours, "what is a
      trial", general knowledge, ...).
    - specific: scoped per account_id via a TAG filter -- for answers that
      were looked up from one customer's own data (balance, transactions,
      card status, ...) and must never be served to a different customer.
    Both share a single embedding model instance to avoid loading it twice."""
    print("⏳ Initializing lightweight vectorizer to save VRAM...")
    vetorizador = HFTextVectorizer(config.EMBEDDING_MODEL)

    # The vector dims go into the index name so switching embedding models
    # (e.g. 384-dim MiniLM -> 768-dim mpnet) starts a fresh index instead of
    # reusing an existing one whose vector field has the wrong dimensions.
    base_name = f"{config.CACHE_NAME}_{vetorizador.dims}"
    general_cache = _build_cache(vetorizador, f"{base_name}_general", scoped=False)
    specific_cache = _build_cache(vetorizador, f"{base_name}_specific", scoped=True)
    return general_cache, specific_cache
