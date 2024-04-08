import psycopg2
import hashlib
import csv

def hash_password(password):
    # Hash de la contraseña utilizando SHA-256
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    return hashed_password

# Conexión a la base de datos
conn = psycopg2.connect(
    dbname="visualizador",
    user="visualizador",
    password="Estadisticas24",
    host="sigechaco.com.ar",
    port="5432"
)

# Cursor
cursor = conn.cursor()

# Abre el archivo CSV
with open('usuariosbase.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Datos del usuario
        nombre = row['nombre']
        contraseña = row['contraseña']
        email = row['email']
        nombrecompleto = row['nombrecompleto']
        telefono = row['telefono']

        # Valores predeterminados
        activo = True
        nivelacceso = "Director"
        is_staff=True
        is_superuser=False

        # Hash de la contraseña
        hashed_password = hash_password(contraseña)

        # Verificar si el usuario ya existe en la tabla users_customuser
        cursor.execute("SELECT COUNT(*) FROM users_customuser WHERE nombre = %s", (nombre,))
        if cursor.fetchone()[0] == 0:
            # Si el usuario no existe, insertarlo en la tabla
            # Query SQL
            sql = "INSERT INTO users_customuser (nombre, password, email, activo, nombrecompleto, nivelacceso, telefono, is_staff, is_superuser) VALUES (%s, %s, %s, %s, %s, %s, %s,%s,%s)"
            values = (nombre, hashed_password, email, activo, nombrecompleto, nivelacceso, telefono, is_staff, is_superuser)

            # Ejecutar la consulta SQL
            cursor.execute(sql, values)

# Commit y cierre
conn.commit()
cursor.close()
conn.close()
