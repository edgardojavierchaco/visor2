#!/bin/bash

# ========================
# Script universal de mantenimiento Docker Compose
# ========================

# Verifica argumento
if [ -z "$1" ]; then
    echo "❌ Uso: $0 <archivo-docker-compose.yml>"
    exit 1
fi

ARCHIVO_COMPOSE="$1"

# Detectar entorno
if [[ "$ARCHIVO_COMPOSE" == *"prod"* || "$ARCHIVO_COMPOSE" == *"produccion"* ]]; then
    ENTORNO="producción"
    CUIDADO="⚠️"
else
    ENTORNO="local"
    CUIDADO=""
fi

echo "🔧 Iniciando mantenimiento en entorno **$ENTORNO** ($ARCHIVO_COMPOSE) $CUIDADO"
echo

# Mostrar uso de espacio antes
echo "📊 Espacio ocupado antes:"
docker system df
echo

# ====== LOCAL ======
if [[ "$ENTORNO" == "local" ]]; then

    echo "🛑 Deteniendo servicios..."
    docker-compose -f "$ARCHIVO_COMPOSE" down

    echo "🗑️ Eliminando contenedores detenidos..."
    docker container prune -f

    echo "🧹 Eliminando imágenes sin etiqueta..."
    docker image prune -f

    echo "🚧 Limpiando caché de build..."
    docker builder prune -f

    echo "🌐 Eliminando redes no usadas..."
    docker network prune -f

    echo "📦 Buscando volúmenes huérfanos..."
    volumenes=$(docker volume ls -qf dangling=true)
    if [ -n "$volumenes" ]; then
        echo "$volumenes"
        read -p "¿Eliminar volúmenes huérfanos? (s/n): " resp_vol
        if [[ "$resp_vol" =~ ^[sS]$ ]]; then
            docker volume prune -f
        else
            echo "❌ Volúmenes conservados."
        fi
    else
        echo "✅ No hay volúmenes huérfanos."
    fi

    read -p "¿Eliminar imágenes no utilizadas? (s/n): " resp_img
    if [[ "$resp_img" =~ ^[sS]$ ]]; then
        docker image prune -a -f
    else
        echo "❌ Imágenes conservadas."
    fi

    echo "🧼 Limpiando recursos del proyecto..."
    docker-compose -f "$ARCHIVO_COMPOSE" down --volumes --remove-orphans

# ====== PRODUCCIÓN ======
else
    echo "🛡️ Producción detectada: NO se eliminan imágenes, volúmenes ni se detienen servicios."
    echo "🗑️ Eliminando contenedores detenidos..."
    docker container prune -f

    echo "🚧 Limpiando caché de build..."
    docker builder prune -f

    echo "🌐 Eliminando redes no usadas..."
    docker network prune -f
fi

# Rebuild con --no-cache
read -p "¿Querés hacer build con --no-cache y levantar servicios? (s/n): " resp_build
if [[ "$resp_build" =~ ^[sS]$ ]]; then
    docker-compose -f "$ARCHIVO_COMPOSE" build --no-cache
    docker-compose -f "$ARCHIVO_COMPOSE" up -d
else
    echo "⏩ Saltando build."
fi

# Mostrar espacio después
echo
echo "📊 Espacio ocupado después:"
docker system df

echo
echo "✅ Mantenimiento completado en entorno $ENTORNO."
