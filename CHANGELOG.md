# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-22

### Added
- **RubricEngine integration**: 5-dimension weighted scoring (accuracy, calibration, cultural sensitivity, handoff quality, explanation quality) now wired into eval runner.
- **Expected action evaluation**: `expected_action` field in test cases is now evaluated; action accuracy metric added to all reports.
- **Retry with exponential backoff**: All API providers now support configurable retry logic with backoff.
- **Token-bucket rate limiting**: Per-provider rate limiting enforced via `RateLimiter`.
- **Structured logging**: Full `modeval.*` logger hierarchy across all modules.
- **`dangerous_activities` harm category**: Added to taxonomy (used by `daigou_gray_zone.jsonl`).
- **Provider resource lifecycle**: All providers implement `close()` for proper HTTP client cleanup.
- **LLM Judge lazy client init**: Anthropic/OpenAI clients initialized on first use, not constructor.
- **Comprehensive test suite**: 60+ tests covering providers, scoring, taxonomy, eval runner, and utilities.
- **Report generator module**: `src/reporting/` with Markdown and JSON report generation.
- **CLI scripts updated**: `compare_providers.py`, `compare_platforms.py`, `generate_report.py` with logging.
- **Test suite validation script**: `scripts/validate_suites.py` for CI.
- **CHANGELOG.md**: Version history tracking.
- **`py.typed` marker**: PEP 561 compliance for typed package consumers.

### Fixed
- **`run_eval.py` variable bug**: `data["agreement"]` corrected to `results_data["agreement"]`.
- **Config-code alignment**: `eval_config.yaml` retry/rate-limit settings now actually read and used by providers.
- **Report generator imports**: Fixed `src.eval_runner` to relative `..eval_runner` import.

### Removed
- **`cultural_bias_delta` dead code**: Removed unused field from `ClassificationMetrics`.

## [0.1.0] - 2026-04-20

### Added
- Initial framework with 4 moderation provider adapters (OpenAI, Perspective, LLM Judge Claude, LLM Judge GPT-4o).
- 8 edge-case test suites with 161 annotated cases.
- Platform-specific suites for TikTok (3 suites) and RedNote (3 suites).
- Cross-platform comparison suite.
- 5-dimension rubric definition (YAML).
- Platform policy profiles (TikTok, RedNote).
- Classification metrics (macro/micro F1, per-category breakdown).
- Expected Calibration Error (ECE).
- Human-AI handoff metrics (trigger rate, precision, recall, context completeness).
- Cohen's kappa inter-provider agreement.
- CLI runner with Click.
- English + Chinese README.
