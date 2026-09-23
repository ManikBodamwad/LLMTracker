# llmtrack

[![PyPI version](https://img.shields.io/pypi/v/llm-cost-track.svg)](https://pypi.org/project/llm-cost-track/)
[![Python versions](https://img.shields.io/pypi/pyversions/llm-cost-track.svg)](https://pypi.org/project/llm-cost-track/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://img.shields.io/pypi/dm/llm-cost-track.svg)](https://pypi.org/project/llm-cost-track/)

LLM cost attribution per feature — track which parts of your product are spending your AI budget.

---

## The Problem

Every company using LLMs knows their total monthly bill, but almost none know which user-facing feature or internal workflow is responsible. Without granular attribution, teams cannot optimize high-cost features, set feature-level unit economics, or enforce sub-budgets.

---

## Installation

```bash
pip install llm-cost-track
```

---

## Quickstart

```python
import openai
from llmtrack import CostTracker

tracker = CostTracker()

with tracker.feature("document_summary"):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Summarize this text: ..."}]
    )

tracker.report()
```

---

## Features

- 🎯 **Feature-Level Cost Attribution**: Tag LLM calls with clear product or feature names.
- ⚡ **Zero-Config Auto-Patching**: Automatically captures usage from OpenAI and Anthropic SDKs with safe fallbacks.
- 🧵 **Thread-Safe Context Manager**: Safely isolate concurrent requests and nested execution flows.
- 💰 **Built-in Model Pricing**: Accurate per-million token pricing for 25+ major models across OpenAI, Anthropic, Google, Mistral, Meta, and DeepSeek.
- 📊 **Rich Terminal & HTML Reports**: Generate rich ASCII terminal breakdown tables or self-contained dark-mode HTML dashboards.
- 🚨 **Budget Alerts**: Set daily spending limits per feature with custom webhook/callback notifications.
- 💾 **Lightweight & Local Storage**: Defaults to embedded SQLite (`llmtrack.db`) or in-memory storage.
- 💻 **CLI Tooling**: Query stats and manage tracking databases directly from the terminal with `llmtrack`.

---

## Supported Models

| Provider | Supported Models |
|---|---|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `gpt-4.5`, `o1`, `o1-pro`, `o1-mini`, `o3`, `o3-mini`, `o4-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`, embeddings (`text-embedding-3-small/large`) |
| **Anthropic** | `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-3-opus`, `claude-3-haiku`, `claude-opus-4`, `claude-sonnet-4-5`, `claude-haiku-4-5`, `claude-opus-5-5`, `claude-sonnet-5` |
| **Google** | `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-1.5-flash-8b` |
| **DeepSeek** | `deepseek-r1` / `deepseek-reasoner`, `deepseek-v3` / `deepseek-chat`, `deepseek-v4-flash`, `deepseek-v4-pro`, `deepseek-coder` |
| **xAI** | `grok-2`, `grok-2-vision`, `grok-3`, `grok-3-mini`, `grok-4.7`, `grok-4.6`, `grok-4.1-fast`, `grok-beta` |
| **Mistral** | `mistral-large-2411`, `mistral-large`, `mistral-medium-3.5`, `mistral-small-2409`, `codestral-2501`, `pixtral-large`, `pixtral-12b`, `ministral-8b`, `ministral-3b` |
| **Meta LLaMA** | `llama-3.3-70b`, `llama-3.2-90b-vision`, `llama-3.2-11b-vision`, `llama-3.2-3b`, `llama-3.2-1b`, `llama-3.1-405b`, `llama-3.1-70b`, `llama-3.1-8b` |
| **Alibaba Qwen** | `qwen-2.5-72b`, `qwen-2.5-coder-32b`, `qwen-2.5-14b`, `qwen-2.5-7b`, `qwen-max`, `qwen-plus`, `qwen-turbo` |
| **Cohere** | `command-r-plus`, `command-r`, `command-light`, embeddings (`embed-english-v3.0`, `embed-multilingual-v3.0`) |

*Custom and unknown models fallback gracefully or can be dynamically registered with `register_custom_model()`.*

---

## API Reference

### `CostTracker`

```python
tracker = CostTracker(
    storage: Optional[BaseStorage] = None,
    db_path: str = "llmtrack.db",
    auto_patch: bool = True
)
```

- **`with tracker.feature(name: str):`**  
  Context manager tagging all calls in the block with `name`.
- **`tracker.log_call(model: str, input_tokens: int, output_tokens: int, feature: Optional[str] = None, latency_ms: float = 0.0, metadata: dict = {}) -> CallEvent`**  
  Manually record an LLM call event.
- **`tracker.report(days: int = 7, output: str = "terminal", filepath: Optional[str] = None) -> None`**  
  Display or export a cost attribution report (`output="terminal"` or `output="html"`).
- **`tracker.summary(days: int = 7) -> dict`**  
  Return an aggregated summary dict with total cost, calls, and per-feature breakdowns.
- **`tracker.set_budget_alert(feature: str, daily_limit_usd: float, callback: Optional[Callable] = None) -> None`**  
  Register daily spending alerts.

---

## CLI Usage

```bash
# View terminal summary table (default: last 7 days)
llmtrack report

# Generate report for the last 30 days
llmtrack report --days 30

# Export self-contained HTML report
llmtrack report --html --output cost_report.html

# Clear database
llmtrack clear --db llmtrack.db
```

---

## Storage Backends

- **`SQLiteStorage(db_path="llmtrack.db")`**: Default persistent storage. Auto-creates schema and indexes.
- **`MemoryStorage()`**: Thread-safe in-memory store, ideal for testing, serverless functions, or short-lived scripts.

```python
from llmtrack import CostTracker, MemoryStorage

tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)
```

---

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/ManikBodamwad/LLMTracker/issues).

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
