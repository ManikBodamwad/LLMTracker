# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-09-28

### Breaking
- `openai`, `anthropic` and `httpx` are no longer hard dependencies. Install the SDK you use via extras: `llm-cost-track[openai]`, `[anthropic]`, `[litellm]` or `[all]`. Auto-patching still covers whichever SDKs are installed.
- Streaming OpenAI/LiteLLM chat calls now get `stream_options={"include_usage": True}` injected when unset (one extra final chunk with empty `choices`); pass `CostTracker(inject_stream_usage=False)` to opt out.

### Fixed
- Budget alerts never fired: `set_budget_alert` only registered a limit. Alerts are now checked after every tracked call, notify at most once per UTC day, and callback errors are logged instead of swallowed.
- Feature tags leaked between concurrent asyncio tasks (thread-local storage). They now use `contextvars`.
- Module-level `openai.chat.completions.create` calls were recorded twice.
- Multiple `CostTracker` instances stacked wrappers and double-logged. Patching is now idempotent, and `tracker.unpatch()` detaches a tracker.
- Model names passed positionally (`litellm.completion("gpt-4o", ...)`) were recorded as `unknown` and billed at the fallback rate.
- Fuzzy pricing matched in both directions on raw substrings, so `gpt-4.1` could silently take `gpt-4` pricing and short names matched inside unrelated strings. Matching is now whole-token and one-directional.
- SQLite timestamps are normalized to UTC before storing, so mixed naive/offset timestamps compare correctly.
- HTML reports now escape feature names.
- Tracking failures are now logged on the `llmtrack` logger instead of being silently ignored.

### Added
- Streaming support (sync and async) for OpenAI, Anthropic (`create(stream=True)` and `messages.stream()`) and LiteLLM.
- Patching of OpenAI Responses API and embeddings, `chat.completions.parse`, Anthropic beta Messages, and `litellm.acompletion` / `embedding` / `aembedding`.
- Prompt-cache-aware pricing: `cached_input_tokens` / `cache_creation_tokens` on `log_call` and `CallEvent`, provider default cache rates, and `cache_read_price_per_1m` / `cache_write_price_per_1m` in `register_custom_model`.
- `CallEvent.estimated_pricing`, `summary()["estimated_calls"]`, a one-time warning per unrecognized model, and a report footnote when estimated pricing was used.
- Provider inference understands `provider/model` prefixes and OpenAI o-series names.
- `BaseStorage.feature_cost()` (SQL `SUM` in SQLite) backing the alert checks.
- SQLite: WAL journaling, 30s busy timeout, composite `(feature, timestamp)` index, explicit INSERT columns, and automatic migration of older databases.
- End-to-end tests driving real OpenAI and Anthropic clients over a mocked HTTP transport.

## [0.3.0] - 2026-09-26

### Added
- Downloads badge in README
- Demo GIF and HTML dashboard screenshot section in README
- Richer quickstart example with 5-feature realistic simulation
- "Why llmtrack" problem/solution section in README
- Real-world cost savings examples section in README
- GitHub star CTA in README
- docs/assets/ directory with recording instructions

### Changed
- Improved README structure and visual clarity

## [0.2.2] - 2026-09-26

### Added
- Explicit `authors` and `maintainers` metadata with contact email for package indexes and download tracking services.
- Added direct links to documentation and changelog in project URLs.

## [0.2.1] - 2026-09-23

### Changed
- Refactored documentation and README to an enterprise-grade standard without informal symbols/emojis.
- Cleaned up HTML dashboard template typography.

## [0.2.0] - 2026-09-23

### Added
- Comprehensive model pricing updates for 50+ latest LLMs across OpenAI, Anthropic, Google Gemini, DeepSeek, xAI Grok, Mistral, Meta LLaMA 3.3/3.2, Alibaba Qwen 2.5, and Cohere Command.
- Added support for latest models: `claude-3-7-sonnet`, `claude-3-5-haiku`, `gemini-2.5-pro/flash`, `gemini-2.0-flash`, `deepseek-r1`, `deepseek-v3`, `grok-2/3/4.x`, `mistral-large-2411`, `llama-3.3-70b`, `qwen-2.5-coder-32b`, `command-r-plus`.
- Expanded provider inference with dedicated tags for `xai`, `deepseek`, `meta`, `alibaba`, and `cohere`.

## [0.1.0] - 2025-01-15

### Added
- Initial release
- `CostTracker` class with thread-safe `feature()` context manager
- Auto-patching for OpenAI and Anthropic SDKs
- SQLite and in-memory storage backends
- Terminal report using Rich
- HTML report generation with interactive dark UI and bar charts
- Budget alerts system with threshold checking and custom callbacks
- CLI: `llmtrack report`, `llmtrack clear`
- Support for 25+ LLM models across OpenAI, Anthropic, Google, Mistral, Meta, DeepSeek
- Fuzzy model name matching and aliases
