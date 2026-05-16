import json
import logging
import os
import time
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


SERVICE_NAME = "shipping"
REQUEST_ID_HEADER = "x-request-id"
UPSTREAM_SERVICE_HEADER = "x-upstream-service"
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory:8000")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(SERVICE_NAME)


class ShippingItemRequest(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


class ShippingQuoteRequest(BaseModel):
    postal_code: str
    items: list[ShippingItemRequest]


app = FastAPI(title="Shipping Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def log_event(event: str, **fields: str | int | float | bool | None) -> None:
    logger.info(json.dumps({"event": event, "service": SERVICE_NAME, **fields}))


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", request.headers.get(REQUEST_ID_HEADER, str(uuid4())))


def build_headers(request_id: str) -> dict[str, str]:
    return {
        REQUEST_ID_HEADER: request_id,
        UPSTREAM_SERVICE_HEADER: SERVICE_NAME,
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid4()))
    upstream_service = request.headers.get(UPSTREAM_SERVICE_HEADER, "external")
    request.state.request_id = request_id
    started_at = time.perf_counter()

    log_event(
        "request.started",
        request_id=request_id,
        upstream_service=upstream_service,
        method=request.method,
        path=request.url.path,
    )

    response = await call_next(request)

    log_event(
        "request.finished",
        request_id=request_id,
        upstream_service=upstream_service,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
    )

    response.headers[REQUEST_ID_HEADER] = request_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok"}


@app.post("/shipping/quote")
def create_shipping_quote(payload: ShippingQuoteRequest, request: Request) -> dict[str, str | int | float | bool | list[dict[str, str | int | float]]]:
    request_id = get_request_id(request)

    log_event(
        "outbound.request",
        request_id=request_id,
        target_service="inventory",
        target_path="/inventory/fulfillment-plan",
    )

    try:
        with httpx.Client(timeout=5.0) as client:
            fulfillment_response = client.post(
                f"{INVENTORY_URL}/inventory/fulfillment-plan",
                json={"items": [item.model_dump() for item in payload.items]},
                headers=build_headers(request_id),
            )
            fulfillment_response.raise_for_status()
    except httpx.HTTPError as exc:
        log_event(
            "outbound.error",
            request_id=request_id,
            target_service="inventory",
            detail=str(exc),
        )
        raise HTTPException(status_code=502, detail="Inventory service unavailable for shipping quote.") from exc

    fulfillment_plan = fulfillment_response.json()
    remote_area = payload.postal_code.strip().startswith("9")
    base_cost = 4.5 + (1.25 * len(fulfillment_plan["warehouses"])) + (0.55 * fulfillment_plan["total_weight_kg"])
    if remote_area:
        base_cost += 3.0

    eta_days = 4 if fulfillment_plan["split_required"] else 2
    if remote_area:
        eta_days += 1

    log_event(
        "shipping.quoted",
        request_id=request_id,
        remote_area=remote_area,
        eta_days=eta_days,
        quoted_total=round(base_cost, 2),
    )

    return {
        "service": SERVICE_NAME,
        "request_id": request_id,
        "eta_days": eta_days,
        "shipping_cost": round(base_cost, 2),
        "split_required": fulfillment_plan["split_required"],
        "dispatch_hours": fulfillment_plan["dispatch_hours"],
        "warehouses": fulfillment_plan["warehouses"],
    }