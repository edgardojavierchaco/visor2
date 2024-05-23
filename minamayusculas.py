import csv

# Define los nombres de las columnas que deseas convertir a mayúsculas
COLUMNAS_A_CONVERTIR = ['apellido', 'nombres']

# Ruta al archivo CSV de entrada y de salida
archivo_entrada = '/home/edgardochaco/Imágenes/directores.csv'
archivo_salida = '/home/edgardochaco/Imágenes/directores_convertido.csv'

try:
    # Abre el archivo CSV de entrada y crea el archivo CSV de salida
    with open(archivo_entrada, mode='r', encoding='utf-8') as infile, \
         open(archivo_salida, mode='w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.DictReader(infile, delimiter='|')
        fieldnames = reader.fieldnames
        
        # Validar que las columnas especificadas existan en el archivo CSV
        if not all(col in fieldnames for col in COLUMNAS_A_CONVERTIR):
            raise ValueError(f"Una o más columnas especificadas no se encuentran en el archivo CSV. Columnas disponibles: {fieldnames}")
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter='|')
        
        # Escribir la cabecera
        writer.writeheader()
        
        # Procesar cada fila
        for row in reader:
            # Convertir los valores de las columnas especificadas a mayúsculas
            for columna in COLUMNAS_A_CONVERTIR:
                if row[columna] is not None:
                    row[columna] = row[columna].upper()
            # Escribir la fila modificada al archivo de salida
            writer.writerow(row)

    print("Conversión a mayúsculas completada.")
except Exception as e:
    print(f"Ocurrió un error: {e}")

