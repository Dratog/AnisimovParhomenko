"""Подключение к базе данных сервиса заказов."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from orders.config import settings


class Base(DeclarativeBase):
    """Общий предок для таблиц заказов."""


def _engine_options(url: str) -> dict:
    # SQLite по умолчанию запрещает работу из нескольких потоков FastAPI.
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.database_url, **_engine_options(settings.database_url))
SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Отдаёт сессию на время запроса; в тестах её подменяют."""
    with SessionFactory() as session:
        yield session
