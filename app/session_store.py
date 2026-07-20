import csv
import time
from pathlib import Path

from app.metrics import RequestMetric

# One CSV per session_id, so each browser session's history (tokens consumed,
# cache reuse, latency) can be inspected independently after the fact.
SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"

_CSV_HEADER = [
    "timestamp",
    "question",
    "cache_hit",
    "cache_scope",
    "latency_ms",
    "prompt_tokens",
    "output_tokens",
    "total_tokens",
    "tokens_saved",
]


def record(session_id: str, metric: RequestMetric) -> None:
    """Append one request's metrics to sessions/<session_id>.csv, creating
    the file (with header) on the session's first request."""
    SESSIONS_DIR.mkdir(exist_ok=True)
    file_path = SESSIONS_DIR / f"{session_id}.csv"
    is_new = not file_path.exists()

    with file_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(_CSV_HEADER)
        writer.writerow(
            [
                time.time(),
                metric.question,
                metric.cache_hit,
                metric.cache_scope,
                f"{metric.latency_ms:.2f}",
                metric.prompt_tokens,
                metric.output_tokens,
                metric.total_tokens,
                metric.tokens_saved,
            ]
        )
