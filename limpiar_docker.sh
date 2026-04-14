#!/bin/bash

echo "🚀 Limpiando imágenes dangling..."
docker image prune -f

echo "🧱 Limpiando cachés de build..."
docker builder prune -f

echo "🗑️ Eliminando contenedores detenidos..."
docker container prune -f

echo "🔍 Verificando volúmenes huérfanos (no usados por ningún contenedor)..."
volumenes_huerfanos=$(docker volume ls -qf dangling=true)

if [ -z "$volumenes_huerfanos" ]; then
    echo "✅ No se encontraron volúmenes huérfanos."
else
    echo "📦 Se encontraron los siguientes volúmenes huérfanos:"
    echo "$volumenes_huerfanos"
    echo
    read -p "¿Querés eliminarlos? (s/n): " opcion
    if [ "$opcion" == "s" ] || [ "$opcion" == "S" ]; then
        docker volume prune -f
        echo "🧹 Volúmenes huérfanos eliminados."
    else
        echo "❌ Volúmenes huérfanos conservados."
    fi
fi

echo "✅ Limpieza completa."

