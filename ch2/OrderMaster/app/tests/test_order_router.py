import pytest
from fastapi.testclient import TestClient

import app.store as store
from app.main import app

client = TestClient(app)

ITEM = {"product": "Widget", "quantity": 2, "unit_price": 9.99}


@pytest.fixture(autouse=True)
def clear_store():
    store.orders.clear()
    yield
    store.orders.clear()


def create_order(**kwargs):
    payload = {"customer_name": "Alice", "items": [ITEM], **kwargs}
    return client.post("/orders", json=payload)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /orders
# ---------------------------------------------------------------------------

def test_create_order_happy_path():
    r = create_order()
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "PENDING"
    assert data["customer_name"] == "Alice"
    assert len(data["items"]) == 1
    assert "id" in data


def test_create_order_empty_items_rejected():
    r = client.post("/orders", json={"customer_name": "Alice", "items": []})
    assert r.status_code == 422


def test_create_order_invalid_quantity_rejected():
    r = client.post("/orders", json={"customer_name": "Alice", "items": [
        {"product": "X", "quantity": 0, "unit_price": 1.0}
    ]})
    assert r.status_code == 422


def test_create_order_multiple_items():
    items = [
        {"product": "Widget", "quantity": 2, "unit_price": 9.99},
        {"product": "Gadget", "quantity": 1, "unit_price": 24.50},
        {"product": "Doohickey", "quantity": 5, "unit_price": 3.00},
    ]
    r = client.post("/orders", json={"customer_name": "Alice", "items": items})
    assert r.status_code == 201
    data = r.json()
    assert len(data["items"]) == 3
    assert data["items"][0]["product"] == "Widget"
    assert data["items"][1]["product"] == "Gadget"
    assert data["items"][2]["product"] == "Doohickey"


def test_create_order_negative_price_rejected():
    r = client.post("/orders", json={"customer_name": "Alice", "items": [
        {"product": "X", "quantity": 1, "unit_price": -1.0}
    ]})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /orders
# ---------------------------------------------------------------------------

def test_list_orders_empty():
    r = client.get("/orders")
    assert r.status_code == 200
    assert r.json() == []


def test_list_orders_returns_all():
    create_order()
    create_order(customer_name="Bob")
    r = client.get("/orders")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_orders_filter_by_status():
    order_id = create_order().json()["id"]
    create_order(customer_name="Bob")  # stays PENDING

    client.patch(f"/orders/{order_id}/status", json={"status": "CONFIRMED"})

    pending = client.get("/orders", params={"status": "PENDING"}).json()
    confirmed = client.get("/orders", params={"status": "CONFIRMED"}).json()

    assert len(pending) == 1
    assert len(confirmed) == 1
    assert confirmed[0]["id"] == order_id


# ---------------------------------------------------------------------------
# GET /orders/{id}
# ---------------------------------------------------------------------------

def test_get_order_happy_path():
    order_id = create_order().json()["id"]
    r = client.get(f"/orders/{order_id}")
    assert r.status_code == 200
    assert r.json()["id"] == order_id


def test_get_order_not_found():
    r = client.get("/orders/does-not-exist")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /orders/{id}/status — valid transitions
# ---------------------------------------------------------------------------

def _advance(order_id, *statuses):
    for s in statuses:
        r = client.patch(f"/orders/{order_id}/status", json={"status": s})
        assert r.status_code == 200, r.text
    return r.json()


def test_transition_pending_to_confirmed():
    oid = create_order().json()["id"]
    data = _advance(oid, "CONFIRMED")
    assert data["status"] == "CONFIRMED"


def test_transition_pending_to_cancelled():
    oid = create_order().json()["id"]
    data = _advance(oid, "CANCELLED")
    assert data["status"] == "CANCELLED"


def test_transition_confirmed_to_shipped():
    oid = create_order().json()["id"]
    data = _advance(oid, "CONFIRMED", "SHIPPED")
    assert data["status"] == "SHIPPED"


def test_transition_confirmed_to_cancelled():
    oid = create_order().json()["id"]
    data = _advance(oid, "CONFIRMED", "CANCELLED")
    assert data["status"] == "CANCELLED"


def test_transition_shipped_to_delivered():
    oid = create_order().json()["id"]
    data = _advance(oid, "CONFIRMED", "SHIPPED", "DELIVERED")
    assert data["status"] == "DELIVERED"


def test_transition_shipped_to_cancelled():
    oid = create_order().json()["id"]
    data = _advance(oid, "CONFIRMED", "SHIPPED", "CANCELLED")
    assert data["status"] == "CANCELLED"


# ---------------------------------------------------------------------------
# PATCH /orders/{id}/status — invalid transitions (422)
# ---------------------------------------------------------------------------

def test_invalid_transition_pending_to_shipped():
    oid = create_order().json()["id"]
    r = client.patch(f"/orders/{oid}/status", json={"status": "SHIPPED"})
    assert r.status_code == 422


def test_invalid_transition_pending_to_delivered():
    oid = create_order().json()["id"]
    r = client.patch(f"/orders/{oid}/status", json={"status": "DELIVERED"})
    assert r.status_code == 422


def test_invalid_transition_confirmed_to_delivered():
    oid = create_order().json()["id"]
    client.patch(f"/orders/{oid}/status", json={"status": "CONFIRMED"})
    r = client.patch(f"/orders/{oid}/status", json={"status": "DELIVERED"})
    assert r.status_code == 422


def test_invalid_transition_from_terminal_delivered():
    oid = create_order().json()["id"]
    _advance(oid, "CONFIRMED", "SHIPPED", "DELIVERED")
    for target in ("CONFIRMED", "SHIPPED", "CANCELLED", "PENDING"):
        r = client.patch(f"/orders/{oid}/status", json={"status": target})
        assert r.status_code == 422
        assert "none — terminal state" in r.json()["detail"]


def test_invalid_transition_from_terminal_cancelled():
    oid = create_order().json()["id"]
    _advance(oid, "CANCELLED")
    r = client.patch(f"/orders/{oid}/status", json={"status": "PENDING"})
    assert r.status_code == 422
    assert "none — terminal state" in r.json()["detail"]


def test_update_status_order_not_found():
    r = client.patch("/orders/no-such-id/status", json={"status": "CONFIRMED"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /orders/{id}
# ---------------------------------------------------------------------------

def test_delete_order_happy_path():
    oid = create_order().json()["id"]
    r = client.delete(f"/orders/{oid}")
    assert r.status_code == 204
    assert client.get(f"/orders/{oid}").status_code == 404


def test_delete_order_not_found():
    r = client.delete("/orders/no-such-id")
    assert r.status_code == 404
