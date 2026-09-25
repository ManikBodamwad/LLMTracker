"""
llmtrack quickstart — generates realistic sample data and shows
a full terminal report + HTML dashboard.

Run this to see llmtrack in action. No real API keys needed.
"""
import time
import random
from llmtrack import CostTracker
from llmtrack.storage.memory import MemoryStorage

print("=" * 60)
print("  llm-cost-track — Feature-Level LLM Cost Attribution")
print("=" * 60)
print()

# Use in-memory storage — no files created
tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)

# Realistic production scenario:
# A SaaS product with 4 LLM-powered features running over 7 days

sample_data = [
    # (feature, model, input_tokens, output_tokens, latency_ms)

    # Document summarization — heavy GPT-4o usage
    ("document_summarization", "gpt-4o", 1200, 450, 1840),
    ("document_summarization", "gpt-4o", 980,  380, 1620),
    ("document_summarization", "gpt-4o", 1450, 520, 2100),
    ("document_summarization", "gpt-4o", 870,  310, 1480),
    ("document_summarization", "gpt-4o", 1100, 420, 1780),
    ("document_summarization", "gpt-4o", 1320, 490, 1920),
    ("document_summarization", "gpt-4o", 760,  280, 1340),
    ("document_summarization", "gpt-4o", 1050, 400, 1700),

    # Customer support — cheaper model, high volume
    ("customer_support", "gpt-4o-mini", 180,  140, 320),
    ("customer_support", "gpt-4o-mini", 210,  165, 380),
    ("customer_support", "gpt-4o-mini", 155,  120, 290),
    ("customer_support", "gpt-4o-mini", 230,  180, 410),
    ("customer_support", "gpt-4o-mini", 195,  150, 345),
    ("customer_support", "gpt-4o-mini", 175,  135, 315),
    ("customer_support", "gpt-4o-mini", 220,  170, 395),
    ("customer_support", "gpt-4o-mini", 200,  155, 360),
    ("customer_support", "gpt-4o-mini", 185,  145, 330),
    ("customer_support", "gpt-4o-mini", 215,  168, 385),
    ("customer_support", "gpt-4o-mini", 190,  148, 340),
    ("customer_support", "gpt-4o-mini", 205,  160, 370),

    # Search autocomplete — very cheap, massive volume
    ("search_autocomplete", "gpt-3.5-turbo", 45, 25, 95),
    ("search_autocomplete", "gpt-3.5-turbo", 38, 20, 82),
    ("search_autocomplete", "gpt-3.5-turbo", 52, 28, 108),
    ("search_autocomplete", "gpt-3.5-turbo", 41, 22, 89),
    ("search_autocomplete", "gpt-3.5-turbo", 48, 26, 99),
    ("search_autocomplete", "gpt-3.5-turbo", 35, 18, 76),
    ("search_autocomplete", "gpt-3.5-turbo", 55, 30, 112),
    ("search_autocomplete", "gpt-3.5-turbo", 43, 23, 92),
    ("search_autocomplete", "gpt-3.5-turbo", 50, 27, 103),
    ("search_autocomplete", "gpt-3.5-turbo", 39, 21, 85),
    ("search_autocomplete", "gpt-3.5-turbo", 46, 24, 96),
    ("search_autocomplete", "gpt-3.5-turbo", 42, 22, 90),

    # Invoice extraction — expensive, mission-critical
    ("invoice_extraction", "gpt-4o", 1800, 620, 2840),
    ("invoice_extraction", "gpt-4o", 2100, 740, 3200),
    ("invoice_extraction", "gpt-4o", 1650, 580, 2680),
    ("invoice_extraction", "gpt-4o", 1950, 690, 3050),
    ("invoice_extraction", "gpt-4o", 1720, 600, 2760),

    # Code review — Claude usage
    ("code_review", "claude-3-5-sonnet", 2200, 800, 3400),
    ("code_review", "claude-3-5-sonnet", 1850, 670, 2950),
    ("code_review", "claude-3-5-sonnet", 2450, 890, 3750),
    ("code_review", "claude-3-5-sonnet", 1980, 720, 3100),
]

print(f"Simulating {len(sample_data)} LLM calls across 5 product features...")
print()

# Log all sample calls
for feature_name, model, input_tokens, output_tokens, latency in sample_data:
    with tracker.feature(feature_name):
        tracker.log_call(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
        )

# Small pause for effect
time.sleep(0.5)

# Set a budget alert to demonstrate the feature
tracker.set_budget_alert(
    feature="invoice_extraction",
    daily_limit_usd=5.00,
)

# Print terminal report
print()
tracker.report(days=7)

# Print programmatic summary
print()
summary = tracker.summary(days=7)
features = summary["features"]
most_expensive = max(features, key=lambda x: features[x]["cost_usd"])
most_calls = max(features, key=lambda x: features[x]["calls"])
cheapest_per_call = min(features, key=lambda x: features[x]["avg_cost_per_call"])

print("=" * 60)
print("  Key Insights")
print("=" * 60)
print(f"  Total spend (7 days):     ${summary['total_cost_usd']:.4f}")
print(f"  Total LLM calls:          {summary['total_calls']:,}")
print(f"  Most expensive feature:   {most_expensive}")
print(f"  Highest call volume:      {most_calls} ({features[most_calls]['calls']:,} calls)")
print(f"  Cheapest per call:        {cheapest_per_call} (${features[cheapest_per_call]['avg_cost_per_call']:.6f}/call)")
print()

# Generate HTML report
html_path = "demo_report.html"
tracker.report(output="html", filepath=html_path, days=7)
print(f"  HTML dashboard saved to:  {html_path}")
print()
print("  Open demo_report.html in your browser to see the full dashboard.")
print("=" * 60)
