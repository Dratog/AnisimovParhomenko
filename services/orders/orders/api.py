"""Запросы к сервису заказов."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from orders.db import get_session
from orders.models import Order
from orders.schemas import OrderCreate, OrderRead

router = APIRouter(prefix="/orders", tags=["Заказы"])


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказ",
)
def create_order(payload: OrderCreate, session: Session = Depends(get_session)) -> Order:
    order = Order(**payload.model_dump())
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@router.get("/{order_id}", response_model=OrderRead, summary="Получить заказ")
def get_order(order_id: int, session: Session = Depends(get_session)) -> Order:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заказ {order_id} не найден",
        )
    return order
