"""Tests for taxonomy module."""

import pytest
from src.taxonomy.category_registry import HARM_CATEGORIES, HarmCategory
from src.taxonomy.severity import SEVERITY_LEVELS, SeverityLevel, severity_requires_escalation


class TestHarmCategories:
    def test_all_categories_have_required_fields(self):
        for cat_id, cat in HARM_CATEGORIES.items():
            assert cat.id == cat_id
            assert cat.name
            assert cat.description

    def test_known_categories_exist(self):
        expected = [
            "hate_speech", "harassment", "violence", "csam",
            "self_harm", "misinformation", "spam", "sexual_content",
        ]
        for cat_id in expected:
            assert cat_id in HARM_CATEGORIES, f"Missing category: {cat_id}"


class TestSeverity:
    def test_severity_ordering(self):
        assert SEVERITY_LEVELS["benign"].level < SEVERITY_LEVELS["borderline"].level
        assert SEVERITY_LEVELS["borderline"].level < SEVERITY_LEVELS["severe"].level
        assert SEVERITY_LEVELS["severe"].level < SEVERITY_LEVELS["critical"].level

    def test_critical_requires_escalation(self):
        assert severity_requires_escalation("critical") is True

    def test_benign_no_escalation(self):
        assert severity_requires_escalation("benign") is False
