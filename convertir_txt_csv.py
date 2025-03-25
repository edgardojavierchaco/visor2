import csv

def txt_to_csv(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as txt_file:
        with open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
            reader = csv.reader(txt_file, delimiter='|', quotechar='"')
            writer = csv.writer(csv_file)
            
            for row in reader:
                writer.writerow(row)

# Ejemplo de uso
txt_to_csv('alumnos_sie.txt', 'alumnos_sie.csv')
