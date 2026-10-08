"""Тесты запросов к сервису заказов."""

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


def test_read_created_order(client, order_payload):
    client.post("/orders", json=order_payload)
    payload = order_payload | {"account_id": 2, "item": "Чайник", "quantity": 3}
    created_response = client.post("/orders", json=payload)
    assert created_response.status_code == 201
    created = created_response.json()

    response = client.get(f"/orders/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created
    assert response.json()["account_id"] == payload["account_id"]
    assert response.json()["item"] == payload["item"]
    assert response.json()["quantity"] == payload["quantity"]


def test_read_missing_order_returns_404_with_requested_id(client):
    order_id = 99999

    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 404
    assert str(order_id) in response.json()["detail"]


def test_list_returns_only_requested_account_orders(client, order_payload):
    created = []
    for number in range(3):
        response = client.post("/orders", json=order_payload | {"item": f"Товар {number}"})
        assert response.status_code == 201
        created.append(response.json())
        client.post("/orders", json=order_payload | {"account_id": 2})

    response = client.get("/orders", params={"account_id": order_payload["account_id"]})

    assert response.status_code == 200
    assert response.json() == created


def test_list_returns_empty_for_account_without_orders(client, order_payload):
    client.post("/orders", json=order_payload)

    response = client.get("/orders", params={"account_id": 99999})

    assert response.status_code == 200
    assert response.json() == []


def test_list_supports_limit(client, order_payload):
    client.post("/orders", json=order_payload | {"account_id": 2})
    created = []
    for number in range(3):
        response = client.post("/orders", json=order_payload | {"item": f"Товар {number}"})
        assert response.status_code == 201
        created.append(response.json())

    response = client.get("/orders", params={"account_id": order_payload["account_id"], "limit": 2})

    assert response.status_code == 200
    assert response.json() == created[:2]


def test_list_defaults_to_limit_50(client, order_payload):
    created = []
    for number in range(51):
        response = client.post("/orders", json=order_payload | {"item": f"Товар {number}"})
        assert response.status_code == 201
        created.append(response.json())

    response = client.get("/orders", params={"account_id": order_payload["account_id"]})

    assert response.status_code == 200
    assert response.json() == created[:50]


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({}, "account_id"),
        ({"account_id": "invalid"}, "account_id"),
        ({"account_id": 1, "limit": 0}, "limit"),
        ({"account_id": 1, "limit": 201}, "limit"),
        ({"account_id": 1, "limit": "invalid"}, "limit"),
    ],
)
def test_invalid_list_parameters_return_422(client, params, field):
    response = client.get("/orders", params=params)

    assert response.status_code == 422
    assert any(field in error["loc"] for error in response.json()["detail"])
