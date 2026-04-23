"""Tests for provider adapters."""

import pytest
from src.providers.base import ModerationRequest, ModerationResult, SEVERITY_LEVELS


class TestModerationResult:
    def test_valid_result(self):
        result = ModerationResult(
            harm_category="hate_speech",
            severity="borderline",
            confidence=0.7,
            should_escalate=True,
            escalation_context={"content_snippet": "test"},
            explanation="Borderline hate speech detected",
            raw_response={},
            latency_ms=150.0,
        )
        assert result.severity in SEVERITY_LEVELS
        assert 0.0 <= result.confidence <= 1.0

    def test_benign_result(self):
        result = ModerationResult(
            harm_category=None,
            severity="benign",
            confidence=0.95,
            should_escalate=False,
            escalation_context=None,
            explanation="No harmful content detected",
            raw_response={},
            latency_ms=50.0,
        )
        assert result.harm_category is None
        assert not result.should_escalate


class TestModerationRequest:
    def test_basic_request(self):
        req = ModerationRequest(
            content="test content",
            content_id="test-001",
        )
        assert req.content == "test content"
        assert req.language == "en"  # default

    def test_request_with_context(self):
        req = ModerationRequest(
            content="test",
            content_id="test-002",
            language="zh",
            context={"platform_type": "social_media"},
            policy_profile="rednote",
        )
        assert req.language == "zh"
        assert req.policy_profile == "rednote"
