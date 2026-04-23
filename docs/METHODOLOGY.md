# Evaluation Methodology

## Overview

This framework evaluates AI content moderation systems across five dimensions:
**accuracy**, **calibration**, **cultural sensitivity**, **handoff quality**, and **explanation quality**.

Unlike standard NLP benchmarks that focus on accuracy alone, we emphasize the *margins* — edge cases where moderation systems are most likely to fail and where failures have the highest impact.

## Test Design Principles

### 1. Edge-Case First

We deliberately avoid easy cases (except baselines for sanity checking). Our test suites target:
- **Ambiguity**: Cases where reasonable human annotators disagree
- **Context-dependence**: Cases requiring thread/platform/cultural context
- **Adversarial framing**: Content designed to evade or trigger moderation systems

### 2. Ground Truth as Distribution

For edge cases, ground truth is not binary. We use:
- `expected_action`: The *most defensible* moderation action
- `annotator_agreement`: How much humans agree (0.0–1.0)
- `rationale`: Why this label, acknowledging the ambiguity

A system that flags a case with `annotator_agreement: 0.4` for human review is arguably *better* than one that makes a confident binary decision.

### 3. Cross-Lingual Evaluation

The `cultural_context_zh_en` suite specifically tests whether systems apply consistent quality across languages. We measure **Cultural Bias Delta** — the F1 difference between English and Chinese test cases — to quantify systematic bias.

## Metrics Deep-Dive

### Classification Metrics

Standard precision, recall, and F1 computed per harm category, then aggregated:
- **Macro F1**: Unweighted average across categories (treats rare categories equally)
- **Micro F1**: Weighted by category frequency (reflects overall volume)

### Expected Calibration Error (ECE)

Measures whether a system's confidence scores match its actual accuracy:
- Bin predictions by confidence (10 bins)
- For each bin: |avg_confidence - avg_accuracy|
- ECE = weighted average of bin errors

A well-calibrated system saying "70% confident" should be correct ~70% of the time.

### Handoff Metrics

- **Trigger Rate**: % of cases escalated to human review
- **Trigger Precision**: Among escalated cases, what % genuinely needed humans?
- **Trigger Recall**: Among cases needing humans, what % were escalated?
- **Context Completeness**: When escalating, how much useful context is provided?

### Inter-Provider Agreement

Cohen's Kappa between provider pairs measures whether providers make similar mistakes (suggesting shared blind spots) or complementary ones (suggesting ensemble value).

## Platform Policy Profiles

Different platforms have different community guidelines. The same content might be:
- **Allowed** on Platform A (newsworthy exception)
- **Flagged** on Platform B (stricter minor safety policy)
- **Removed** on Platform C (zero tolerance for borderline content)

Policy profiles (YAML files in `policies/`) map platform-specific rules to our universal harm taxonomy, enabling cross-platform comparison.

## Limitations

1. **Text-only**: Current framework evaluates text content only. Multi-modal (image, video, audio) evaluation is future work.
2. **Static test suites**: Edge cases evolve as culture and language change. Test suites need regular updates.
3. **LLM-as-judge bias**: Using LLMs to evaluate LLMs introduces potential correlation in errors.
4. **English/Chinese only**: Current test suites cover en + zh. Other languages need community contribution.
