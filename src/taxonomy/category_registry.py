"""Canonical harm category definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HarmCategory:
    """A canonical harm category used across the evaluation framework."""

    id: str
    name: str
    description: str
    examples: tuple[str, ...] = ()
    parent: str | None = None


HARM_CATEGORIES: dict[str, HarmCategory] = {
    "harassment": HarmCategory(
        id="harassment",
        name="Harassment",
        description="Content targeting individuals with hostile, intimidating, or abusive language.",
        examples=("personal attacks", "bullying", "dogpiling"),
    ),
    "hate_speech": HarmCategory(
        id="hate_speech",
        name="Hate Speech",
        description="Content promoting hatred or discrimination against protected groups.",
        examples=("slurs", "dehumanization", "supremacist rhetoric"),
    ),
    "violence": HarmCategory(
        id="violence",
        name="Violence",
        description="Content depicting, promoting, or glorifying physical violence.",
        examples=("threats", "graphic violence", "glorification of attacks"),
    ),
    "self_harm": HarmCategory(
        id="self_harm",
        name="Self-Harm",
        description="Content promoting or providing instructions for self-harm or suicide.",
        examples=("suicide instructions", "self-injury promotion"),
    ),
    "sexual_content": HarmCategory(
        id="sexual_content",
        name="Sexual Content",
        description="Explicit sexual content not suitable for general audiences.",
        examples=("explicit descriptions", "non-consensual content"),
    ),
    "csam": HarmCategory(
        id="csam",
        name="CSAM",
        description="Child sexual abuse material or content sexualizing minors.",
        examples=(),  # No examples for this category
    ),
    "misinformation": HarmCategory(
        id="misinformation",
        name="Misinformation",
        description="Demonstrably false claims presented as fact, especially on health/safety.",
        examples=("medical misinformation", "election disinformation"),
    ),
    "spam": HarmCategory(
        id="spam",
        name="Spam",
        description="Unsolicited commercial or deceptive promotional content.",
        examples=("undisclosed ads", "engagement bait", "scams"),
    ),
    "toxicity": HarmCategory(
        id="toxicity",
        name="Toxicity",
        description="Generally rude, disrespectful, or unreasonable content.",
        examples=("inflammatory language", "bad-faith arguments"),
    ),
    "profanity": HarmCategory(
        id="profanity",
        name="Profanity",
        description="Strong language that may violate platform community standards.",
        examples=("excessive swearing", "vulgar expressions"),
    ),
}


def get_category(category_id: str) -> HarmCategory | None:
    """Look up a harm category by ID."""
    return HARM_CATEGORIES.get(category_id)
