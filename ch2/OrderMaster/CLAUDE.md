# OrderMaster

A simple backend service implemented in Python using FastAPI, offering order processing functionality. The application models an order's lifecycle as an explicit state machine. Orders are created in PENDING and advance through CONFIRMED → SHIPPED → DELIVERED, or can be cancelled from any non-terminal state. See "Known simplifications" before suggesting hardening.

## Commands

- Install: `pip install -r requirements.txt`
- Run: `uvicorn app.main:app --reload`


## State machine — the central convention

Orders move through:

    PENDING ──► CONFIRMED ──► SHIPPED ──► DELIVERED
       │            │            │
       └────────────┴────────────┴──► CANCELLED

DELIVERED and CANCELLED are terminal: no further transitions allowed.

Invalid transitions return HTTP 422 with FastAPI's standard validation
error shape. This is part of the public API contract; do not change
the status code without flagging it.

## What this codebase deliberately doesn't have

- No database. Orders live in an in-memory dict that vanishes on restart
- No authentication or authorization
- No background jobs or queues
- No external integrations (payment, inventory, email)
- No persistence layer abstraction — `storage.py` is intentionally thin

If a change would add any of the above, that's a real decision worth
surfacing, not a quiet refactor.


## Testing

When adding tests, use FastAPI's `TestClient` and
keep tests next to the code under `app/tests/`. New behavior should
come with at least one test covering the happy path and one covering
the failure mode. The tests must support 100% branch coverage.

## Don't-touch list

- Transitions in the state machine must happen using `update_status` in `order_router.py`.
- The 422 status code on invalid transitions is part of the API
  contract — changing it is a breaking change
