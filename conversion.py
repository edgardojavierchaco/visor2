import pandas as pd

# Lee el archivo Excel
df = pd.read_excel('colec_coord1.xlsx')

# Escribe el DataFrame en un archivo CSV con el delimitador, comillas y escape especificados
df.to_csv('colectivos.csv', sep='|', quoting=1, escapechar=';', index=False)

# Abrir el archivo CSV y eliminar los caracteres de nueva línea al final de cada línea
with open('colectivos.csv', 'r') as file:
    lines = file.readlines()

with open('colectivos.csv', 'w') as file:
    for line in lines:
        if line.strip():  # Verifica si la línea no está vacía
            file.write(line.rstrip('\n') + '\n')
