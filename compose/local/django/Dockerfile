# ==============================
# Etapa base: Python 3.10 slim
# ==============================
FROM python:3.10.10-slim-bullseye AS python

LABEL maintainer="Edgardo Javier Gómez"

# ==============================
# Etapa build: instalar dependencias y crear wheels
# ==============================
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=local

# Configuración para APT: retries y timeout
RUN echo 'Acquire::Retries "5"; Acquire::http::Timeout "120";' > /etc/apt/apt.conf.d/99-retries \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        libpq-dev \
        wkhtmltopdf \
    || apt-get install --no-install-recommends -y --fix-missing \
        build-essential \
        libpq-dev \
        wkhtmltopdf \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY ./requirements .

# Actualizar pip y crear wheels con timeout extendido
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip --default-timeout=300 wheel --wheel-dir /usr/src/app/wheels -r ${BUILD_ENVIRONMENT}.txt

# Instalar modelos pesados de spaCy por separado
RUN pip install --no-cache-dir \
    https://github.com/explosion/spacy-models/releases/download/es_core_news_md-3.8.0/es_core_news_md-3.8.0-py3-none-any.whl

# ==============================
# Etapa run: instalar dependencias y ejecutar app
# ==============================
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

# Dependencias de sistema necesarias para Django y geoprocesamiento
RUN echo 'Acquire::Retries "5"; Acquire::http::Timeout "120";' > /etc/apt/apt.conf.d/99-retries \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        libpq-dev \
        gettext \
        binutils \
        libproj-dev \
        gdal-bin \
        wkhtmltopdf \
    || apt-get install --no-install-recommends -y --fix-missing \
        libpq-dev \
        gettext \
        binutils \
        libproj-dev \
        gdal-bin \
        wkhtmltopdf \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

# Copiar wheels desde la etapa build
COPY --from=python-build-stage /usr/src/app/wheels /wheels/

# Instalar paquetes Python desde wheels locales
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels/

# Copiar entrypoint y start scripts
COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

COPY ./compose/local/django/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# Copiar código de la app
COPY . ${APP_HOME}

# Entrypoint final
ENTRYPOINT ["/entrypoint"]


