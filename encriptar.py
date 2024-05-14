import hashlib

password = "30380789"
hashed_password = hashlib.sha256(password.encode()).hexdigest()

print(hashed_password)

INSERT INTO usuarios (nombre, contraseña_hash) VALUES ('juancito', sha256('fadaddadafadfd'));


import csv
import hashlib

def calcular_hash_sha256(contraseña):
    return hashlib.sha256(contraseña.encode()).hexdigest()

archivo_csv = 'datos.csv'

archivo_csv_encriptado = 'datos_encriptados.csv'


with open(archivo_csv, 'r', newline='') as entrada:
    
    with open(archivo_csv_encriptado, 'w', newline='') as salida:
        
        lector_csv = csv.DictReader(entrada)
        
        campos = lector_csv.fieldnames
        escritor_csv = csv.DictWriter(salida, fieldnames=campos)
        
        escritor_csv.writeheader()

        
        for fila in lector_csv:
            
            contraseña_encriptada = calcular_hash_sha256(fila['contraseña'])
            
            fila['contraseña'] = contraseña_encriptada
            
            escritor_csv.writerow(fila)

print("Contraseñas encriptadas correctamente.")
