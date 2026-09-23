# LLMTrack

[![PyPI version](https://img.shields.io/pypi/v/llm-cost-track.svg?style=flat-square)](https://pypi.org/project/llm-cost-track/)
[![Python versions](https://img.shields.io/pypi/pyversions/llm-cost-track.svg?style=flat-square)](https://pypi.org/project/llm-cost-track/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/github/actions/workflow/status/ManikBodamwad/LLMTracker/publish.yml?style=flat-square)](https://github.com/ManikBodamwad/LLMTracker)

Feature-level cost attribution and budget monitoring for Large Language Model (LLM) applications.

---

## Overview

Most AI engineering teams know their aggregate monthly LLM bill from providers like OpenAI, Anthropic, and Google Cloud, but lack visibility into which specific product features, customer segments, or background workflows are driving those expenses.

`llmtrack` provides granular, thread-safe cost attribution by wrapping model calls with feature tags, computing exact token costs against real-time provider pricing matrices, persisting telemetry locally, and producing terminal summaries, HTML dashboards, and automated threshold alerts.

---

## Key Capabilities

- **Feature-Level Attribution**: Tag model invocations using context managers or direct API parameters.
- **Zero-Friction Auto-Patching**: Transparently captures token usage and latency from OpenAI and Anthropic SDKs with fallback protections.
- **Thread and Task Isolation**: Safe for high-concurrency web servers using thread-local context separation.
- **Comprehensive Pricing Engine**: Pre-configured per-million token rates for 50+ frontier and open models with fuzzy alias resolution.
- **Embedded Persistence**: Lightweight SQLite storage with indexing and automatic connection recycling; zero mandatory external database dependencies.
- **Actionable Reporting**: Rich terminal breakdown tables and self-contained interactive HTML dashboards.
- **Budget Alerts**: Real-time spending thresholds with support for custom webhook and notification callbacks.
- **CLI Utility**: Query spend statistics and manage tracking databases directly from the command line.

---

## Installation

Install the base package via pip:

```bash
pip install llm-cost-track
```

To include optional LiteLLM integration:

```bash
pip install "llm-cost-track[litellm]"
```

---

## Quickstart

### 1. Auto-Patching with OpenAI

`CostTracker` automatically intercepts calls made through official SDKs when initialized with `auto_patch=True` (default):

```python
import openai
from llmtrack import CostTracker

tracker = CostTracker()

with tracker.feature("document_summary"):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Summarize the quarterly financials."}]
    )

# Print a rich breakdown table to the terminal
tracker.report()
```

### 2. Auto-Patching with Anthropic

```python
import anthropic
from llmtrack import CostTracker

tracker = CostTracker()
client = anthropic.Anthropic()

with tracker.feature("customer_support_agent"):
    message = client.messages.create(
        model="claude-3-7-sonnet",
        max_tokens=1024,
        messages=[{"role": "user", "content": "How do I update my billing email?"}]
    )

tracker.report()
```

### 3. Global Context Tagging

For modular applications, import the top-level `feature` context manager directly:

```python
from llmtrack import feature
import openai

with feature("invoice_extraction"):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Extract line items from invoice #4102."}]
    )
```

### 4. Explicit Call Logging

For custom API clients, proxy gateways, or self-hosted model deployments, log calls directly:

```python
from llmtrack import CostTracker

tracker = CostTracker(auto_patch=False)

tracker.log_call(
    model="deepseek-r1",
    input_tokens=1250,
    output_tokens=680,
    feature="code_review",
    latency_ms=840.2,
    metadata={"repository": "backend-core", "pull_request_id": 142}
)
```

---

## Framework Integration

### FastAPI

Use context managers inside route handlers or dependency injection pipelines:

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel
import openai
from llmtrack import CostTracker

app = FastAPI(title="AI Service")
tracker = CostTracker(db_path="production_metrics.db")

class QueryRequest(BaseModel):
    query: str

@app.post("/api/v1/search")
async def semantic_search(request: QueryRequest):
    with tracker.feature("semantic_search"):
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": request.query}]
        )
    return {"result": response.choices[0].message.content}

@app.get("/api/v1/metrics/costs")
async def get_costs(days: int = 7):
    return tracker.summary(days=days)
```

### Flask

```python
from flask import Flask, request, jsonify
import openai
from llmtrack import CostTracker

app = Flask(__name__)
tracker = CostTracker(db_path="flask_costs.db")

@app.route("/api/summarize", methods=["POST"])
def summarize():
    data = request.get_json() or {}
    content = data.get("text", "")

    with tracker.feature("document_summary"):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}]
        )

    return jsonify({"summary": response.choices[0].message.content})
```

---

## Storage Backends

### SQLite (Default)

Persists events across process restarts in an optimized, indexed SQLite database file:

```python
from llmtrack import CostTracker, SQLiteStorage

storage = SQLiteStorage(db_path="data/attribution.db")
tracker = CostTracker(storage=storage)
```

### In-Memory Storage

Thread-safe, ephemeral storage designed for unit tests, transient jobs, or serverless environments:

```python
from llmtrack import CostTracker, MemoryStorage

tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)
```

---

## Budget Alerts and Notifications

Register spending thresholds per feature to enforce unit economics and guard against runaway loops:

```python
from llmtrack import CostTracker

tracker = CostTracker()

def on_budget_exceeded(feature_name: str, spent_usd: float, limit_usd: float):
    # Dispatch alert via Slack, PagerDuty, or email
    print(f"CRITICAL: Feature '{feature_name}' reached ${spent_usd:.2f} (limit: ${limit_usd:.2f})")

