import pandas as pd

#serie = pd.Series([1,2,3,4,5,6,43])

#print(serie)

df=pd.read_csv("datosinicial.csv")
print(df)

df2=pd.read_excel("/home/edgardochaco/Descargas/2024-03-07_datagrid_export.xlsx")
print(df2)