import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import psycopg2

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Cargar la clave de cifrado
with open("secret.key", "rb") as key_file:
    key = key_file.read()

# Crear un objeto Fernet
cipher = Fernet(key)

# Desencriptar los datos
host = cipher.decrypt(os.getenv('POSTGRES_HOST').encode()).decode()
port = cipher.decrypt(os.getenv('POSTGRES_PORT').encode()).decode()
db = cipher.decrypt(os.getenv('POSTGRES_DB').encode()).decode()
user = cipher.decrypt(os.getenv('POSTGRES_USER').encode()).decode()
password = cipher.decrypt(os.getenv('POSTGRES_PASSWORD').encode()).decode()
db_name1 = cipher.decrypt(os.getenv('DB_NAME1').encode()).decode()

# Establecer la conexión a la base de datos
connection = psycopg2.connect(
    host=host,
    port=port,
    database=db,
    user=user,
    password=password
)