tracker.set_budget_alert(
    feature="bulk_document_indexing",
    daily_limit_usd=25.00,
    callback=on_budget_exceeded
)
```

---

## Reporting

### Terminal Output

Generate formatted Rich summary tables directly in stdout:

```python
tracker.report(days=7, output="terminal")
```

Sample output:

```
-------------------------------------------------------------------------------------
Feature                   Cost (USD)     % of Total   Calls      Avg/Call    Tokens
-------------------------------------------------------------------------------------
document_summary             $12.4500         58.2%     120     $0.103750   1,420,000
customer_support              $6.8200         31.9%     450     $0.015155     890,000
semantic_search               $2.1200          9.9%     840     $0.002523     310,000
-------------------------------------------------------------------------------------
Total Spend: $21.3900 | Total Calls: 1,410 | Period: Last 7 Days
-------------------------------------------------------------------------------------
```

### Standalone HTML Dashboards

Export interactive, dark-mode dashboards with metrics cards, percentage breakdown visualizers, and sortable data grids:

```python
tracker.report(output="html", filepath="reports/weekly_cost_report.html", days=7)
```

### Programmatic Aggregations

Retrieve raw aggregations as Python dictionaries:

```python
summary = tracker.summary(days=30)
total_cost = summary["total_cost_usd"]
feature_stats = summary["features"]
```

---

## Supported Models

The built-in pricing engine includes updated rates (per 1,000,000 tokens) and longest-match fuzzy aliasing for the following model families:

| Provider | Model Identifiers |
|---|---|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `gpt-4.5`, `o1`, `o1-pro`, `o1-mini`, `o3`, `o3-mini`, `o4-mini`, `chatgpt-4o-latest`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`, `text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002` |
| **Anthropic** | `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-3-opus`, `claude-3-haiku`, `claude-opus-5-5`, `claude-sonnet-5`, `claude-haiku-4-5`, `claude-fable-5-1` |
| **Google Cloud** | `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash`, `gemini-2.0-flash-lite`, `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-1.5-flash-8b`, `text-embedding-004` |
| **DeepSeek** | `deepseek-r1` / `deepseek-reasoner`, `deepseek-v3` / `deepseek-chat`, `deepseek-v4-flash`, `deepseek-v4-pro`, `deepseek-coder` |
| **xAI** | `grok-2`, `grok-2-vision`, `grok-3`, `grok-3-mini`, `grok-4.7`, `grok-4.6`, `grok-4.1-fast`, `grok-beta`, `grok-vision-beta` |
| **Mistral AI** | `mistral-large-2411`, `mistral-large`, `mistral-medium-3.5`, `mistral-small-2409`, `codestral-2501`, `pixtral-large`, `pixtral-12b`, `ministral-8b`, `ministral-3b`, `mistral-embed` |
| **Meta LLaMA** | `llama-3.3-70b`, `llama-3.2-90b-vision`, `llama-3.2-11b-vision`, `llama-3.2-3b`, `llama-3.2-1b`, `llama-3.1-405b`, `llama-3.1-70b`, `llama-3.1-8b` |
| **Alibaba Cloud** | `qwen-2.5-72b`, `qwen-2.5-coder-32b`, `qwen-2.5-14b`, `qwen-2.5-7b`, `qwen-max`, `qwen-plus`, `qwen-turbo` |
| **Cohere** | `command-r-plus`, `command-r`, `command-light`, `embed-english-v3.0`, `embed-multilingual-v3.0` |

### Custom Model Registration

Register proprietary or newly released models dynamically at runtime:

```python
from llmtrack.pricing.updater import register_custom_model

register_custom_model(
    model="internal-fine-tuned-llama-70b",
    input_price_per_1m=0.35,
    output_price_per_1m=0.75,
    aliases=["custom-llama-v1", "internal-model"]
)
```

---

## Command Line Interface

`llmtrack` includes a CLI utility for interacting with persistent storage files:

```bash
# Display summary table for the last 7 days (default database: llmtrack.db)
llmtrack report

# Display summary for the last 30 days against a custom database path
llmtrack report --days 30 --db /var/data/llmtrack.db

# Export an HTML dashboard
llmtrack report --html --output reports/monthly_spend.html --days 30

# Clear recorded telemetry from database
llmtrack clear --db /var/data/llmtrack.db
```

---

## API Reference

### `CostTracker`

```python
CostTracker(
    storage: Optional[BaseStorage] = None,
    db_path: str = "llmtrack.db",
    auto_patch: bool = True
)
```

- **`feature(name: str) -> Generator[None, None, None]`**  
  Thread-safe context manager that associates all underlying LLM calls with `name`. Supports nesting.
- **`log_call(model: str, input_tokens: int, output_tokens: int, feature: Optional[str] = None, latency_ms: float = 0.0, metadata: Optional[dict] = None) -> CallEvent`**  
  Records an individual model call event and persists it to configured storage.
- **`report(days: int = 7, output: str = "terminal", filepath: Optional[str] = None) -> None`**  
  Renders formatted terminal statistics or writes an interactive HTML dashboard to disk.
- **`summary(days: int = 7) -> dict`**  
  Returns aggregated cost, token, and call count metrics grouped by feature.
- **`set_budget_alert(feature: str, daily_limit_usd: float, callback: Optional[Callable] = None) -> None`**  
  Establishes a daily spending threshold for a designated feature.

---

## Contributing

Contributions, issue reports, and pull requests are welcome.

1. Fork the repository on GitHub.
2. Create a feature branch: `git checkout -b feature/model-expansion`
3. Ensure test suite passes: `pytest --cov=llmtrack`
4. Commit your changes: `git commit -m 'Add support for new provider'`
5. Push to your branch and open a Pull Request at [https://github.com/ManikBodamwad/LLMTracker](https://github.com/ManikBodamwad/LLMTracker).

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for full terms.
