"""
Flask integration example for llmtrack.

Demonstrates tracking LLM spend per route or business feature in Flask.
"""

from flask import Flask, jsonify, request

from llmtrack import CostTracker

app = Flask(__name__)
tracker = CostTracker(db_path="flask_llmtrack.db")


@app.route("/api/summarize", methods=["POST"])
def summarize():
    data = request.get_json() or {}
    text = data.get("text", "Sample document text.")

    with tracker.feature("document_summary"):
        # Real call or manual log:
        # response = openai.chat.completions.create(...)
        event = tracker.log_call(
            model="gpt-4o",
            input_tokens=len(text.split()) * 2,
            output_tokens=150,
            metadata={"endpoint": "/api/summarize"},
        )

    return jsonify(
        {
            "summary": "This is a concise summary.",
            "cost_usd": event.cost_usd,
        }
    )


@app.route("/api/support/chat", methods=["POST"])
def support_chat():
    with tracker.feature("customer_support"):
        event = tracker.log_call(
            model="gpt-4o-mini",
            input_tokens=250,
            output_tokens=100,
            metadata={"endpoint": "/api/support/chat"},
        )

    return jsonify(
        {
            "reply": "How can I help you today?",
            "cost_usd": event.cost_usd,
        }
    )


@app.route("/api/costs", methods=["GET"])
def get_costs():
    days = request.args.get("days", default=7, type=int)
    return jsonify(tracker.summary(days=days))


if __name__ == "__main__":
    app.run(port=5000, debug=True)
