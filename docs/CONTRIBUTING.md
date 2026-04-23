# Contributing Guide

Thank you for your interest in contributing to the AI Content Moderation Edge-Case Evaluation Framework!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yingshill/ai-content-moderation-edge-case-eval-framework.git
cd ai-content-moderation-edge-case-eval-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Code Quality

### Linting & Formatting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
ruff check src/ tests/ scripts/

# Auto-fix issues
ruff check --fix src/ tests/ scripts/

# Format code
ruff format src/ tests/ scripts/
```

### Type Checking

We use [mypy](https://mypy.readthedocs.io/) for static type analysis:

```bash
mypy src/ --ignore-missing-imports --no-strict-optional
```

The project includes a `py.typed` marker (PEP 561) for downstream type checking consumers.

### Testing

We use [pytest](https://docs.pytest.org/) with async support:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_providers.py -v

# Run with coverage (if installed)
pytest tests/ --cov=src --cov-report=term-missing
```

**Test categories:**
- `test_providers.py` — Provider adapter unit tests with mocked API calls
- `test_scoring.py` — Metrics, calibration, handoff, agreement, rubric tests
- `test_taxonomy.py` — Category registry and severity validation
- `test_eval_runner.py` — Test suite loading, metric mapping, explanation quality
- `test_utils.py` — Logging, retry, rate limiting utilities

### Validate Test Suites

```bash
python scripts/validate_suites.py
```

This checks all JSONL files in `test_suites/` for required fields (`id`, `content`, `ground_truth`).

## Project Structure

```
src/
  providers/     # Moderation system adapters
  scoring/       # Metrics, rubric, agreement
  taxonomy/      # Harm categories, severity levels
  reporting/     # Report generation (Markdown/JSON)
  utils/         # Logging, retry, rate limiting
  eval_runner.py # Main orchestrator

test_suites/     # JSONL test cases
configs/         # YAML configuration files
policies/        # Platform policy profiles
rubrics/         # Scoring rubric definitions
scripts/         # CLI entry points
tests/           # Test suite
docs/            # Documentation
```

## Adding Content

### New Test Cases

1. Add cases to an existing suite or create a new `.jsonl` file under `test_suites/`.
2. Follow the ground truth schema in `docs/METHODOLOGY.md`.
3. Ensure `harm_category` values exist in `src/taxonomy/category_registry.py`.
4. Run `python scripts/validate_suites.py` to verify.

### New Provider Adapter

1. Create `src/providers/your_provider.py`.
2. Subclass `ModerationProvider` from `src/providers/base.py`.
3. Implement `moderate()`, `provider_name()`, and `close()`.
4. Accept `rate_limit_rpm`, `max_retries`, `backoff_base` in constructor.
5. Add mock tests in `tests/test_providers.py`.
6. Wire into `scripts/run_eval.py` and `configs/eval_config.yaml`.

### New Harm Category

1. Add the category to `HARM_CATEGORIES` in `src/taxonomy/category_registry.py`.
2. Add a regression test in `tests/test_taxonomy.py`.
3. Update `docs/METHODOLOGY.md` if needed.

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new provider adapter for Llama Guard
fix: correct ECE bin boundary handling
test: add mock tests for Perspective provider
docs: update methodology with action accuracy metric
chore: update dependencies
ci: add Python 3.12 to test matrix
```

## Pull Request Checklist

- [ ] Code passes `ruff check` and `mypy`
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Test suites validate (`python scripts/validate_suites.py`)
- [ ] New features have corresponding tests
- [ ] Documentation updated if applicable
- [ ] CHANGELOG.md updated
