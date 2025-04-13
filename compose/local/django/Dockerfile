# define un alias para la versión específica de python usada en este archivo.
FROM python:3.10.10-slim-bullseye as python

LABEL maintainer="Edgardo Javier Gómez"

# Python etapa de construcción
FROM python as python-build-stage

ARG BUILD_ENVIRONMENT=local

# Instala paquete apt
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencias para construir paquete Python
  build-essential \
  # psycopg2 dependencias
  libpq-dev \
  # wkhtmltopdf para generar PDFs desde HTML
  wkhtmltopdf

# Los requisitos se instalan aquí para garantizar que se almacenarán en caché.
COPY ./requirements .

# Crea dependencias y subdependencias de Python
RUN pip wheel --wheel-dir /usr/src/app/wheels  \
  -r ${BUILD_ENVIRONMENT}.txt


# Etapa 'run' de python
FROM python as python-run-stage

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV BUILD_ENV ${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

# Instala los requerimientos de las dependencias del systema
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg2 dependencias
  libpq-dev \
  # Translations dependencias
  gettext \
  # GDAL
  binutils \
  libproj-dev \
  gdal-bin \
  wkhtmltopdf \
  # Limpieza de archivos no utilizados
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Todas las copias de directorio absolutas ignoran la instrucción workdir. Todas las copias relativas del directorio se escriben según la instrucción workdir
# Copiar ruedas de dependencia de Python de python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels para instalar las dependencias de python
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
	&& rm -rf /wheels/

COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/local/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

# copia el código de la aplicación a WORKDIR
COPY . ${APP_HOME}

ENTRYPOINT ["/entrypoint"]
