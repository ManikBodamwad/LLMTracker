"""
llmtrack quickstart example.

Run this to see llmtrack in action with mock data.
No real API keys needed.
"""

from llmtrack import CostTracker
from llmtrack.storage.memory import MemoryStorage

# Use in-memory storage for demo
tracker = CostTracker(storage=MemoryStorage(), auto_patch=False)

# Simulate logging calls for different features
features_data = [
    ("document_summarization", "gpt-4o", 800, 300, 45.2),
    ("document_summarization", "gpt-4o", 750, 280, 42.1),
    ("customer_support", "gpt-4o-mini", 200, 150, 12.3),
    ("customer_support", "gpt-4o-mini", 180, 140, 11.8),
    ("customer_support", "gpt-4o-mini", 210, 160, 13.1),
    ("search_autocomplete", "gpt-3.5-turbo", 50, 30, 8.2),
    ("search_autocomplete", "gpt-3.5-turbo", 45, 25, 7.9),
    ("invoice_extraction", "gpt-4o", 1200, 400, 89.3),
]

for feature_name, model, input_tokens, output_tokens, latency in features_data:
    with tracker.feature(feature_name):
        tracker.log_call(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
        )

# Print terminal report
tracker.report()

# Get programmatic summary
summary = tracker.summary()
print(f"\nTotal cost: ${summary['total_cost_usd']:.4f}")
print(
    f"Most expensive feature: {max(summary['features'], key=lambda x: summary['features'][x]['cost_usd'])}"
)

# Generate HTML report
tracker.report(output="html", filepath="demo_report.html")
print("\nHTML report saved to: demo_report.html")
