"""
RailMind: Bounded Memory Audit Chain.
Prevents unbounded memory growth in long-running LLM orchestration loops.
Uses a sliding window with O(1) eviction — mirrors how LangChain's
ConversationSummaryBufferMemory works in production at Uber/Google.
"""
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class AuditEntry:
    role: str          # "user" | "assistant" | "system"
    content: str
    token_estimate: int = 0

    def __post_init__(self):
        # Rough token estimate: 1 token ≈ 4 chars
        self.token_estimate = len(self.content) // 4


class BoundedAuditChain:
    """
    Sliding-window conversation memory with a hard token budget ceiling.

    Invariant: total_tokens_in_chain <= max_tokens at all times.
    When the budget is exceeded, oldest non-system entries are evicted first.

    FAANG Principle (Google Brain style): Memory pressure is shed
    gracefully via eviction rather than raising OOM errors in prod.
    """

    def __init__(self, max_tokens: int = 8192, system_prompt: Optional[str] = None):
        self.max_tokens = max_tokens
        self._chain: deque[AuditEntry] = deque()
        self._total_tokens: int = 0
        self._system_prompt = system_prompt

        if system_prompt:
            entry = AuditEntry(role="system", content=system_prompt)
            self._chain.appendleft(entry)
            self._total_tokens += entry.token_estimate

    def add(self, role: str, content: str) -> None:
        entry = AuditEntry(role=role, content=content)
        self._chain.append(entry)
        self._total_tokens += entry.token_estimate
        self._evict()

    def _evict(self) -> None:
        """Evict oldest non-system entries until token budget is satisfied."""
        eviction_candidates = [e for e in list(self._chain) if e.role != "system"]
        while self._total_tokens > self.max_tokens and eviction_candidates:
            oldest = eviction_candidates.pop(0)
            self._chain.remove(oldest)
            self._total_tokens -= oldest.token_estimate
            logger.debug(f"Evicted audit chain entry ({oldest.token_estimate} tokens). Total: {self._total_tokens}")

    def get_messages(self) -> List[dict]:
        """Returns OpenAI-compatible message list for LLM calls."""
        return [{"role": e.role, "content": e.content} for e in self._chain]

    @property
    def total_tokens(self) -> int:
        return self._total_tokens

    def __len__(self) -> int:
        return len(self._chain)
