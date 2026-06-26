from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException

import app.store as store
from app.models import (
    CreateOrderRequest,
    Order,
    OrderStatus,
    UpdateStatusRequest,
    VALID_TRANSITIONS,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=Order, status_code=201)
def create_order(body: CreateOrderRequest) -> Order:
    """Create a new order in PENDING status."""
    now = datetime.now(timezone.utc)
    order = Order(
        id=str(uuid4()),
        customer_name=body.customer_name,
        items=body.items,
        status=OrderStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    store.orders[order.id] = order
    print(f"Order created: {order.id}")
    return order


@router.get("", response_model=list[Order])
def list_orders(status: Optional[OrderStatus] = None) -> list[Order]:
    """Return all orders, optionally filtered by status."""
    all_orders = list(store.orders.values())
    if status is not None:
        all_orders = [o for o in all_orders if o.status == status]
    return all_orders


@router.get("/{order_id}", response_model=Optional[Order])
def get_order(order_id: str) -> None:
    """Return a single order by ID, or 404 if not found."""
    order = store.orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=Order)
def update_status(order_id: str, body: UpdateStatusRequest) -> Order:
    """Advance or cancel an order according to the state machine.

    Returns 404 if the order does not exist.
    Returns 422 if the requested transition is not allowed from the current state.
    """
    order = store.orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = VALID_TRANSITIONS[order.status]
    if body.status not in allowed:
        allowed_names = [s.value for s in allowed] if allowed else []
        raise HTTPException(
            status_code=422,
            detail=(
                f"Cannot transition from {order.status.value} to {body.status.value}. "
                f"Allowed next states: {allowed_names or ['none — terminal state']}"
            ),
        )

    updated = order.model_copy(
        update={"status": body.status, "updated_at": datetime.now(timezone.utc)}
    )
    store.orders[order_id] = updated
    return updated


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: str) -> None:
    """Permanently remove an order. Returns 404 if not found."""
    if order_id not in store.orders:
        raise HTTPException(status_code=404, detail="Order not found")
    del store.orders[order_id]
