from cryptography.fernet import Fernet

# Generar una clave y guardarla en un archivo
key = Fernet.generate_key()
with open("secret.key", "wb") as key_file:
    key_file.write(key)

# Crear un objeto Fernet
cipher = Fernet(key)

# Datos a encriptar
data = {
    "POSTGRES_HOST": "visoreducativochaco.com.ar",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "visualizador",
    "POSTGRES_USER": "visualizador",
    "POSTGRES_PASSWORD": "Estadisticas24",
    "DB_NAME1": "Padron"
}

# Encriptar los datos
encrypted_data = {k: cipher.encrypt(v.encode()).decode() for k, v in data.items()}

# Mostrar los datos encriptados
for key, value in encrypted_data.items():
    print(f"{key}={value}")
