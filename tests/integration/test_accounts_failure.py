"""Отказ и восстановление настоящего сервиса клиентов."""

import time
from contextlib import AbstractContextManager
from uuid import uuid4

import httpx


def test_order_creation_recovers_after_accounts_outage(
    accounts_client: httpx.Client,
    orders_client: httpx.Client,
    accounts_outage: AbstractContextManager[str],
) -> None:
    response = accounts_client.post(
        "/accounts",
        json={"name": "Проверка отказа", "email": f"outage-{uuid4().hex}@example.com"},
    )
    assert response.status_code == 201, response.text
    account_id = response.json()["id"]
    payload = {"account_id": account_id, "item": "Чайник", "quantity": 1}

    with accounts_outage as interruption:
        started = time.monotonic()
        response = orders_client.post("/orders", json=payload)
        elapsed = time.monotonic() - started

        assert response.status_code == 503, response.text
        assert response.json() == {"detail": "Сервис клиентов недоступен"}
        assert elapsed < 3, f"Ответ при отказе занял {elapsed:.2f} с"
        if interruption == "pause":
            assert elapsed >= 1.5, f"Таймаут по умолчанию завершился за {elapsed:.2f} с"
        print(f"accounts {interruption}: HTTP 503 за {elapsed:.2f} с")

        response = orders_client.get("/orders", params={"account_id": account_id})
        assert response.status_code == 200, response.text
        assert response.json() == []

    response = orders_client.post("/orders", json=payload)
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["account_id"] == account_id
    assert order["item"] == payload["item"]
    assert order["quantity"] == payload["quantity"]

    response = orders_client.get("/orders", params={"account_id": account_id})
    assert response.status_code == 200, response.text
    assert response.json() == [order]
