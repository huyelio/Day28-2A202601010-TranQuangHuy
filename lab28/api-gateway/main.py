import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Lab 28 AI Platform API Gateway", version="1.0.0")
Instrumentator().instrument(app).expose(app)

VLLM_URL = os.getenv("VLLM_URL", "").rstrip("/")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4")


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    embedding: list[float] = Field(default_factory=lambda: [0.0] * 384)


class ChatResponse(BaseModel):
    answer: str
    latency_ms: float
    model: str
    context_count: int


async def search_context(client: httpx.AsyncClient, embedding: list[float]) -> list[Any]:
    if len(embedding) != 384:
        raise HTTPException(status_code=422, detail="embedding must contain 384 values")

    try:
        response = await client.post(
            f"{QDRANT_URL}/collections/documents/points/search",
            json={"vector": embedding, "limit": 3, "with_payload": True},
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json().get("result", [])
    except httpx.HTTPError:
        return []


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    if not VLLM_URL:
        raise HTTPException(
            status_code=503,
            detail="VLLM_URL is not configured; set VLLM_NGROK_URL in .env",
        )

    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        context = await search_context(client, payload.embedding)
        prompt = f"Context: {context}\n\nQuestion: {payload.query}"
        try:
            response = await client.post(
                f"{VLLM_URL}/v1/chat/completions",
                json={
                    "model": MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="vLLM request timed out") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"vLLM unavailable: {exc}") from exc

    result = response.json()
    try:
        answer = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Invalid response from vLLM") from exc

    return ChatResponse(
        answer=answer,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        model=result.get("model", MODEL_NAME),
        context_count=len(context),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, Any]:
    dependencies: dict[str, bool] = {"vllm_configured": bool(VLLM_URL)}
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            dependencies["qdrant"] = (await client.get(f"{QDRANT_URL}/healthz")).is_success
        except httpx.HTTPError:
            dependencies["qdrant"] = False
    return {"status": "ready" if all(dependencies.values()) else "degraded", **dependencies}
