from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class NoteCreateRequest(BaseModel):
    title: str


app = FastAPI(title="Notes Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


notes = [
    {"id": 1, "title": "Check greeter response", "done": False},
    {"id": 2, "title": "Try math division", "done": True},
]


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "notes", "status": "ok"}


@app.get("/notes")
def list_notes() -> dict[str, list[dict[str, int | str | bool]] | str]:
    return {"service": "notes", "items": notes}


@app.post("/notes", status_code=201)
def create_note(payload: NoteCreateRequest) -> dict[str, int | str | bool]:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title must not be empty.")

    note = {"id": len(notes) + 1, "title": title, "done": False}
    notes.append(note)
    return note


@app.post("/notes/{note_id}/toggle")
def toggle_note(note_id: int) -> dict[str, int | str | bool]:
    for note in notes:
        if note["id"] == note_id:
            note["done"] = not note["done"]
            return note

    raise HTTPException(status_code=404, detail="Note not found.")
