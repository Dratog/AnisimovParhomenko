"""HTTP-клиенты для проверки реально запущенных сервисов."""

import os
import time
from collections.abc import Iterator

import httpx
import pytest


def _wait_for_service(client: httpx.Client) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            if client.get("/health").status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(0.2)
    pytest.fail(f"Сервис {client.base_url} не готов к интеграционной проверке")


@pytest.fixture(scope="session")
def accounts_client() -> Iterator[httpx.Client]:
    url = os.getenv("ACCOUNTS_TEST_URL", "http://127.0.0.1:8001")
    with httpx.Client(base_url=url, timeout=5.0) as client:
        _wait_for_service(client)
        yield client


@pytest.fixture(scope="session")
def orders_client() -> Iterator[httpx.Client]:
    url = os.getenv("ORDERS_TEST_URL", "http://127.0.0.1:8002")
    with httpx.Client(base_url=url, timeout=5.0) as client:
        _wait_for_service(client)
        yield client
