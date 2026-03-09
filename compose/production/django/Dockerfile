# Base Python
FROM python:3.10.10-slim-bullseye AS python-base
LABEL maintainer="Edgardo Javier Gómez"

# Stage build
FROM python-base AS python-build
ARG BUILD_ENVIRONMENT=production

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    wkhtmltopdf \
  && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

COPY ./requirements ./
RUN pip wheel --wheel-dir /wheels -r ${BUILD_ENVIRONMENT}.txt

# Stage run
FROM python-base AS python-run
ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

# Crear usuario django
RUN useradd -m django

WORKDIR ${APP_HOME}

# Instalar dependencias del sistema
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    gettext \
    wkhtmltopdf \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copiar ruedas e instalar dependencias de Python
COPY --from=python-build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
  && rm -rf /wheels

# Copiar entrypoints
COPY --chown=django:django ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

COPY --chown=django:django ./compose/production/django/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# Copiar código fuente (excepto media)
COPY --chown=django:django .. ${APP_HOME}

# Crear carpetas persistentes y dar permisos correctos
RUN mkdir -p ${APP_HOME}/productionfiles ${APP_HOME}/media && \
    chown -R django:django ${APP_HOME}/productionfiles ${APP_HOME}/media && \
    chmod -R 775 ${APP_HOME}/productionfiles ${APP_HOME}/media

# Usar usuario no root
USER django

ENTRYPOINT ["/entrypoint"]
