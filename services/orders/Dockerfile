# ---------- этап 1: собираем зависимости и приложение ----------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./

# Этот слой зависит только от списка зависимостей, а не от исходников.
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY orders ./orders
RUN pip install --no-cache-dir --no-deps --prefix=/install .

# ---------- этап 2: собираем итоговый образ ----------
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 app \
    && mkdir /app \
    && chown app:app /app

COPY --from=builder /install /usr/local

# Здесь сервис создаёт SQLite-базу, поэтому каталог принадлежит app.
WORKDIR /app
USER app
EXPOSE 8000

CMD ["uvicorn", "orders.main:app", "--host", "0.0.0.0", "--port", "8000"]
