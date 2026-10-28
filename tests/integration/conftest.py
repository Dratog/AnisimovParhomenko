"""HTTP-клиенты для проверки реально запущенных сервисов."""

import os
import subprocess
import time
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

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


@pytest.fixture(params=[("stop", "start"), ("pause", "unpause")], ids=["stopped", "unresponsive"])
def accounts_outage(
    request: pytest.FixtureRequest, accounts_client: httpx.Client, orders_client: httpx.Client
) -> AbstractContextManager[str]:
    # Управляем только локальным Compose, к которому обращаются HTTP-клиенты.
    for client, port in [(accounts_client, 8001), (orders_client, 8002)]:
        if client.base_url.host not in {"127.0.0.1", "localhost"} or client.base_url.port != port:
            pytest.fail("Проверка отказов требует локального Compose на портах 8001/8002")

    interrupt, recover = request.param
    project_root = Path(__file__).resolve().parents[2]

    @contextmanager
    def outage() -> Iterator[str]:
        try:
            subprocess.run(
                ["docker", "compose", interrupt, "accounts"],
                cwd=project_root,
                check=True,
                timeout=30,
            )
            yield interrupt
        finally:
            subprocess.run(
                ["docker", "compose", recover, "accounts"],
                cwd=project_root,
                check=True,
                timeout=30,
            )
            _wait_for_service(accounts_client)

    return outage()
