# Test Suite Authoring Guide

## Format

Each test case is a single JSON object on one line in a `.jsonl` file.
See `schema.json` for the complete JSON Schema.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, format: `<suite>-<number>` (e.g. `sarcasm-001`) |
| `content` | string | The text content to be evaluated by moderation systems |
| `language` | string | `en`, `zh`, or `mixed` |
| `ground_truth` | object | Expected moderation outcome (see below) |
| `metadata` | object | Test case metadata (see below) |

### Ground Truth

| Field | Required | Description |
|-------|----------|-------------|
| `harm_category` | yes | Canonical harm category or `null` for benign |
| `severity` | yes | `benign`, `borderline`, `severe`, `critical` |
| `expected_action` | yes | `allow`, `flag_for_review`, `remove`, `remove_and_escalate` |
| `rationale` | no | Why this is the correct label |
| `annotator_agreement` | no | 0.0-1.0, how much human annotators agree |

### Metadata

| Field | Required | Description |
|-------|----------|-------------|
| `edge_case_type` | yes | Which test suite this belongs to |
| `cultural_context` | no | Cultural context tag |
| `requires_thread_context` | no | Whether full thread context is needed |
| `platform_specific` | no | Platform name if platform-specific |
| `difficulty` | no | `easy`, `medium`, `hard`, `adversarial` |

## Harm Categories

Canonical categories (from `src/taxonomy/category_registry.py`):
- `hate_speech`
- `harassment`
- `violence`
- `csam` (child sexual abuse material)
- `self_harm`
- `misinformation`
- `spam`
- `sexual_content`
- `dangerous_activities`
- `privacy_violation`

## Severity Levels

- **benign**: No policy violation
- **borderline**: Ambiguous, reasonable reviewers disagree
- **severe**: Clear violation
- **critical**: Requires immediate action + escalation

## Writing Good Edge Cases

1. **Start with the ambiguity**: What makes this case hard to classify?
2. **Provide context**: Include thread context, author history, platform type
3. **Honest ground truth**: Set realistic `annotator_agreement` — low agreement IS the point for edge cases
4. **Rationale matters**: Explain WHY this is the correct label
5. **Test both directions**: Include cases where systems over-flag AND under-flag

## Validation

```bash
# Validate test cases against schema
python -m jsonschema -i test_suites/edge_cases/sarcasm_vs_hate.jsonl test_suites/schema.json
```
