# ==============================
# BASE IMAGE
# ==============================
FROM python:3.10-slim-bullseye AS base

LABEL maintainer="Edgardo Javier Gómez"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ==============================
# SYSTEM DEPENDENCIES
# ==============================
FROM base AS system

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    gettext \
    curl \
    libxml2-dev \
    libxslt1-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    proj-data \
    proj-bin \
 && rm -rf /var/lib/apt/lists/*

# ==============================
# PYTHON DEPENDENCIES
# ==============================
FROM system AS python-deps

ARG BUILD_ENVIRONMENT=local

COPY requirements/ /requirements/

RUN python -m pip install --upgrade pip setuptools wheel

RUN pip install --default-timeout=300 \
    -r /requirements/${BUILD_ENVIRONMENT}.txt

# ==============================
# RUNTIME IMAGE
# ==============================
FROM system AS runtime

ARG APP_HOME=/app

# ==============================
# HOST UID/GID
# ==============================
ARG UID=1000
ARG GID=1000

ENV HOME=/home/django

WORKDIR ${APP_HOME}

# ==============================
# USER
# ==============================
RUN groupadd -g ${GID} django && \
    useradd -m \
    -u ${UID} \
    -g django \
    -s /bin/bash \
    django

# ==============================
# COPY PYTHON PACKAGES
# ==============================
COPY --from=python-deps /usr/local /usr/local

# ==============================
# ENTRYPOINTS
# ==============================
COPY compose/production/django/entrypoint /entrypoint
COPY compose/local/django/start /start

RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint
RUN sed -i 's/\r$//g' /start && chmod +x /start

# ==============================
# REQUIRED DIRS
# ==============================
RUN mkdir -p \
    /app/staticfiles \
    /app/media \
    /app/productionfiles \
    /app/logs

# ==============================
# COPY PROJECT
# ==============================
COPY . ${APP_HOME}

# ==============================
# PERMISSIONS
# ==============================
RUN chown -R django:django /app

# ==============================
# NON ROOT USER
# ==============================
USER django

# ==============================
# ENTRYPOINT
# ==============================
ENTRYPOINT ["/entrypoint"]