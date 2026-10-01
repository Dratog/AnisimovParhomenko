"""Данные запроса и ответа сервиса заказов."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    """Данные для создания заказа."""

    account_id: int
    item: str
    quantity: int = Field(ge=1)


class OrderRead(BaseModel):
    """Карточка заказа в ответе API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    item: str
    quantity: int
    created_at: datetime
