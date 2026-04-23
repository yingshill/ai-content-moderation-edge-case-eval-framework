"""Abstract base class for moderation providers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModerationResult:
    """Standardized result from any moderation provider."""

    harm_category: str | None
    severity: str  # benign | borderline | severe | critical
    confidence: float  # 0.0 - 1.0
    should_escalate: bool
    escalation_context: dict[str, Any] | None
    explanation: str
    raw_response: dict[str, Any]
    latency_ms: float
    provider_name: str = ""

    def __post_init__(self) -> None:
        if self.severity not in ("benign", "borderline", "severe", "critical"):
            raise ValueError(f"Invalid severity: {self.severity!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")


@dataclass
class ModerationRequest:
    """Input to a moderation provider."""

    content: str
    content_id: str = ""
    language: str = "en"
    context: dict[str, Any] = field(default_factory=dict)
    policy_profile: str | None = None  # e.g. "tiktok", "rednote"


class ModerationProvider(ABC):
    """Abstract interface for moderation system adapters."""

    @abstractmethod
    async def moderate(self, request: ModerationRequest) -> ModerationResult:
        """Run moderation on a single piece of content."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g. 'openai', 'perspective')."""
        ...

    async def moderate_timed(self, request: ModerationRequest) -> ModerationResult:
        """Run moderation and record wall-clock latency."""
        start = time.perf_counter()
        result = await self.moderate(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.latency_ms = elapsed_ms
        result.provider_name = self.provider_name()
        return result
