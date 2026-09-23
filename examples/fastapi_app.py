"""
FastAPI integration example for llmtrack.

Demonstrates asynchronous request handling and feature-level cost attribution.
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel

from llmtrack import CostTracker

app = FastAPI(title="LLMTrack FastAPI Demo")
tracker = CostTracker(db_path="fastapi_llmtrack.db")


class SummarizeRequest(BaseModel):
    content: str


class ChatRequest(BaseModel):
    message: str


@app.post("/summarize")
async def summarize_endpoint(req: SummarizeRequest):
    with tracker.feature("pdf_summarization"):
        # Auto-patched or manually logged LLM call
        event = tracker.log_call(
            model="gpt-4o",
            input_tokens=len(req.content.split()) * 2,
            output_tokens=200,
            metadata={"source": "api_v1"},
        )

    return {
        "status": "success",
        "result": "Summarized content preview...",
        "call_id": event.id,
        "cost_usd": event.cost_usd,
    }


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    with tracker.feature("ai_assistant"):
        event = tracker.log_call(
            model="claude-sonnet-4-5",
            input_tokens=150,
            output_tokens=80,
        )

    return {
        "reply": f"Echo: {req.message}",
        "cost_usd": event.cost_usd,
    }


@app.get("/metrics/costs")
async def cost_metrics(days: int = Query(default=7, ge=1, le=90)):
    return tracker.summary(days=days)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
