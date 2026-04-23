# Human-AI Handoff Quality Analysis Framework

## Why Handoff Quality Matters

Content moderation at scale requires human-AI collaboration. The quality of the *handoff* — when an AI system escalates a case to human review — determines:

1. **Reviewer efficiency**: How quickly can a human make a decision?
2. **Decision quality**: Does the AI provide enough context for an informed decision?
3. **Coverage**: Are the right cases being escalated?

## Evaluation Dimensions

### 1. Trigger Precision

*"Of cases the AI escalated, how many genuinely needed human review?"*

- Low precision = reviewer fatigue from false escalations
- Target: >80% for production systems

### 2. Trigger Recall

*"Of cases that needed human review, how many did the AI catch?"*

- Low recall = harmful content slipping through
- Target: >95% for high-severity categories

### 3. Context Completeness

*"When escalating, does the AI provide all information needed for a decision?"*

Required context fields:
- Content snippet (with relevant surrounding context)
- Predicted harm category
- Confidence score
- Similar past decisions (top 3)
- Recommended action
- Relevant policy reference

### 4. Reviewer Time-Saved

*"How much faster is review with AI context vs from scratch?"*

Estimated by measuring context completeness against baseline review time.

## Configuration

See `configs/handoff_policy.yaml` for threshold configuration.

## Analysis Output

The framework generates:
- Per-provider handoff metrics
- Confusion matrix for escalation decisions
- Context completeness heatmap
- Missed escalation case studies
