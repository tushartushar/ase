# OrderMaster

Minimal order-processing REST API built with FastAPI. Demonstrates a state-machine-driven workflow: orders move through `PENDING → CONFIRMED → SHIPPED → DELIVERED` (or `CANCELLED`).

## Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive docs available at http://localhost:8000/docs.

## State Machine

```
PENDING ──► CONFIRMED ──► SHIPPED ──► DELIVERED
   │              │           │
   └──────────────┴───────────┴──► CANCELLED
```

Terminal states (`DELIVERED`, `CANCELLED`) accept no further transitions.

## API

### Create an order
```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Alice",
    "items": [{"product": "Widget", "quantity": 2, "unit_price": 9.99}]
  }' | jq
```

### List orders (optional `?status=PENDING` filter)
```bash
curl -s http://localhost:8000/orders | jq
curl -s "http://localhost:8000/orders?status=PENDING" | jq
```

### Get a single order
```bash
curl -s http://localhost:8000/orders/<id> | jq
```

### Advance status
```bash
curl -s -X PATCH http://localhost:8000/orders/<id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "CONFIRMED"}' | jq
```

### Invalid transition (returns 422)
```bash
# Cannot skip from PENDING straight to DELIVERED
curl -s -X PATCH http://localhost:8000/orders/<id>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "DELIVERED"}' | jq
```

### Delete an order
```bash
curl -s -X DELETE http://localhost:8000/orders/<id>
```

### Health check
```bash
curl -s http://localhost:8000/health
```
