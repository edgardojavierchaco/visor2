# ============================================================
# BASE PYTHON
# ============================================================
FROM python:3.10-slim-bookworm AS python-base

LABEL maintainer="Edgardo Javier Gómez"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1


# ============================================================
# STAGE BUILD
# ============================================================
FROM python-base AS python-build

ARG BUILD_ENVIRONMENT=production

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        libpq-dev \
        gdal-bin \
        libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copiar requirements
COPY ./requirements /requirements

# Actualizar herramientas de compilación Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Generar wheels
RUN pip wheel \
    --wheel-dir /wheels \
    -r /requirements/${BUILD_ENVIRONMENT}.txt


# ============================================================
# STAGE RUN
# ============================================================
FROM python-base AS python-run

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}


# ============================================================
# USUARIO DJANGO
# ============================================================
RUN useradd \
    --create-home \
    --shell /bin/bash \
    django


# ============================================================
# DEPENDENCIAS DEL SISTEMA
# ============================================================
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libpq5 \
        gdal-bin \
        libgdal32 \
        gettext \
        wkhtmltopdf \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*


# ============================================================
# GDAL
# ============================================================
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal


# ============================================================
# INSTALAR DEPENDENCIAS PYTHON
# ============================================================
COPY --from=python-build /wheels /wheels

RUN pip install \
        --no-cache-dir \
        --no-index \
        --find-links=/wheels \
        /wheels/* \
    && rm -rf /wheels


# ============================================================
# ENTRYPOINT
# ============================================================
COPY --chown=django:django \
    ./compose/production/django/entrypoint \
    /entrypoint

RUN sed -i 's/\r$//g' /entrypoint \
    && chmod +x /entrypoint


# ============================================================
# START
# ============================================================
COPY --chown=django:django \
    ./compose/production/django/start \
    /start

RUN sed -i 's/\r$//g' /start \
    && chmod +x /start


# ============================================================
# CÓDIGO FUENTE
# ============================================================
COPY --chown=django:django . ${APP_HOME}


# ============================================================
# STATIC / MEDIA
# ============================================================
RUN mkdir -p \
        ${APP_HOME}/productionfiles \
        ${APP_HOME}/media \
    && chown -R django:django \
        ${APP_HOME}/productionfiles \
        ${APP_HOME}/media \
    && chmod -R 775 \
        ${APP_HOME}/productionfiles \
        ${APP_HOME}/media


# ============================================================
# USUARIO FINAL
# ============================================================
USER django


# ============================================================
# ENTRYPOINT
# ============================================================
ENTRYPOINT ["/entrypoint"]