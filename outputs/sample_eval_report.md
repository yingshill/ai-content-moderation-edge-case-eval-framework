# Evaluation Report: eval_a1b2c3d4

**Generated:** 2026-04-22T12:00:00+00:00

## Provider: openai

| Metric | Value |
|--------|-------|
| Test Cases | 10 |
| Macro F1 | 0.723 |
| Micro F1 | 0.800 |
| Calibration Error (ECE) | 0.142 |
| Action Accuracy | 70.0% |
| **Rubric Score (5-dim)** | **0.640** |
| Handoff Trigger Rate | 40.0% |
| Handoff Precision | 0.750 |
| Handoff Recall | 0.600 |
| Context Completeness | 100.0% |

### Per-Category Breakdown

| Category | Precision | Recall | F1 | Support |
|----------|-----------|--------|-----|--------|
| harassment | 0.800 | 0.667 | 0.727 | 6 |
| hate_speech | 0.667 | 1.000 | 0.800 | 2 |

## Provider: llm_judge_anthropic_claude-sonnet-4-20250514

| Metric | Value |
|--------|-------|
| Test Cases | 10 |
| Macro F1 | 0.856 |
| Micro F1 | 0.900 |
| Calibration Error (ECE) | 0.087 |
| Action Accuracy | 80.0% |
| **Rubric Score (5-dim)** | **0.780** |
| Handoff Trigger Rate | 30.0% |
| Handoff Precision | 1.000 |
| Handoff Recall | 0.600 |
| Context Completeness | 100.0% |

### Per-Category Breakdown

| Category | Precision | Recall | F1 | Support |
|----------|-----------|--------|-----|--------|
| harassment | 0.857 | 1.000 | 0.923 | 6 |
| hate_speech | 1.000 | 0.500 | 0.667 | 2 |

## Inter-Provider Agreement

| Provider A | Provider B | Cohen's Kappa |
|------------|------------|---------------|
| llm_judge_anthropic_claude-sonnet-4-20250514 | openai | 0.615 |
