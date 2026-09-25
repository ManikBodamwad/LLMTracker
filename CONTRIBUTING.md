# Contributing to llmtrack

Thanks for your interest in contributing. Here's how to get started.

## Setup

```bash
git clone https://github.com/ManikBodamwad/LLMTracker
cd LLMTracker
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest --cov=llmtrack
```

Aim to keep coverage above 80%.

## Common Contributions

### Adding a new model to the pricing database

1. Open `src/llmtrack/pricing/models.py`
2. Add the model to `MODEL_PRICING` dict:
```python
"your-model-name": {"input": X.XX, "output": X.XX},
```
3. Add any aliases to `MODEL_ALIASES` if needed
4. Add a test in `tests/test_pricing.py`
5. Open a PR with a link to the official pricing page as source

### Adding a new SDK integration

1. Create `src/llmtrack/integrations/your_provider.py`
2. Follow the pattern in `openai.py` and `anthropic.py`
3. Add the patch call in `tracker.py`'s `_apply_patches()` method
4. Add tests

### Reporting bugs

Open an issue at https://github.com/ManikBodamwad/LLMTracker/issues with:
- Python version
- llmtrack version (`pip show llm-cost-track`)
- Minimal code to reproduce
- Expected vs actual behavior

## Code Style

- Black for formatting: `black src/`
- Ruff for linting: `ruff check src/`
- Type hints required on all public functions

## PR Checklist

- [ ] Tests pass: `pytest`
- [ ] Coverage above 80%: `pytest --cov=llmtrack`
- [ ] Linting clean: `ruff check src/`
- [ ] Formatting clean: `black --check src/`
- [ ] CHANGELOG.md updated
- [ ] Version bumped if needed
