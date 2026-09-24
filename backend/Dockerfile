FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system eillen && adduser --system --ingroup eillen eillen
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY alembic ./alembic
COPY bin ./bin
RUN chown -R eillen:eillen /app
USER eillen
EXPOSE 8080
CMD ["./bin/start-api"]
