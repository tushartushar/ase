from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Lifecycle states an order can occupy."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# Which statuses a given status can transition to
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderItem(BaseModel):
    """A single line item within an order."""

    product: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class Order(BaseModel):
    """A customer order and its current lifecycle state."""

    id: str
    customer_name: str
    items: list[OrderItem]
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    @property
    def total(self) -> float:
        """Sum of quantity × unit_price across all line items."""
        return sum(i.quantity * i.unit_price for i in self.items)


class CreateOrderRequest(BaseModel):
    """Request body for POST /orders."""

    customer_name: str
    items: list[OrderItem] = Field(min_length=1)


class UpdateStatusRequest(BaseModel):
    """Request body for PATCH /orders/{id}/status."""

    status: OrderStatus
