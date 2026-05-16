# Microservice Test Project

Kleines Demo-Projekt mit drei Python-Microservices, einem React-Frontend und einer Dev-Container-Konfiguration.

## Inhalte

- `greeter`: erzeugt einfache Gruesse
- `math`: rechnet einfache Operationen
- `notes`: speichert Demo-Notizen im Speicher
- `frontend`: React-Oberflaeche zum direkten Testen aller Services

## Start

```bash
docker compose up --build
```

Danach sind diese UIs erreichbar:

- Frontend: http://localhost:5173
- Greeter Docs: http://localhost:8001/docs
- Math Docs: http://localhost:8002/docs
- Notes Docs: http://localhost:8003/docs

## Dev Container

Das Projekt kann direkt in einem Dev Container geoeffnet werden. VS Code startet dabei den `workspace`-Container und dieselbe Compose-Umgebung.

## Struktur

```text
.
├── .devcontainer
├── frontend
├── services
│   ├── greeter
│   ├── math
│   └── notes
└── docker-compose.yml
```
