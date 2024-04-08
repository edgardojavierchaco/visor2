import csv

# Nombre del archivo CSV de entrada y el nombre de la tabla en la base de datos
csv_file = 'alumnos_sie2.csv'
table_name = 'alumnos_sie'

# Abre el archivo CSV y lee los datos
with open(csv_file, 'r') as file:
    csv_reader = csv.DictReader(file)
    headers = csv_reader.fieldnames

    # Genera las declaraciones SQL INSERT
    sql_statements = []
    for row in csv_reader:
        values = ', '.join(f"'{row[header]}'" for header in headers)
        sql_statement = f"INSERT INTO {table_name} ({', '.join(headers)}) VALUES ({values});"
        sql_statements.append(sql_statement)

# Escribe las declaraciones SQL en un archivo .sql
sql_file = 'datos.sql'
with open(sql_file, 'w') as file:
    file.write('\n'.join(sql_statements))

print(f"Se han generado las declaraciones SQL en el archivo '{sql_file}'.")
