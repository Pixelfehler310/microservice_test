import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


SERVICE_NAME = "inventory"
REQUEST_ID_HEADER = "x-request-id"
UPSTREAM_SERVICE_HEADER = "x-upstream-service"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(SERVICE_NAME)


class InventoryItemRequest(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


class InventoryCheckRequest(BaseModel):
    items: list[InventoryItemRequest]


class FulfillmentPlanRequest(BaseModel):
    items: list[InventoryItemRequest]


app = FastAPI(title="Inventory Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CATALOG = {
    "keyboard": {"name": "Mechanical Keyboard", "available": 14, "weight_kg": 0.8, "warehouse": "berlin"},
    "mouse": {"name": "Precision Mouse", "available": 22, "weight_kg": 0.2, "warehouse": "berlin"},
    "monitor": {"name": "27 inch Monitor", "available": 7, "weight_kg": 4.7, "warehouse": "hamburg"},
    "dock": {"name": "USB-C Dock", "available": 11, "weight_kg": 0.4, "warehouse": "hamburg"},
}


def log_event(event: str, **fields: str | int | float | bool | None) -> None:
    logger.info(json.dumps({"event": event, "service": SERVICE_NAME, **fields}))


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", request.headers.get(REQUEST_ID_HEADER, str(uuid4())))


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


@app.post("/inventory/check")
def check_inventory(payload: InventoryCheckRequest, request: Request) -> dict[str, str | bool | list[dict[str, str | int | bool]]]:
    request_id = get_request_id(request)
    items: list[dict[str, str | int | bool]] = []
    all_available = True

    for entry in payload.items:
        product = CATALOG.get(entry.sku)
        available = product["available"] if product else 0
        can_fulfill = product is not None and available >= entry.quantity
        all_available = all_available and can_fulfill
        items.append(
            {
                "sku": entry.sku,
                "requested": entry.quantity,
                "available": available,
                "can_fulfill": can_fulfill,
                "warehouse": product["warehouse"] if product else "unknown",
            }
        )

    log_event(
        "inventory.checked",
        request_id=request_id,
        line_count=len(payload.items),
        all_available=all_available,
    )

    return {
        "service": SERVICE_NAME,
        "request_id": request_id,
        "all_available": all_available,
        "items": items,
    }


@app.post("/inventory/fulfillment-plan")
def fulfillment_plan(payload: FulfillmentPlanRequest, request: Request) -> dict[str, str | int | float | bool | list[dict[str, str | int | float]]]:
    request_id = get_request_id(request)
    warehouses: dict[str, dict[str, int | float]] = {}
    split_required = False
    total_weight = 0.0

    for entry in payload.items:
        product = CATALOG.get(entry.sku)
        warehouse = product["warehouse"] if product else "unknown"
        if warehouse not in warehouses:
            warehouses[warehouse] = {"packages": 0, "weight_kg": 0.0}

        warehouses[warehouse]["packages"] += 1
        if product is not None:
            item_weight = product["weight_kg"] * entry.quantity
            warehouses[warehouse]["weight_kg"] += item_weight
            total_weight += item_weight

    split_required = len(warehouses) > 1
    warehouse_plan = [
        {
            "warehouse": warehouse,
            "packages": details["packages"],
            "weight_kg": round(details["weight_kg"], 2),
        }
        for warehouse, details in warehouses.items()
    ]
    dispatch_hours = 24 if split_required else 8

    log_event(
        "inventory.fulfillment_planned",
        request_id=request_id,
        split_required=split_required,
        package_groups=len(warehouse_plan),
        total_weight_kg=round(total_weight, 2),
    )

    return {
        "service": SERVICE_NAME,
        "request_id": request_id,
        "split_required": split_required,
        "dispatch_hours": dispatch_hours,
        "total_weight_kg": round(total_weight, 2),
        "warehouses": warehouse_plan,
    }