"""Tests for taxonomy: categories, severity, validation."""

from __future__ import annotations

import pytest

from src.taxonomy.category_registry import (
    HARM_CATEGORIES,
    VALID_CATEGORIES,
    get_category,
    validate_category,
)
from src.taxonomy.severity import Severity, severity_distance


# --- Category Registry ---


class TestCategoryRegistry:
    def test_all_categories_have_required_fields(self):
        for cat_id, cat in HARM_CATEGORIES.items():
            assert cat.id == cat_id
            assert cat.name
            assert cat.description

    def test_dangerous_activities_exists(self):
        """Regression: dangerous_activities must exist (used in daigou_gray_zone.jsonl)."""
        assert "dangerous_activities" in HARM_CATEGORIES
        cat = HARM_CATEGORIES["dangerous_activities"]
        assert cat.name == "Dangerous Activities"

    def test_core_categories_present(self):
        expected = {
            "harassment", "hate_speech", "violence", "self_harm",
            "sexual_content", "csam", "misinformation", "spam",
            "dangerous_activities", "toxicity", "profanity",
        }
        assert expected.issubset(set(HARM_CATEGORIES.keys()))

    def test_get_category_valid(self):
        cat = get_category("harassment")
        assert cat is not None
        assert cat.id == "harassment"

    def test_get_category_invalid(self):
        assert get_category("nonexistent") is None

    def test_validate_category_valid(self):
        assert validate_category("harassment") is True
        assert validate_category("dangerous_activities") is True

    def test_validate_category_none_is_valid(self):
        """None represents benign content."""
        assert validate_category(None) is True

    def test_validate_category_invalid(self):
        assert validate_category("made_up_category") is False

    def test_valid_categories_includes_none(self):
        assert None in VALID_CATEGORIES

    def test_frozen_dataclass(self):
        cat = HARM_CATEGORIES["harassment"]
        with pytest.raises(AttributeError):
            cat.name = "Modified"  # type: ignore


# --- Severity ---


class TestSeverity:
    def test_ordering(self):
        assert Severity.BENIGN < Severity.BORDERLINE
        assert Severity.BORDERLINE < Severity.SEVERE
        assert Severity.SEVERE < Severity.CRITICAL

    def test_from_string_valid(self):
        assert Severity.from_string("benign") == Severity.BENIGN
        assert Severity.from_string("CRITICAL") == Severity.CRITICAL
        assert Severity.from_string("Borderline") == Severity.BORDERLINE

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            Severity.from_string("unknown")

    def test_to_string(self):
        assert Severity.BENIGN.to_string() == "benign"
        assert Severity.CRITICAL.to_string() == "critical"

    def test_severity_distance(self):
        assert severity_distance("benign", "benign") == 0
        assert severity_distance("benign", "critical") == 3
        assert severity_distance("borderline", "severe") == 1
        assert severity_distance("critical", "benign") == 3  # Symmetric

    def test_int_values(self):
        assert int(Severity.BENIGN) == 0
        assert int(Severity.BORDERLINE) == 1
        assert int(Severity.SEVERE) == 2
        assert int(Severity.CRITICAL) == 3
