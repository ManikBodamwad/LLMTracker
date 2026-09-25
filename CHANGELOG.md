# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
