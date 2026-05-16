# Microservice Test Project

Kleines Demo-Projekt mit mehreren Python-Microservices, einem React-Frontend und einer Dev-Container-Konfiguration.

## Inhalte

- `greeter`: erzeugt einfache Gruesse
- `math`: rechnet einfache Operationen
- `notes`: speichert Demo-Notizen im Speicher
- `inventory`: prueft Lagerbestand und erstellt Fulfillment-Plaene
- `shipping`: berechnet Versandangebote auf Basis des Inventory-Services
- `checkout`: aggregiert Bestand und Versand zu einem kompletten Angebots-Flow
- `frontend`: React-Oberflaeche zum direkten Testen aller Services

Die drei neuen Services erzeugen bewusst eine kleine Call-Chain fuer spaeteres Request-Logging:

```text
Client -> checkout -> inventory
				 -> shipping -> inventory
```

Alle drei propagieren dieselbe `X-Request-ID` und schreiben strukturierte JSON-Logs. Damit lassen sich spaeter mit Loki und Promtail zusammenhaengende Requests serviceuebergreifend nachvollziehen.

## Start

```bash
docker compose up --build
```

Danach sind diese UIs erreichbar:

- Frontend: http://localhost:5173
- Greeter Docs: http://localhost:8001/docs
- Math Docs: http://localhost:8002/docs
- Notes Docs: http://localhost:8003/docs
- Inventory Docs: http://localhost:8004/docs
- Shipping Docs: http://localhost:8005/docs
- Checkout Docs: http://localhost:8006/docs

Beispiel fuer die neue Kette:

```bash
curl -X POST http://localhost:8006/checkout/quote \
	-H "Content-Type: application/json" \
	-H "X-Request-ID: demo-checkout-001" \
	-d '{
		"customer_id": "student-42",
		"postal_code": "90402",
		"items": [
			{"sku": "keyboard", "quantity": 1},
			{"sku": "monitor", "quantity": 1},
			{"sku": "mouse", "quantity": 2}
		]
	}'
```

## Dev Container

Das Projekt kann direkt in einem Dev Container geoeffnet werden. VS Code startet dabei den `workspace`-Container und dieselbe Compose-Umgebung.

## Struktur

```text
.
├── .devcontainer
├── frontend
├── services
│   ├── greeter
│   ├── inventory
│   ├── math
│   ├── notes
│   ├── shipping
│   └── checkout
└── docker-compose.yml
```
