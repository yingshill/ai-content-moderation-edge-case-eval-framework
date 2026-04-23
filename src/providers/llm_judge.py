"""LLM-as-judge moderation adapter (Claude / GPT-4o)."""

from __future__ import annotations

import json
import os
from typing import Any

from .base import ModerationProvider, ModerationRequest, ModerationResult
from ..utils.logging import get_logger

logger = get_logger("providers.llm_judge")

_SYSTEM_PROMPT = """You are an expert content moderation evaluator. Analyze the given content and return a JSON object with exactly these fields:

{
  "harm_category": "<category or null if benign>",
  "severity": "<benign|borderline|severe|critical>",
  "confidence": <0.0-1.0>,
  "should_escalate": <true|false>,
  "explanation": "<brief rationale citing specific content elements>"
}

Harm categories: harassment, hate_speech, violence, self_harm, sexual_content, csam, misinformation, spam, dangerous_activities, toxicity, profanity, other.

Consider:
- Cultural and linguistic context
- Sarcasm, irony, and tone
- Whether content discusses harm vs promotes it
- Author intent signals from context
- Platform-specific norms if policy_profile is provided

Respond ONLY with valid JSON. No markdown fences."""


class LLMJudgeProvider(ModerationProvider):
    """Uses an LLM (Claude or GPT-4o) as a moderation judge."""

    def __init__(
        self,
        backend: str = "anthropic",  # "anthropic" or "openai"
        model: str | None = None,
        api_key: str | None = None,
        rate_limit_rpm: int = 30,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ) -> None:
        super().__init__(rate_limit_rpm=rate_limit_rpm, max_retries=max_retries, backoff_base=backoff_base)
        self._backend = backend
        if backend == "anthropic":
            self._model = model or "claude-sonnet-4-20250514"
            self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        else:
            self._model = model or "gpt-4o"
            self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

        # Lazily initialized clients (one per provider instance)
        self._anthropic_client: Any = None
        self._openai_client: Any = None
        logger.info(f"initialized backend={self._backend} model={self._model}")

    def provider_name(self) -> str:
        return f"llm_judge_{self._backend}_{self._model}"

    async def moderate(self, request: ModerationRequest) -> ModerationResult:
        user_msg = self._build_user_message(request)

        if self._backend == "anthropic":
            raw = await self._call_anthropic(user_msg)
        else:
            raw = await self._call_openai(user_msg)

        parsed = self._parse_response(raw)

        return ModerationResult(
            harm_category=parsed.get("harm_category"),
            severity=parsed.get("severity", "benign"),
            confidence=float(parsed.get("confidence", 0.5)),
            should_escalate=bool(parsed.get("should_escalate", False)),
            escalation_context=(
                {
                    "content_snippet": request.content[:200],
                    "harm_category_prediction": parsed.get("harm_category"),
                    "confidence_score": parsed.get("confidence"),
                    "recommended_action": "flag_for_review",
                }
                if parsed.get("should_escalate")
                else None
            ),
            explanation=parsed.get("explanation", "No explanation provided."),
            raw_response={"model": self._model, "parsed": parsed, "raw_text": raw},
            latency_ms=0.0,
        )

    def _build_user_message(self, request: ModerationRequest) -> str:
        parts = [f"Content to evaluate:\n{request.content}"]
        if request.context:
            parts.append(f"\nContext: {json.dumps(request.context)}")
        if request.policy_profile:
            parts.append(f"\nPolicy profile: {request.policy_profile}")
        if request.language != "en":
            parts.append(f"\nContent language: {request.language}")
        return "\n".join(parts)

    async def _call_anthropic(self, user_msg: str) -> str:
        if self._anthropic_client is None:
            import anthropic
            self._anthropic_client = anthropic.AsyncAnthropic(api_key=self._api_key)

        message = await self._anthropic_client.messages.create(
            model=self._model,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text

    async def _call_openai(self, user_msg: str) -> str:
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=self._api_key)

        response = await self._openai_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=512,
            temperature=0.0,
        )
        return response.choices[0].message.content or ""

    async def close(self) -> None:
        """Clean up LLM client resources."""
        if self._anthropic_client is not None:
            await self._anthropic_client.close()
            self._anthropic_client = None
        if self._openai_client is not None:
            await self._openai_client.close()
            self._openai_client = None

    @staticmethod
    def _parse_response(raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"parse_failed raw_length={len(raw_text)}")
            return {
                "harm_category": None,
                "severity": "benign",
                "confidence": 0.0,
                "should_escalate": True,
                "explanation": f"Failed to parse LLM response: {raw_text[:200]}",
            }
