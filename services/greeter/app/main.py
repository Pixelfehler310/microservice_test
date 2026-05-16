from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class GreetingRequest(BaseModel):
    name: str
    style: str = "friendly"


app = FastAPI(title="Greeter Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


GREETINGS = {
    "friendly": "Hello",
    "formal": "Good day",
    "casual": "Hi",
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "greeter", "status": "ok"}


@app.post("/greet")
def greet(payload: GreetingRequest) -> dict[str, str]:
    style = payload.style.lower()
    prefix = GREETINGS.get(style, GREETINGS["friendly"])
    return {
        "service": "greeter",
        "message": f"{prefix}, {payload.name}!",
        "style": style,
    }
