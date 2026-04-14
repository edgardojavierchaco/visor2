import pandas as pd
import re
import csv

# 🔧 Función para limpiar números
def limpiar_numero(valor):
    if pd.isna(valor):
        return 0
    if isinstance(valor, str):
        valor = valor.strip()
        if valor in ["", "-"]:
            return 0
        valor = valor.replace(".", "")  # miles
    try:
        return int(valor)
    except:
        return 0

# 📥 Leer Excel
df = pd.read_excel("/home/edgardo/Documentos/visor2/tabla_poblacion.xlsx", header=None)

data = []
current_area = None
reading_data = False

for i, row in df.iterrows():
    
    row_str = " ".join([str(x) for x in row if pd.notna(x)]).upper()

    # 🔍 Detectar AREA
    if "AREA" in row_str:
        match = re.search(r'(\d{9})', row_str)
        if match:
            current_area = match.group(1)
        reading_data = False
        continue

    # 🔹 Detectar encabezado
    if "MUJER" in row_str and ("VARON" in row_str or "MASCUL" in row_str):
        reading_data = True
        continue

    # 📊 Leer datos
    if reading_data and current_area:
        edad = row[1]

        if pd.isna(edad):
            reading_data = False
            continue

        if isinstance(edad, str) and "TOTAL" in edad.upper():
            reading_data = False
            continue

        mujer = limpiar_numero(row[2])
        varon = limpiar_numero(row[3])
        total = limpiar_numero(row[4])

        if total == 0:
            total = mujer + varon

        data.append({
            "area": str(current_area).strip(),
            "edad": str(edad).strip(),
            "mujer": mujer,
            "varon": varon,
            "total": total
        })

# 📊 Crear DataFrame
resultado = pd.DataFrame(data)

# 🧹 limpieza final
resultado["area"] = resultado["area"].astype(str).str.strip()
resultado["edad"] = resultado["edad"].astype(str).str.strip()

# 🔥 AGREGAR ID (CLAVE)
resultado.insert(0, "id", range(1, len(resultado) + 1))

# 💾 Exportar CSV listo para PostgreSQL
resultado.to_csv(
    "/home/edgardo/Documentos/visor2/salida.csv",
    index=False,
    encoding="utf-8",
    quoting=csv.QUOTE_ALL
)

print("✅ CSV generado correctamente")
print("Filas:", len(resultado))
print(resultado.head())