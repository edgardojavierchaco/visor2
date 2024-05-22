import csv

# Ruta al archivo CSV de entrada y salida
archivo_entrada = '/home/edgardochaco/Imágenes/nominadocentesabril.csv'
archivo_salida = '/home/edgardochaco/Imágenes/nominadocentesabril_processed.csv'

# Abre el archivo CSV de entrada y crea el archivo CSV de salida
with open(archivo_entrada, mode='r', encoding='utf-8') as infile, \
     open(archivo_salida, mode='w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.DictReader(infile, delimiter='|')
    fieldnames = reader.fieldnames
    writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter='|')
    
    writer.writeheader()
    for row in reader:
        if row['activo'] == 'Sin Datos':
            row['activo'] = 'False'  # o 'True' según tu contexto
        writer.writerow(row)

print("Preprocesamiento del archivo CSV completado.")
