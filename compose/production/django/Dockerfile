# =========================================================
# BASE
# =========================================================
FROM python:3.10-slim-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# =========================================================
# SYSTEM DEPENDENCIES (BUILD ONLY)
# =========================================================
FROM base AS builder-system

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libpq-dev \
    libffi-dev \
    gdal-bin \
    libgdal-dev \
    gettext \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /build

# SOLO requirements primero (cache máximo)
COPY ./requirements/ /requirements/

RUN pip install --upgrade pip setuptools wheel cython

RUN pip wheel --no-cache-dir --wheel-dir /wheels \
    -r /requirements/production.txt

# =========================================================
# RUNTIME
# =========================================================
FROM base AS runtime

ARG APP_HOME=/app

ENV APP_HOME=${APP_HOME}
WORKDIR ${APP_HOME}

RUN useradd -m django

# SOLO runtime libs (sin compiladores!)
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq5 \
    gdal-bin \
    gettext \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder-system /wheels /wheels

RUN pip install --no-cache-dir --no-index \
    --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# entrypoints
COPY --chown=django:django ./compose/production/django/entrypoint /entrypoint
RUN chmod +x /entrypoint

COPY --chown=django:django ./compose/production/django/start /start
RUN chmod +x /start

# código
COPY --chown=django:django . ${APP_HOME}

RUN mkdir -p media productionfiles && \
    chown -R django:django ${APP_HOME}

USER django

ENTRYPOINT ["/entrypoint"]
CMD ["/start"]