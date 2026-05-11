# =========================================================
# BASE
# =========================================================
FROM python:3.10-slim-bullseye AS python-base

LABEL maintainer="Edgardo Javier Gómez"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# =========================================================
# SYSTEM DEPS
# =========================================================
FROM python-base AS system-deps

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libpq5 \
    gdal-bin \
    libgdal-dev \
    gettext \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# =========================================================
# BUILD
# =========================================================
FROM system-deps AS python-build

ARG BUILD_ENVIRONMENT=production

WORKDIR /build

COPY ./requirements /requirements

RUN pip install --upgrade pip setuptools wheel

RUN pip wheel \
    --wheel-dir /wheels \
    -r /requirements/${BUILD_ENVIRONMENT}.txt

# =========================================================
# RUNTIME
# =========================================================
FROM system-deps AS python-run

ARG APP_HOME=/app

ENV HOME=/home/django
ENV APP_HOME=${APP_HOME}

WORKDIR ${APP_HOME}

RUN useradd -m django

COPY --from=python-build /wheels /wheels

RUN pip install --no-cache-dir --no-index \
    --find-links=/wheels /wheels/* \
    && rm -rf /wheels

COPY --chown=django:django ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

COPY --chown=django:django ./compose/production/django/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

COPY --chown=django:django . ${APP_HOME}

RUN mkdir -p \
    ${APP_HOME}/media \
    ${APP_HOME}/productionfiles \
    && chown -R django:django ${APP_HOME}

USER django

ENTRYPOINT ["/entrypoint"]

CMD ["/start"]