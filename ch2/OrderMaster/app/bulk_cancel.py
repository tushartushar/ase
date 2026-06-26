from fastapi import APIRouter
from pydantic import BaseModel

import app.store as store
from app.models import OrderStatus, VALID_TRANSITIONS, UpdateStatusRequest
from app.order_router import update_status

router = APIRouter(prefix="/orders", tags=["orders"])


class BulkCancelRequest(BaseModel):
    """Request body for POST /orders/bulk-cancel."""

    order_ids: list[str]


class BulkCancelResult(BaseModel):
    """Result of a bulk-cancel operation."""

    cancelled: list[str]
    skipped: list[str]


@router.post("/bulk-cancel", response_model=BulkCancelResult)
def bulk_cancel(body: BulkCancelRequest) -> BulkCancelResult:
    """Cancel multiple orders in one request.

    Each order is processed independently via update_status.
    Orders that are not found or are already in a terminal state are added to
    ``skipped`` rather than causing the entire request to fail.
    """
    cancelled: list[str] = []
    skipped: list[str] = []

    for order_id in body.order_ids:
        order = store.orders.get(order_id)
        if order is None or OrderStatus.CANCELLED not in VALID_TRANSITIONS[order.status]:
            skipped.append(order_id)
            continue

        update_status(order_id, UpdateStatusRequest(status=OrderStatus.CANCELLED))
        cancelled.append(order_id)

    return BulkCancelResult(cancelled=cancelled, skipped=skipped)
