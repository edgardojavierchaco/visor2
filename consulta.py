""" import pandas as pd

# Cargar los archivos CSV en DataFrames
try:
    df1 = pd.read_csv('egresados7mo2023.csv', sep='|', quotechar='"')
    df2 = pd.read_csv('preinscriptos7mo2023.csv', sep='|', quotechar='"')
    df3 = pd.read_csv('regpreins1año2024.csv', sep='|', quotechar='"')
except pd.errors.ParserError as e:
    print("Error de lectura CSV:", e)
    # Manejar el error según sea necesario
    # Por ejemplo, puedes registrar el error o abortar el proceso.

# Fusionar los DataFrames en uno solo basado en la columna 'nro_documento'
merged_df = pd.merge(df1, df2, on='nro_documento', how='inner')
merged_df = pd.merge(merged_df, df3, on='nro_documento', how='inner')

# Guardar el DataFrame fusionado en un nuevo archivo CSV
merged_df.to_csv('registros_coincidentes.csv', index=False, sep='|', quotechar='"') """


import pandas as pd

# Cargar los archivos CSV en DataFrames
egresados_df = pd.read_csv('egresados7mo2023.csv', sep='|', quotechar='"')
regpreins_df = pd.read_csv('regpreins1año2024.csv', sep='|', quotechar='"')

# Fusionar los DataFrames usando el método 'left' para mantener todos los registros de 'egresados_df'
merged_df = pd.merge(egresados_df, regpreins_df, on='nro_documento', how='left', indicator=True)

# Filtrar los registros que están en 'egresados_df' pero no en 'regpreins_df'
not_in_regpreins_df = merged_df[merged_df['_merge'] == 'left_only'].copy()

# Eliminar la columna auxiliar '_merge'
not_in_regpreins_df.drop(columns=['_merge'], inplace=True)

# Guardar los registros en otro archivo CSV
not_in_regpreins_df.to_csv('registros_no_en_regpreins.csv', index=False, sep='|', quotechar='"')
