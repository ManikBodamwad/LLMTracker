# LLMTrack Documentation & In-Depth Usage Guide

`llmtrack` gives you granular, feature-level attribution of your LLM API spending across models and providers.

---

## Table of Contents

- [Installation](#installation)
- [How It Works](#how-it-works)
- [Core Usage Patterns](#core-usage-patterns)
  - [Auto-Patching](#auto-patching)
  - [Context Manager](#context-manager)
  - [Manual Call Logging](#manual-call-logging)
- [Storage Backends](#storage-backends)
- [Reporting](#reporting)
  - [Rich Terminal Output](#rich-terminal-output)
  - [Interactive HTML Reports](#interactive-html-reports)
  - [Programmatic Summary](#programmatic-summary)
- [Budget Alerts](#budget-alerts)
- [Web Framework Integration](#web-framework-integration)
- [CLI Reference](#cli-reference)

---

## Installation

```bash
pip install llm-cost-track
```

With optional LiteLLM integration:

```bash
pip install "llm-cost-track[litellm]"
```

---

## How It Works

1. **Tagging:** You wrap your code blocks in `with tracker.feature("feature_name"):` or `with feature("feature_name"):`.
2. **Interception / Logging:** LLM client SDK calls (OpenAI, Anthropic, LiteLLM) or explicit `tracker.log_call(...)` invocations are recorded with token usage and latency.
3. **Cost Calculation:** Token counts are matched against a built-in pricing engine supporting 25+ major models with fuzzy alias resolution.
4. **Local Persistence:** Events are stored in local SQLite (`llmtrack.db`) or in-memory.
5. **Attribution & Alerts:** Summaries, tables, HTML dashboards, and budget alerts show exact spend per feature.

---

## Core Usage Patterns

### Auto-Patching

By default, `CostTracker(auto_patch=True)` automatically intercepts OpenAI and Anthropic calls:

```python
import openai
from llmtrack import CostTracker

tracker = CostTracker()

with tracker.feature("user_onboarding"):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Welcome message"}]
    )
```

### Context Manager

Context managers are thread-safe and can be nested. If nested, inner blocks override the active feature tag and revert when exiting:

```python
with tracker.feature("batch_pipeline"):
    # Tagged as "batch_pipeline"
    
    with tracker.feature("document_summary"):
        # Tagged as "document_summary"
        ...
        
    # Reverts back to "batch_pipeline"
```

### Manual Call Logging

For custom wrappers, LiteLLM, or unsupported providers:

```python
tracker.log_call(
    model="claude-sonnet-4-5",
    input_tokens=1500,
    output_tokens=600,
    feature="code_generation",
    latency_ms=850.0,
    metadata={"repo": "my-project", "author": "user_42"},
)
```

---

## Storage Backends

### SQLite (Default)

Persists events to a SQLite file across application restarts:

```python
from llmtrack import CostTracker, SQLiteStorage

storage = SQLiteStorage("data/metrics.db")
tracker = CostTracker(storage=storage)
```

### Memory Storage

Keeps events in memory only. Ideal for unit tests, transient jobs, or CI:

```python
from llmtrack import CostTracker, MemoryStorage

tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)
```

---

## Reporting

### Rich Terminal Output

```python
tracker.report(days=7)
```

### Interactive HTML Reports

```python
tracker.report(output="html", filepath="llmtrack_report.html", days=30)
```

### Programmatic Summary

```python
summary = tracker.summary(days=7)
print(f"Total: ${summary['total_cost_usd']:.4f}")
for feature, stats in summary["features"].items():
    print(f"{feature}: ${stats['cost_usd']:.4f} ({stats['calls']} calls)")
```

---

## Budget Alerts

Trigger alerts or custom webhooks when daily spend on a feature exceeds a threshold:

```python
def send_slack_alert(feature, spent, limit):
    print(f"ALERT: {feature} spent ${spent:.2f} today, exceeding limit of ${limit:.2f}")

tracker.set_budget_alert(
    feature="image_generation",
    daily_limit_usd=10.0,
    callback=send_slack_alert,
)
```

---

## CLI Reference

```bash
# View terminal report for last 7 days
llmtrack report

# View report for last 30 days on a custom SQLite file
llmtrack report --days 30 --db my_database.db

# Export interactive HTML report
llmtrack report --html --output llmtrack_30d.html --days 30

# Clear stored tracking database
llmtrack clear --db my_database.db
```
