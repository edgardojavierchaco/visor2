import csv

def convertir_csv_a_txt(csv_file, txt_file):
    # Abrimos el archivo CSV de entrada con ';' como delimitador
    with open(csv_file, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile, delimiter='|')  # Usamos ';' como delimitador de entrada
        # Abrimos el archivo TXT de salida con '|' como delimitador
        with open(txt_file, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile, delimiter='|')  # Usamos '|' como delimitador de salida
            for row in reader:
                writer.writerow(row)

# Ejemplo de uso
csv_file = 'bnh2024.csv'  # Reemplaza con el nombre de tu archivo CSV
txt_file = 'bnh2024.txt'  # Nombre del archivo de salida

convertir_csv_a_txt(csv_file, txt_file)

