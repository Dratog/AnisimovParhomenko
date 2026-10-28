"""Запросы к сервису заказов."""

import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from orders.config import settings
from orders.db import get_session
from orders.models import Order
from orders.schemas import OrderCreate, OrderRead

router = APIRouter(prefix="/orders", tags=["Заказы"])


async def _check_account(account_id: int) -> None:
    try:
        # Ограничиваем всю проверку, включая разрешение имени сервиса.
        async with asyncio.timeout(settings.accounts_timeout_seconds):
            async with httpx.AsyncClient(timeout=settings.accounts_timeout_seconds) as client:
                response = await client.get(
                    f"{settings.accounts_url.rstrip('/')}/accounts/{account_id}"
                )
    except (httpx.RequestError, TimeoutError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис клиентов недоступен",
        ) from None

    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Клиент {account_id} не найден",
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис клиентов недоступен",
        )


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказ",
)
async def create_order(payload: OrderCreate, session: Session = Depends(get_session)) -> Order:
    await _check_account(payload.account_id)
    return await run_in_threadpool(_save_order, payload, session)


def _save_order(payload: OrderCreate, session: Session) -> Order:
    order = Order(**payload.model_dump())
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@router.get("", response_model=list[OrderRead], summary="Список заказов клиента")
def list_orders(
    account_id: int,
    session: Session = Depends(get_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Order]:
    stmt = select(Order).where(Order.account_id == account_id).order_by(Order.id).limit(limit)
    return list(session.scalars(stmt))


@router.get("/{order_id}", response_model=OrderRead, summary="Получить заказ")
def get_order(order_id: int, session: Session = Depends(get_session)) -> Order:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заказ {order_id} не найден",
        )
    return order
