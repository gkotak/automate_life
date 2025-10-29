# Article Summarizer Backend - Testing Guide

## Overview

This directory contains the test suite for the article_summarizer_backend. Tests are organized by type (unit, integration) and run fast enough to execute on every commit.

## Test Statistics

- **Total Tests:** 97
- **Execution Time:** ~0.12 seconds
- **Pass Rate:** 100%
- **Coverage:** 87% (core/url_utils), comprehensive coverage for text_utils and content_detector

## Running Tests

### Quick Start

```bash
# Run all unit tests (recommended for daily development)
cd programs/article_summarizer_backend
python3 -m pytest tests/unit/ -v

# Run specific test file
python3 -m pytest tests/unit/test_url_utils.py -v

# Run tests with coverage report
python3 -m pytest tests/unit/ --cov=core --cov-report=html

# Run tests in quiet mode (less verbose)
python3 -m pytest tests/unit/ -q
```

### Test Execution Strategy

#### ✅ ALWAYS Run Tests

**Before every commit:**
Tests run automatically via pre-commit hook (if configured). They're fast (<1 second) so there's no reason not to run them.

**When to run manually:**
- After modifying any file in `core/`, `processors/`, or `app/services/`
- Before creating a pull request
- After pulling changes from main branch
- When debugging unexpected behavior

**Why it's feasible:**
- Tests execute in ~0.12 seconds
- No external dependencies (fully mocked)
- No network calls or database access
- Completely deterministic and reliable

#### 🔄 Continuous Integration

For a CI/CD pipeline (GitHub Actions, etc.), recommended workflow:

```yaml
# .github/workflows/test.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd programs/article_summarizer_backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          cd programs/article_summarizer_backend
          python3 -m pytest tests/unit/ -v --cov=core --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./programs/article_summarizer_backend/coverage.xml
```

### Pre-Commit Hook

To enable automatic test execution before every commit:

```bash
# Link the pre-commit hook
cd /Users/gauravkotak/cursor-projects-1/automate_life
ln -sf ../../.githooks/pre-commit-pytest .git/hooks/pre-commit-pytest

# Or configure git to use .githooks directory
git config core.hooksPath .githooks
```

To bypass the hook (not recommended):
```bash
git commit --no-verify -m "Emergency fix"
```

## Test Organization

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── README.md                      # This file
├── PHASE1_SUMMARY.md             # Phase 1 completion report
├── unit/                         # Unit tests (fast, no external deps)
│   ├── __init__.py
│   ├── test_url_utils.py         # 30 tests - URL utilities
│   ├── test_text_utils.py        # 37 tests - Text processing
│   └── test_content_detector.py  # 30 tests - Video platform detection
└── integration/                  # Integration tests (coming in Phase 2-4)
    └── __init__.py
```

## Test Markers

Tests are categorized using pytest markers:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run slow tests separately
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

## Writing New Tests

### Template for Unit Tests

```python
import pytest
from module_name import function_to_test

class TestFunctionName:
    """Tests for function_to_test()"""

    @pytest.mark.unit
    def test_basic_functionality(self):
        """Should do the expected thing"""
        result = function_to_test("input")
        assert result == "expected_output"

    @pytest.mark.unit
    def test_edge_case(self):
        """Should handle edge case gracefully"""
        result = function_to_test("")
        assert result is not None
```

### Using Fixtures

Common fixtures are defined in `conftest.py`:

```python
def test_with_sample_urls(sample_urls):
    """Use sample_urls fixture"""
    youtube_url = sample_urls['youtube']
    assert 'youtube.com' in youtube_url

def test_with_sample_titles(sample_titles):
    """Use sample_titles fixture"""
    title = sample_titles['with_special_chars']
    # test title handling
```

## Test Coverage

### Current Coverage (Phase 1)

| Module | Coverage | Status |
|--------|----------|--------|
| core/url_utils.py | 87% | ✅ Excellent |
| core/text_utils.py | ~95% | ✅ Excellent |
| core/content_detector.py | ~80% | ✅ Good |

### Viewing Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/unit/ --cov=core --cov-report=html

# Open in browser
open htmlcov/index.html
```

## Troubleshooting

### Tests Fail Locally

1. **Check Python version:** Requires Python 3.9+
   ```bash
   python3 --version
   ```

2. **Install test dependencies:**
   ```bash
   pip install -r requirements-test.txt
   ```

3. **Clear pytest cache:**
   ```bash
   rm -rf .pytest_cache
   pytest --cache-clear
   ```

### SSL/urllib3 Warnings

If you see SSL warnings, they're harmless and filtered in pytest.ini:
```
urllib3.exceptions.NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+
```

### Import Errors

Make sure you're running from the correct directory:
```bash
cd programs/article_summarizer_backend
python3 -m pytest tests/unit/
```

## Performance

### Benchmark (M1 MacBook Pro)

```
97 tests in 0.12s
- test_url_utils.py: 30 tests in 0.04s
- test_text_utils.py: 37 tests in 0.05s
- test_content_detector.py: 30 tests in 0.03s
```

Tests are optimized for speed:
- No file I/O operations
- No network requests
- No database queries
- All external dependencies mocked
- Fixtures are session-scoped where possible

## Next Steps

### Phase 2: Data Processors (Coming Soon)

- `test_transcript_processor.py` - YouTube transcript fetching (mocked)
- `test_source_extractor.py` - Source name extraction

### Phase 3: Integration Tests (Coming Soon)

- `test_browser_fetcher.py` - Web fetching with authentication
- `test_authentication.py` - Browser cookie handling
- `test_article_processor.py` - Full pipeline integration tests

### Phase 4: API Tests (Coming Soon)

- `test_article_routes.py` - FastAPI endpoint testing
- `test_auth_routes.py` - Authentication flow testing

## Contributing

When adding new tests:

1. ✅ Follow the existing test structure
2. ✅ Use descriptive test names (`test_should_do_something`)
3. ✅ Add `@pytest.mark.unit` decorator
4. ✅ Keep tests fast (<0.01s each)
5. ✅ Use fixtures from `conftest.py` where possible
6. ✅ Add docstrings explaining what the test validates
7. ✅ Run all tests before committing

## FAQ

**Q: How long should tests take?**
A: Unit tests should be nearly instant (<0.2s total). Integration tests can be slower.

**Q: Should I run tests before every commit?**
A: Yes! They're fast enough that there's no reason not to.

**Q: Can I skip tests temporarily?**
A: Yes, use `git commit --no-verify`, but only for emergencies.

**Q: What if a test is flaky?**
A: Unit tests should never be flaky. If you see intermittent failures, fix the test or the code.

**Q: How do I test async functions?**
A: Use `@pytest.mark.asyncio` decorator. pytest-asyncio is already configured.

**Q: Should tests modify files?**
A: No. Unit tests should never have side effects. Use temporary directories if needed.

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [PHASE1_SUMMARY.md](./PHASE1_SUMMARY.md) - Detailed Phase 1 report
