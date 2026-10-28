"""Служебный endpoint /health подтверждает доступность сервиса заказов."""

from fastapi.testclient import TestClient

from orders.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "orders"}
