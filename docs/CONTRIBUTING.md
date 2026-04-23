# Contributing

Thank you for your interest in improving AI content moderation evaluation!

## How to Contribute

### Adding Test Cases

The most valuable contribution is new edge-case test cases. See `test_suites/README.md` for the authoring guide.

1. Fork the repo
2. Create a branch: `git checkout -b add-test-cases-<suite-name>`
3. Add test cases to the appropriate `.jsonl` file
4. Validate against schema: `python -m jsonschema -i <file> test_suites/schema.json`
5. Open a PR with a description of what edge cases you added and why

### Adding Provider Adapters

1. Create a new file in `src/providers/`
2. Implement the `ModerationProvider` interface from `base.py`
3. Add configuration to `configs/eval_config.yaml`
4. Add tests in `tests/test_providers.py`

### Adding Platform Policy Profiles

1. Create a YAML file in `policies/`
2. Follow the schema in `policies/schema.json`
3. Map platform categories to canonical harm taxonomy
4. Document any platform-specific context fields

## Code Style

- Python 3.11+
- Type hints required
- Format with `ruff format`
- Lint with `ruff check`

## Ground Truth Guidelines

- Be honest about ambiguity — set realistic `annotator_agreement`
- Provide detailed `rationale`
- Test both over-flagging and under-flagging scenarios
- For culturally sensitive cases, consult with cultural context experts when possible
