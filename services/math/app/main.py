from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class CalculationRequest(BaseModel):
    left: float
    right: float
    operation: Literal["add", "subtract", "multiply", "divide"]


app = FastAPI(title="Math Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "math", "status": "ok"}


@app.post("/calculate")
def calculate(payload: CalculationRequest) -> dict[str, float | str]:
    if payload.operation == "add":
        result = payload.left + payload.right
    elif payload.operation == "subtract":
        result = payload.left - payload.right
    elif payload.operation == "multiply":
        result = payload.left * payload.right
    else:
        if payload.right == 0:
            raise HTTPException(status_code=400, detail="Division by zero is not allowed.")
        result = payload.left / payload.right

    return {
        "service": "math",
        "operation": payload.operation,
        "result": result,
    }
