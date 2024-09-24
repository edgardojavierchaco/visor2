FROM nginx:alpine

# Crea los directorios necesarios y establece los permisos
RUN mkdir -p /var/cache/nginx/client_temp && \
    chown -R nginx:nginx /var/cache/nginx

# Copia la configuración personalizada de nginx
COPY ./compose/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copia los archivos estáticos y media desde el host
COPY ./apps/media /usr/share/nginx/html/media

# Establece permisos en los directorios de archivos estáticos y media
RUN chown -R nginx:nginx /usr/share/nginx/html/static /usr/share/nginx/html/media
