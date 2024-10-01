import csv

def convertir_csv_a_txt(csv_file, txt_file):
    with open(csv_file, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        with open(txt_file, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile, delimiter='|')
            for row in reader:
                writer.writerow(row)

# Ejemplo de uso
csv_file = 'bnhalumnoscomun2024_rect.csv'  # Reemplaza con el nombre de tu archivo CSV
txt_file = 'bnhalumnoscomun2024_rect.txt'  # Nombre del archivo de salida

convertir_csv_a_txt(csv_file, txt_file)
