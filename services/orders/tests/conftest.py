"""Общая подготовка для тестов сервиса заказов."""

from collections.abc import Iterator
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from orders.db import Base, get_session
from orders.main import app


@pytest.fixture(autouse=True)
def accounts_http(monkeypatch) -> Mock:
    """Подменяет исходящий HTTP, не затрагивая транспорт FastAPI TestClient."""

    def existing_account(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.startswith("/accounts/")
        account_id = int(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(
            200,
            json={
                "id": account_id,
                "name": "Иван Петров",
                "email": "ivan@example.com",
                "phone": None,
                "created_at": "2026-10-23T12:00:00",
            },
        )

    handler = Mock(side_effect=existing_account)
    transport = httpx.MockTransport(handler)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await transport.handle_async_request(request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", handle_async_request)
    return handler


@pytest.fixture()
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_session() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(client) -> Iterator[Session]:
    """Открывает сессию той же БД, которую использует тестовый API."""
    yield from app.dependency_overrides[get_session]()


@pytest.fixture()
def order_payload() -> dict:
    return {"account_id": 1, "item": "Кофемолка", "quantity": 2}
