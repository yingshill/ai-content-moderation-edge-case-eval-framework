"""Taxonomy module: harm categories and severity definitions."""

from .category_registry import (
    HARM_CATEGORIES,
    HarmCategory,
    VALID_CATEGORIES,
    get_category,
    validate_category,
)
from .severity import Severity, severity_distance

__all__ = [
    "HARM_CATEGORIES",
    "HarmCategory",
    "VALID_CATEGORIES",
    "get_category",
    "validate_category",
    "Severity",
    "severity_distance",
]
