FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ARG DEBUG=false

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    gcc \
    build-essential \
    python3-dev \
    libpq-dev \
    git \
    cmake \
    zlib1g-dev \
    libsqlite3-dev \
    && git clone https://github.com/felt/tippecanoe.git /tmp/tippecanoe \
    && cd /tmp/tippecanoe \
    && make -j$(nproc) \
    && make install \
    && cd / \
    && rm -rf /tmp/tippecanoe \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$DEBUG" = "true" ] ; then \
    uv sync --frozen --no-install-project ; \
    else \
    uv sync --frozen --no-install-project --no-dev ; \
    fi

COPY . ./code
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$DEBUG" = "true" ] ; then \
    uv sync --frozen ; \
    else \
    uv sync --frozen --no-dev ; \
    fi

FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libpq5 \
    sqlite3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /.venv
COPY --from=builder /app/code /app
COPY --from=builder /usr/local/bin/tippecanoe /usr/local/bin/tippecanoe

ENV PATH="/.venv/bin:$PATH"

WORKDIR /app

RUN mkdir -p /app/media /app/logs /app/staticfiles \
    && chmod 755 /app/logs \
    && python manage.py collectstatic --noinput --clear || true

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
