"""Google Perspective API adapter."""

from __future__ import annotations

import os
from typing import Any

import httpx

from .base import ModerationProvider, ModerationRequest, ModerationResult

_ATTR_MAP: dict[str, str] = {
    "TOXICITY": "toxicity",
    "SEVERE_TOXICITY": "toxicity",
    "IDENTITY_ATTACK": "hate_speech",
    "INSULT": "harassment",
    "PROFANITY": "profanity",
    "THREAT": "violence",
    "SEXUALLY_EXPLICIT": "sexual_content",
}

_DEFAULT_ATTRIBUTES = [
    "TOXICITY",
    "SEVERE_TOXICITY",
    "IDENTITY_ATTACK",
    "INSULT",
    "PROFANITY",
    "THREAT",
]


class PerspectiveProvider(ModerationProvider):
    """Adapter for Google Perspective API."""

    def __init__(
        self,
        api_key: str | None = None,
        attributes: list[str] | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("PERSPECTIVE_API_KEY", "")
        self._attributes = attributes or _DEFAULT_ATTRIBUTES
        self._client = httpx.AsyncClient(timeout=30.0)

    def provider_name(self) -> str:
        return "perspective"

    async def moderate(self, request: ModerationRequest) -> ModerationResult:
        url = (
            "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
            f"?key={self._api_key}"
        )
        payload = {
            "comment": {"text": request.content},
            "languages": [request.language],
            "requestedAttributes": {attr: {} for attr in self._attributes},
        }
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        scores: dict[str, float] = {}
        for attr, info in data.get("attributeScores", {}).items():
            scores[attr] = info["summaryScore"]["value"]

        top_attr = max(scores, key=scores.get) if scores else None  # type: ignore[arg-type]
        top_score = scores.get(top_attr or "", 0.0)

        harm = _ATTR_MAP.get(top_attr or "") if top_attr else None
        severity = self._score_to_severity(top_score)
        should_escalate = severity == "borderline" or (
            0.4 < top_score < 0.7
        )

        return ModerationResult(
            harm_category=harm,
            severity=severity,
            confidence=top_score,
            should_escalate=should_escalate,
            escalation_context=(
                {
                    "content_snippet": request.content[:200],
                    "harm_category_prediction": harm,
                    "confidence_score": top_score,
                    "recommended_action": "flag_for_review",
                }
                if should_escalate
                else None
            ),
            explanation=(
                f"Top attribute: {top_attr} ({top_score:.3f}). "
                f"All scores: {', '.join(f'{k}={v:.3f}' for k, v in scores.items())}."
            ),
            raw_response=data,
            latency_ms=0.0,
        )

    @staticmethod
    def _score_to_severity(score: float) -> str:
        if score >= 0.90:
            return "critical"
        if score >= 0.75:
            return "severe"
        if score >= 0.50:
            return "borderline"
        return "benign"
