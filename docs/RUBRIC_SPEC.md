# Rubric Format Specification

## Overview

Rubrics are YAML files that define evaluation dimensions, weights, and scoring criteria.

## Format

```yaml
dimensions:
  <dimension_name>:
    description: "What this dimension measures"
    weight: 0.25  # Must sum to 1.0 across all dimensions
    scoring:
      5: "Criteria for score 5 (best)"
      4: "Criteria for score 4"
      3: "Criteria for score 3"
      2: "Criteria for score 2"
      1: "Criteria for score 1 (worst)"
```

## Constraints

- Weights MUST sum to 1.0 (tolerance: ±0.01)
- Scoring levels MUST include all of 1-5
- Dimension names must be valid Python identifiers

## Default Rubric

The default rubric (`rubrics/default.yaml`) includes 5 dimensions:
- accuracy (0.25)
- calibration (0.20)
- cultural_sensitivity (0.20)
- handoff_quality (0.20)
- explanation_quality (0.15)

## Custom Rubrics

Create custom rubrics for specific use cases:
- Minor safety evaluation: Higher weight on recall_bias
- Production readiness: Higher weight on calibration
- Multilingual: Higher weight on cultural_sensitivity

See `rubrics/custom_example.yaml` for a template.
