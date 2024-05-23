import csv

# Nombre del archivo CSV de entrada y salida
archivo_entrada = '/home/edgardochaco/Imágenes/docenteshscatedrasabril.csv'
archivo_salida = '/home/edgardochaco/Imágenes/docenteshscatedrasabrilcorregido.csv'

# Nombre de la columna que contiene los nombres con comas
nombre_columna = 'nombre'

# Función para eliminar las comas de los nombres en la columna específica
def eliminar_comas(nombre_columna):
    return nombre_columna.replace(',', '')

# Abrir el archivo de entrada y crear un archivo de salida
with open(archivo_entrada, 'r', newline='') as csv_entrada, \
     open(archivo_salida, 'w', newline='') as csv_salida:
    # Configurar el lector CSV y el escritor CSV
    lector_csv = csv.DictReader(csv_entrada)
    encabezados = lector_csv.fieldnames
    escritor_csv = csv.DictWriter(csv_salida, fieldnames=encabezados)
    escritor_csv.writeheader()

    # Procesar cada fila del archivo de entrada
    for fila in lector_csv:
        # Eliminar las comas de la columna de nombres
        fila[nombre_columna] = eliminar_comas(fila[nombre_columna])
        # Escribir la fila procesada en el archivo de salida
        escritor_csv.writerow(fila)

print("Se han eliminado las comas de la columna de nombres en el archivo CSV.")
