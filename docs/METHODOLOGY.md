# Evaluation Methodology

## Overview

This framework evaluates AI content moderation systems on **edge cases** — ambiguous content that exposes weaknesses in automated moderation. Evaluation is multi-dimensional, measuring not just accuracy but calibration, cultural sensitivity, handoff quality, and explanation quality.

## Architecture

```
Test Suites (JSONL) → Eval Runner → Providers (parallel) → Scoring → Reports
     │                      │              │                  │
     │                      │              │                  ├─ Classification Metrics
     ├─ Edge cases           ├─ Async       ├─ OpenAI Mod      ├─ Calibration Error (ECE)
     ├─ Platform-specific    ├─ Rate limit  ├─ Perspective     ├─ Handoff Metrics
     ├─ Cross-platform       ├─ Retry       ├─ LLM Judge       ├─ Action Accuracy
     └─ Baselines            └─ Logging     └─ (extensible)    ├─ Rubric Score (5-dim)
                                                              └─ Inter-Provider Agreement
```

## Evaluation Dimensions

### 1. Classification Accuracy

- **Macro F1**: Unweighted mean F1 across all harm categories. Treats rare categories equally.
- **Micro F1**: Global TP/FP/FN aggregation. Reflects overall volume-weighted performance.
- **Per-category breakdown**: Precision, recall, F1, and support for each harm category.

### 2. Calibration (Expected Calibration Error)

Measures whether a model's confidence scores reflect its actual accuracy. A well-calibrated model with 80% confidence should be correct ~80% of the time.

- **Implementation**: Binned ECE with 10 bins.
- **Target**: ECE < 0.10 for production readiness.

### 3. Action Accuracy

Measures whether the predicted moderation action matches the ground truth.

**Action mapping from severity:**
| Severity | Default Action |
|----------|---------------|
| benign | allow |
| borderline | flag_for_review |
| severe | remove |
| critical | remove_and_escalate |

Each test case includes an `expected_action` field. The framework compares the provider's predicted action against this ground truth.

### 4. Human-AI Handoff Quality

Evaluates the escalation decision-making:

- **Trigger Rate**: What fraction of cases are escalated to human review.
- **Trigger Precision**: Of escalated cases, how many truly needed human review.
- **Trigger Recall**: Of cases needing human review, how many were caught.
- **Context Completeness**: Whether escalation contexts include required fields (content snippet, predicted category, confidence score, recommended action).

**Escalation heuristic**: A case should be escalated when:
- Severity is "borderline" or "critical"
- Annotator agreement is below 0.6 (indicating genuinely ambiguous content)

### 5. Rubric Score (5-Dimension Weighted)

The core differentiator of this framework. Each provider is scored on 5 dimensions using a YAML-configurable rubric:

| Dimension | Weight | Source Metric |
|-----------|--------|---------------|
| Accuracy | 0.25 | Macro F1 |
| Calibration | 0.20 | 1.0 - ECE |
| Cultural Sensitivity | 0.20 | Accuracy on culturally-tagged cases |
| Handoff Quality | 0.20 | Mean of precision, recall, context completeness |
| Explanation Quality | 0.15 | Heuristic scoring of explanation text |

**Rubric scoring**: Each dimension is mapped to a 1-5 integer score:
| Metric Range | Rubric Score |
|-------------|-------------|
| >= 0.90 | 5 (Excellent) |
| >= 0.75 | 4 (Good) |
| >= 0.50 | 3 (Fair) |
| >= 0.25 | 2 (Poor) |
| < 0.25 | 1 (Very Poor) |

The final normalized score (0.0 - 1.0) is the weighted sum divided by the maximum possible.

### 6. Inter-Provider Agreement

- **Cohen's Kappa**: Pairwise agreement between providers, correcting for chance.
- Computed for all C(n,2) provider pairs.
- Kappa > 0.6 indicates substantial agreement; < 0.4 indicates meaningful disagreement worth investigating.

## Test Suite Design

### Edge Case Categories

| Suite | Cases | Challenge |
|-------|-------|-----------|
| sarcasm_vs_hate | 10 | Distinguishing ironic from genuine hostility |
| cultural_context_zh_en | 8 | Cross-cultural interpretation differences |
| metaphorical_violence | 7 | Figurative vs. literal threat language |
| ai_generated_self_reference | 6 | AI discussing its own content policies |
| coded_language | 7 | Dog whistles and evolving euphemisms |
| reclaimed_slurs | 8 | In-group reclamation vs. out-group usage |
| news_reporting_vs_glorification | 8 | Journalism about violence vs. promotion |
| minors_safety_boundary | 7 | Age-appropriate content boundary cases |

### Platform-Specific Suites

| Platform | Suite | Cases | Focus |
|----------|-------|-------|-------|
| TikTok | duet_context | 8 | Duet/stitch context changes meaning |
| TikTok | audio_meme | 7 | Audio layer contradicts visual |
| TikTok | creator_fund_spam | 6 | Engagement farming vs. genuine content |
| RedNote | zhongcao_vs_ad | 5 | Organic recommendations vs. undisclosed ads |
| RedNote | daigou_gray_zone | 5 | Cross-border commerce gray areas |
| RedNote | medical_beauty | 5 | Medical claims in beauty content |

### Ground Truth Schema

Each test case includes:
```json
{
  "id": "unique-id",
  "content": "The text to moderate",
  "language": "en",
  "context": {},
  "ground_truth": {
    "harm_category": "harassment|null",
    "severity": "benign|borderline|severe|critical",
    "expected_action": "allow|flag_for_review|remove|remove_and_escalate",
    "annotator_agreement": 0.0-1.0
  },
  "metadata": {
    "edge_case_type": "sarcasm|cultural|...",
    "difficulty": "medium|hard|expert"
  }
}
```

## Running Evaluations

```bash
# Basic evaluation
python scripts/run_eval.py -s test_suites/edge_cases/ -c configs/eval_config.yaml

# With platform policy
python scripts/run_eval.py -s test_suites/platform_tiktok/ -p tiktok

# Compare providers
python scripts/compare_providers.py outputs/eval_latest.json

# Cross-platform comparison
python scripts/compare_platforms.py -p tiktok -p rednote

# Generate reports
python scripts/generate_report.py outputs/eval_latest.json -f both
```

## Extending the Framework

### Adding a New Provider

1. Create `src/providers/your_provider.py`
2. Subclass `ModerationProvider`
3. Implement `moderate()` and `provider_name()`
4. Override `close()` if using HTTP clients
5. Add to `_build_providers()` in `scripts/run_eval.py`
6. Add config section in `configs/eval_config.yaml`

### Adding a New Test Suite

1. Create a JSONL file in `test_suites/`
2. Follow the ground truth schema above
3. Validate with `python scripts/validate_suites.py`
4. Ensure all `harm_category` values exist in `src/taxonomy/category_registry.py`

### Adding a New Rubric Dimension

1. Add the dimension to `rubrics/default.yaml`
2. Ensure weights sum to 1.0
3. Add the metric computation in `src/eval_runner.py`
