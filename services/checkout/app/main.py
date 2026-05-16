import json
import logging
import os
import time
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


SERVICE_NAME = "checkout"
REQUEST_ID_HEADER = "x-request-id"
UPSTREAM_SERVICE_HEADER = "x-upstream-service"
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory:8000")
SHIPPING_URL = os.getenv("SHIPPING_URL", "http://shipping:8000")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(SERVICE_NAME)


class CheckoutItemRequest(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


class CheckoutQuoteRequest(BaseModel):
    customer_id: str
    postal_code: str
    items: list[CheckoutItemRequest]


app = FastAPI(title="Checkout Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PRICE_LIST = {
    "keyboard": 129.0,
    "mouse": 59.0,
    "monitor": 349.0,
    "dock": 149.0,
}


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


@app.post("/checkout/quote")
def create_checkout_quote(payload: CheckoutQuoteRequest, request: Request) -> dict[str, str | bool | float | dict | list[dict[str, str | int | float | bool]]]:
    request_id = get_request_id(request)
    line_items = [item.model_dump() for item in payload.items]

    try:
        with httpx.Client(timeout=5.0) as client:
            log_event(
                "outbound.request",
                request_id=request_id,
                target_service="inventory",
                target_path="/inventory/check",
            )
            inventory_response = client.post(
                f"{INVENTORY_URL}/inventory/check",
                json={"items": line_items},
                headers=build_headers(request_id),
            )
            inventory_response.raise_for_status()

            log_event(
                "outbound.request",
                request_id=request_id,
                target_service="shipping",
                target_path="/shipping/quote",
            )
            shipping_response = client.post(
                f"{SHIPPING_URL}/shipping/quote",
                json={"postal_code": payload.postal_code, "items": line_items},
                headers=build_headers(request_id),
            )
            shipping_response.raise_for_status()
    except httpx.HTTPError as exc:
        log_event(
            "outbound.error",
            request_id=request_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=502, detail="Downstream service unavailable for checkout quote.") from exc

    inventory = inventory_response.json()
    shipping = shipping_response.json()
    subtotal = round(sum(PRICE_LIST.get(item.sku, 0) * item.quantity for item in payload.items), 2)
    total = round(subtotal + shipping["shipping_cost"], 2)
    ready_to_checkout = inventory["all_available"]

    log_event(
        "checkout.quoted",
        request_id=request_id,
        customer_id=payload.customer_id,
        ready_to_checkout=ready_to_checkout,
        subtotal=subtotal,
        total=total,
    )

    return {
        "service": SERVICE_NAME,
        "request_id": request_id,
        "customer_id": payload.customer_id,
        "ready_to_checkout": ready_to_checkout,
        "subtotal": subtotal,
        "total": total,
        "availability": inventory,
        "shipping": shipping,
    }