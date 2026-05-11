# =========================================================
# BASE
# =========================================================
FROM python:3.10-slim-bullseye AS python-base

LABEL maintainer="Edgardo Javier Gómez"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# =========================================================
# BUILD STAGE
# =========================================================
FROM python-base AS python-build

ARG BUILD_ENVIRONMENT=production

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /build

# Copiar sólo requirements para maximizar caché
COPY ./requirements /requirements

RUN pip install --upgrade pip setuptools wheel

RUN pip wheel \
    --wheel-dir /wheels \
    -r /requirements/${BUILD_ENVIRONMENT}.txt

# =========================================================
# RUNTIME
# =========================================================
FROM python-base AS python-run

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV HOME=/home/django
ENV APP_HOME=${APP_HOME}
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

# Usuario no root
RUN useradd -m django

# SOLO runtime libs
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq5 \
    gettext \
    gdal-bin \
    libgdal-dev \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Wheels compiladas
COPY --from=python-build /wheels /wheels

RUN pip install --no-cache-dir --no-index \
    --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# Entrypoint
COPY --chown=django:django ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

# Start
COPY --chown=django:django ./compose/production/django/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# Proyecto
COPY --chown=django:django . ${APP_HOME}

# Directorios persistentes
RUN mkdir -p \
    ${APP_HOME}/media \
    ${APP_HOME}/productionfiles \
    && chown -R django:django ${APP_HOME}

USER django

ENTRYPOINT ["/entrypoint"]

CMD ["/start"]