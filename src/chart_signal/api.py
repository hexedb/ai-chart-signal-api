from __future__ import annotations

import os
from importlib.resources import files

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from .domain import DecisionPolicy
from .provider import provider_from_env

app = FastAPI(
    title="AI Chart Signal API",
    version="1.0.0",
    description="Multimodal chart analysis with explicit confidence gates and NO_TRADE fallback.",
)
provider = provider_from_env()
policy = DecisionPolicy(
    min_confidence=float(os.getenv("MIN_SIGNAL_CONFIDENCE", "0.72")),
    min_confirmations=int(os.getenv("MIN_CONFIRMATIONS", "3")),
)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return files("chart_signal").joinpath("static/index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": type(provider).__name__}


@app.post("/v1/analyze")
async def analyze(
    request: Request,
    symbol: str = Query("XAUUSD", min_length=2, max_length=20),
    timeframe: str = Query("H1", pattern=r"^[A-Za-z0-9]+$"),
    image: bytes = Body(..., media_type="application/octet-stream"),
) -> dict[str, object]:
    content_type = request.headers.get("content-type", "")
    if not (content_type.startswith("image/") or content_type == "application/octet-stream"):
        raise HTTPException(415, "send raw image bytes with an image/* content type")
    if not 128 <= len(image) <= 8 * 1024 * 1024:
        raise HTTPException(413, "image must be between 128 bytes and 8 MB")
    try:
        features = provider.extract(image, symbol=symbol.upper(), timeframe=timeframe.upper())
        return policy.decide(symbol.upper(), timeframe.upper(), features).to_dict()
    except ValueError as exc:
        raise HTTPException(422, f"invalid provider output: {exc}") from exc

