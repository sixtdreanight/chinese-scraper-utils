# Contributing to chinese-scraper-utils

Thanks for your interest in contributing!

## Getting Started

```bash
git clone https://github.com/sixtdreanight/chinese-scraper-utils.git
cd chinese-scraper-utils
pip install -e ".[dev]"
pytest
```

## Development Workflow

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Run `pytest` to verify all tests pass
4. Add tests for new functionality
5. Commit using [Conventional Commits][conv] format
6. Push and open a pull request

## Commit Convention

```
feat: add rate limiter retry for 500/502/504
fix: prevent httpx client thread-safety issue
refactor: extract date normalization into shared module
test: add regression tests for CLI extract
docs: update API_REFERENCE
```

Types: `feat` `fix` `refactor` `test` `docs` `chore` `perf` `ci`

## Code Style

- Full type hints on all public functions
- Use Pydantic models for data structures
- Functions under 50 lines; files under 800 lines
- Error handling: raise typed exceptions, no bare `except:`
- Follow PEP 8

## Testing

- Minimum 80% coverage for new code
- Use pytest fixtures for shared setup
- Descriptive test names: `test_extract_raises_on_empty_url()`

## Pull Request Checklist

- [ ] All tests pass (`pytest`)
- [ ] Type hints added for new public APIs
- [ ] New tests added for new behavior
- [ ] API changes documented in `API_REFERENCE.md`
- [ ] `CHANGELOG.md` updated

## Questions?

Open a [discussion](https://github.com/sixtdreanight/chinese-scraper-utils/discussions).

[conv]: https://www.conventionalcommits.org/
