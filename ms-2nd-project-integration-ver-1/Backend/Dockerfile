FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system ieum \
    && useradd --system --gid ieum --home-dir /app ieum

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY --chown=ieum:ieum . .

USER ieum

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && if [ \"$APP_MODE\" = \"demo\" ]; then python -m ieum.demo seed; fi && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
