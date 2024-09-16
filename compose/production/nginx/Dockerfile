FROM nginx:alpine

# Elimina la configuración por defecto
RUN rm /etc/nginx/conf.d/default.conf

# Copia la configuración personalizada de nginx
COPY ./nginx.conf /etc/nginx/conf.d/

# Copia los archivos estáticos desde la carpeta build del proyecto
COPY ./staticfiles /usr/share/nginx/static

# Copia los archivos de media desde la carpeta de medios
COPY ./apps/media /usr/share/nginx/media
