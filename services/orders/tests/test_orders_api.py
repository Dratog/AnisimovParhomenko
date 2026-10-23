"""Тесты запросов к сервису заказов."""

import httpx
import pytest
from sqlalchemy import func, select

from orders.config import settings
from orders.models import Order


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
def test_invalid_order_payload_returns_422(client, payload, field, accounts_http):
    response = client.post("/orders", json=payload)

    assert response.status_code == 422
    assert any(field in error["loc"] for error in response.json()["detail"])
    accounts_http.assert_not_called()


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


def test_create_order_checks_account_before_saving(
    client, order_payload, db_session, accounts_http, monkeypatch
):
    monkeypatch.setattr(settings, "accounts_url", "http://accounts.test:8123/")
    monkeypatch.setattr(settings, "accounts_timeout_seconds", 0.75)
    account_response = accounts_http.side_effect

    def check_before_save(request):
        assert db_session.scalar(select(func.count()).select_from(Order)) == 0
        return account_response(request)

    accounts_http.side_effect = check_before_save

    response = client.post("/orders", json=order_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["account_id"] == order_payload["account_id"]
    assert body["item"] == order_payload["item"]
    assert body["quantity"] == order_payload["quantity"]
    assert body["created_at"]
    accounts_http.assert_called_once()
    request = accounts_http.call_args.args[0]
    assert request.method == "GET"
    assert str(request.url) == f"http://accounts.test:8123/accounts/{order_payload['account_id']}"
    assert request.extensions["timeout"] == {
        "connect": 0.75,
        "read": 0.75,
        "write": 0.75,
        "pool": 0.75,
    }
    saved = db_session.get(Order, body["id"])
    assert saved is not None
    assert saved.account_id == order_payload["account_id"]
    assert saved.item == order_payload["item"]
    assert saved.quantity == order_payload["quantity"]


def test_missing_account_returns_404_without_saving_order(
    client, order_payload, db_session, accounts_http
):
    account_id = order_payload["account_id"]
    accounts_http.side_effect = None
    accounts_http.return_value = httpx.Response(
        404, json={"detail": f"Клиент {account_id} не найден"}
    )

    response = client.post("/orders", json=order_payload)

    assert response.status_code == 404
    assert response.json() == {"detail": f"Клиент {account_id} не найден"}
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0
    accounts_http.assert_called_once()


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
def test_accounts_network_error_returns_503_without_saving_order(
    client, order_payload, db_session, accounts_http, error_type
):
    accounts_http.side_effect = error_type("Accounts unavailable")

    response = client.post("/orders", json=order_payload)

    assert response.status_code == 503
    assert response.json() == {"detail": "Сервис клиентов недоступен"}
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0
    accounts_http.assert_called_once()


@pytest.mark.parametrize("status_code", [302, 500, 503])
def test_unsuccessful_account_check_returns_503_without_saving_order(
    client, order_payload, db_session, accounts_http, status_code
):
    accounts_http.side_effect = None
    accounts_http.return_value = httpx.Response(status_code)

    response = client.post("/orders", json=order_payload)

    assert response.status_code == 503
    assert response.json() == {"detail": "Сервис клиентов недоступен"}
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0
    accounts_http.assert_called_once()
