import csv
import zipfile
import os
import unicodedata

INPUT_FILE = "integracion_fp_talleres.csv"
OUTPUT_TXT = "integracion_fp_talleres.txt"
OUTPUT_ZIP = "integracion_fp_talleres.zip"

CAMPOS = 27
SEP = "|"


def normalizar_nombre(nombre):
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = nombre.encode("ascii", "ignore").decode("ascii")
    return nombre.replace(" ", "_")


with open(INPUT_FILE, encoding="utf-8") as fin, \
     open(OUTPUT_TXT, "w", encoding="utf-8") as fout:

    for linea in fin:
        linea = linea.rstrip("\n")

        # separar por pipe
        campos = linea.split(SEP)

        # tomar SOLO los primeros 27
        campos = campos[:CAMPOS]

        # completar si faltan
        if len(campos) < CAMPOS:
            campos += [""] * (CAMPOS - len(campos))

        # escribir EXACTAMENTE 27
        fout.write(SEP.join(campos) + "\n")


with zipfile.ZipFile(normalizar_nombre(OUTPUT_ZIP), "w", zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(OUTPUT_TXT, arcname=os.path.basename(OUTPUT_TXT))

print("✔ Archivo corregido: 27 campos exactos, sin pipes extras")