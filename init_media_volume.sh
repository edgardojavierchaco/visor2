#!/bin/bash
# init_media_volume.sh
# Inicializa el volumen de Docker con los archivos de media de producción
# sin sobrescribir lo que ya exista.

# Nombre del volumen
VOLUME_NAME="visor2_production_media_visor"

# Carpeta de media en tu proyecto (host)
SOURCE_DIR="$(pwd)/productionfiles/media"

# Directorio temporal para montar el volumen
TEMP_DIR="$(mktemp -d)"

echo "Montando volumen temporalmente en $TEMP_DIR..."
docker run --rm -v ${VOLUME_NAME}:/data -v $TEMP_DIR:/tmp busybox true

# Copiar archivos al volumen solo si no existen
echo "Copiando archivos desde $SOURCE_DIR al volumen..."
for file in $(find "$SOURCE_DIR" -type f); do
    REL_PATH="${file#$SOURCE_DIR/}"
    if [ ! -f "$TEMP_DIR/$REL_PATH" ]; then
        mkdir -p "$(dirname "$TEMP_DIR/$REL_PATH")"
        cp "$file" "$TEMP_DIR/$REL_PATH"
        echo "  + Copiado: $REL_PATH"
    else
        echo "  - Ignorado (ya existe): $REL_PATH"
    fi
done

# Montar el contenido de TEMP_DIR en el volumen
docker run --rm -v ${VOLUME_NAME}:/data -v $TEMP_DIR:/tmp busybox sh -c "cp -r /tmp/* /data/"

# Limpiar temporal
rm -rf "$TEMP_DIR"

echo "Inicialización del volumen completada ✅"