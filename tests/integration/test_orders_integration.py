"""Создание заказа через настоящие accounts, orders и их базы данных."""

from datetime import datetime
from uuid import uuid4

import httpx


def test_create_order_for_existing_account(
    accounts_client: httpx.Client, orders_client: httpx.Client
) -> None:
    account_payload = {
        "name": "Интеграционный клиент",
        "email": f"integration-{uuid4().hex}@example.com",
    }
    response = accounts_client.post("/accounts", json=account_payload)
    assert response.status_code == 201, response.text
    account = response.json()
    assert account["id"] > 0
    assert account["name"] == account_payload["name"]
    assert account["email"] == account_payload["email"]

    order_payload = {"account_id": account["id"], "item": "Кофемолка", "quantity": 2}
    response = orders_client.post("/orders", json=order_payload)
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["id"] > 0
    assert order["account_id"] == account["id"]
    assert order["item"] == order_payload["item"]
    assert order["quantity"] == order_payload["quantity"]
    datetime.fromisoformat(order["created_at"])

    response = orders_client.get(f"/orders/{order['id']}")
    assert response.status_code == 200, response.text
    assert response.json() == order
