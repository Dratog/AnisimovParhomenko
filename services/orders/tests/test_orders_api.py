"""Тесты создания заказа."""

import pytest


def test_create_order_returns_201(client, order_payload):
    response = client.post("/orders", json=order_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["account_id"] == order_payload["account_id"]
    assert body["item"] == order_payload["item"]
    assert body["quantity"] == order_payload["quantity"]
    assert body["created_at"]


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"item": "Кофемолка", "quantity": 2}, "account_id"),
        ({"account_id": 1, "quantity": 2}, "item"),
        ({"account_id": 1, "item": "Кофемолка"}, "quantity"),
        ({"account_id": 1, "item": "Кофемолка", "quantity": 0}, "quantity"),
    ],
)
def test_invalid_order_payload_returns_422(client, payload, field):
    response = client.post("/orders", json=payload)

    assert response.status_code == 422
    assert any(field in error["loc"] for error in response.json()["detail"])
