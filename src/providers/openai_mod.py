"""OpenAI Moderation API adapter."""

from __future__ import annotations

import os
from typing import Any

import httpx

from .base import ModerationProvider, ModerationRequest, ModerationResult

# OpenAI category -> our canonical harm categories
_CATEGORY_MAP: dict[str, str] = {
    "harassment": "harassment",
    "harassment/threatening": "harassment",
    "hate": "hate_speech",
    "hate/threatening": "hate_speech",
    "self-harm": "self_harm",
    "self-harm/intent": "self_harm",
    "self-harm/instructions": "self_harm",
    "sexual": "sexual_content",
    "sexual/minors": "csam",
    "violence": "violence",
    "violence/graphic": "violence",
}

_SEVERITY_THRESHOLDS = {
    "critical": 0.95,
    "severe": 0.80,
    "borderline": 0.50,
}


class OpenAIModerationProvider(ModerationProvider):
    """Adapter for the OpenAI Moderation endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "omni-moderation-latest",
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )

    def provider_name(self) -> str:
        return "openai"

    async def moderate(self, request: ModerationRequest) -> ModerationResult:
        resp = await self._client.post(
            "/moderations",
            json={"input": request.content, "model": self._model},
        )
        resp.raise_for_status()
        data = resp.json()
        result = data["results"][0]

        # Find highest-scoring flagged category
        scores: dict[str, float] = result.get("category_scores", {})
        flagged_cats: dict[str, bool] = result.get("categories", {})

        top_category: str | None = None
        top_score: float = 0.0
        for cat, is_flagged in flagged_cats.items():
            score = scores.get(cat, 0.0)
            if score > top_score:
                top_score = score
                top_category = cat

        harm = _CATEGORY_MAP.get(top_category or "") if top_category else None
        severity = self._score_to_severity(top_score)
        should_escalate = severity in ("borderline", "critical") or top_score < 0.7

        return ModerationResult(
            harm_category=harm,
            severity=severity,
            confidence=top_score,
            should_escalate=should_escalate,
            escalation_context=self._build_escalation_context(
                request, harm, top_score, should_escalate
            ),
            explanation=self._build_explanation(top_category, top_score, flagged_cats),
            raw_response=data,
            latency_ms=0.0,
        )

    @staticmethod
    def _score_to_severity(score: float) -> str:
        for level, threshold in _SEVERITY_THRESHOLDS.items():
            if score >= threshold:
                return level
        return "benign"

    @staticmethod
    def _build_explanation(
        top_cat: str | None, score: float, cats: dict[str, bool]
    ) -> str:
        flagged = [c for c, v in cats.items() if v]
        if not flagged:
            return f"No categories flagged. Highest score: {score:.3f} ({top_cat})."
        return (
            f"Flagged categories: {', '.join(flagged)}. "
            f"Top: {top_cat} ({score:.3f})."
        )

    @staticmethod
    def _build_escalation_context(
        request: ModerationRequest,
        harm: str | None,
        confidence: float,
        should_escalate: bool,
    ) -> dict[str, Any] | None:
        if not should_escalate:
            return None
        return {
            "content_snippet": request.content[:200],
            "harm_category_prediction": harm,
            "confidence_score": confidence,
            "recommended_action": "flag_for_review",
        }
