"""Tests for moderation provider adapters."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.providers.base import (
    ModerationProvider,
    ModerationRequest,
    ModerationResult,
)
from src.providers.openai_mod import OpenAIModerationProvider
from src.providers.perspective import PerspectiveProvider
from src.providers.llm_judge import LLMJudgeProvider


# --- ModerationResult validation ---


class TestModerationResult:
    def test_valid_result(self):
        result = ModerationResult(
            harm_category="harassment",
            severity="borderline",
            confidence=0.75,
            should_escalate=True,
            escalation_context={"content_snippet": "test"},
            explanation="Test explanation",
            raw_response={},
            latency_ms=100.0,
        )
        assert result.severity == "borderline"
        assert result.expected_action == "flag_for_review"

    def test_benign_result_action(self):
        result = ModerationResult(
            harm_category=None,
            severity="benign",
            confidence=0.1,
            should_escalate=False,
            escalation_context=None,
            explanation="Nothing found",
            raw_response={},
            latency_ms=50.0,
        )
        assert result.expected_action == "allow"

    def test_critical_result_action(self):
        result = ModerationResult(
            harm_category="csam",
            severity="critical",
            confidence=0.99,
            should_escalate=True,
            escalation_context={},
            explanation="Critical content",
            raw_response={},
            latency_ms=50.0,
        )
        assert result.expected_action == "remove_and_escalate"

    def test_invalid_severity_raises(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            ModerationResult(
                harm_category="test",
                severity="unknown",
                confidence=0.5,
                should_escalate=False,
                escalation_context=None,
                explanation="",
                raw_response={},
                latency_ms=0.0,
            )

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            ModerationResult(
                harm_category="test",
                severity="benign",
                confidence=1.5,
                should_escalate=False,
                escalation_context=None,
                explanation="",
                raw_response={},
                latency_ms=0.0,
            )

    def test_negative_confidence_raises(self):
        with pytest.raises(ValueError, match="Confidence must be 0-1"):
            ModerationResult(
                harm_category="test",
                severity="benign",
                confidence=-0.1,
                should_escalate=False,
                escalation_context=None,
                explanation="",
                raw_response={},
                latency_ms=0.0,
            )


# --- ModerationRequest ---


class TestModerationRequest:
    def test_defaults(self):
        req = ModerationRequest(content="Hello world")
        assert req.language == "en"
        assert req.context == {}
        assert req.policy_profile is None

    def test_with_policy(self):
        req = ModerationRequest(
            content="Test",
            language="zh",
            policy_profile="rednote",
        )
        assert req.policy_profile == "rednote"
        assert req.language == "zh"


# --- OpenAI Provider ---


class TestOpenAIModerationProvider:
    @pytest.mark.asyncio
    async def test_moderate_flagged(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{
                "categories": {
                    "harassment": True,
                    "hate": False,
                    "violence": False,
                },
                "category_scores": {
                    "harassment": 0.92,
                    "hate": 0.1,
                    "violence": 0.05,
                },
            }]
        }
        mock_response.raise_for_status = MagicMock()

        provider = OpenAIModerationProvider(api_key="test-key")
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_response)

        request = ModerationRequest(content="offensive content")
        result = await provider.moderate(request)

        assert result.harm_category == "harassment"
        assert result.severity == "severe"  # 0.92 >= 0.80
        assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_moderate_benign(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{
                "categories": {
                    "harassment": False,
                    "hate": False,
                },
                "category_scores": {
                    "harassment": 0.02,
                    "hate": 0.01,
                },
            }]
        }
        mock_response.raise_for_status = MagicMock()

        provider = OpenAIModerationProvider(api_key="test-key")
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_response)

        request = ModerationRequest(content="hello friend")
        result = await provider.moderate(request)

        assert result.severity == "benign"

    def test_provider_name(self):
        provider = OpenAIModerationProvider(api_key="test")
        assert provider.provider_name() == "openai"

    @pytest.mark.asyncio
    async def test_close(self):
        provider = OpenAIModerationProvider(api_key="test")
        provider._client = AsyncMock()
        provider._client.aclose = AsyncMock()
        await provider.close()
        provider._client.aclose.assert_called_once()


# --- LLM Judge Provider ---


class TestLLMJudgeProvider:
    def test_provider_name_anthropic(self):
        provider = LLMJudgeProvider(backend="anthropic", api_key="test")
        assert "anthropic" in provider.provider_name()

    def test_provider_name_openai(self):
        provider = LLMJudgeProvider(backend="openai", api_key="test")
        assert "openai" in provider.provider_name()

    def test_parse_valid_json(self):
        raw = json.dumps({
            "harm_category": "hate_speech",
            "severity": "severe",
            "confidence": 0.9,
            "should_escalate": True,
            "explanation": "Contains slurs",
        })
        result = LLMJudgeProvider._parse_response(raw)
        assert result["harm_category"] == "hate_speech"
        assert result["severity"] == "severe"

    def test_parse_json_with_markdown_fences(self):
        raw = "```json\n{\"harm_category\": null, \"severity\": \"benign\", \"confidence\": 0.1, \"should_escalate\": false, \"explanation\": \"Safe\"}\n```"
        result = LLMJudgeProvider._parse_response(raw)
        assert result["severity"] == "benign"

    def test_parse_invalid_json_fallback(self):
        raw = "This is not JSON at all"
        result = LLMJudgeProvider._parse_response(raw)
        assert result["severity"] == "benign"
        assert result["should_escalate"] is True  # Fallback escalates
        assert "Failed to parse" in result["explanation"]

    def test_build_user_message_basic(self):
        provider = LLMJudgeProvider(backend="anthropic", api_key="test")
        request = ModerationRequest(content="Test content")
        msg = provider._build_user_message(request)
        assert "Test content" in msg

    def test_build_user_message_with_context(self):
        provider = LLMJudgeProvider(backend="anthropic", api_key="test")
        request = ModerationRequest(
            content="Test",
            language="zh",
            context={"platform": "rednote"},
            policy_profile="rednote",
        )
        msg = provider._build_user_message(request)
        assert "rednote" in msg
        assert "zh" in msg


# --- Perspective Provider ---


class TestPerspectiveProvider:
    def test_provider_name(self):
        provider = PerspectiveProvider(api_key="test")
        assert provider.provider_name() == "perspective"

    @pytest.mark.asyncio
    async def test_moderate_toxic(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "attributeScores": {
                "TOXICITY": {"summaryScore": {"value": 0.92}},
                "SEVERE_TOXICITY": {"summaryScore": {"value": 0.85}},
                "IDENTITY_ATTACK": {"summaryScore": {"value": 0.3}},
            }
        }
        mock_response.raise_for_status = MagicMock()

        provider = PerspectiveProvider(api_key="test-key")
        provider._client = AsyncMock()
        provider._client.post = AsyncMock(return_value=mock_response)

        request = ModerationRequest(content="toxic content")
        result = await provider.moderate(request)

        assert result.harm_category == "toxicity"
        assert result.severity == "critical"  # 0.92 >= 0.90
