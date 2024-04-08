import psycopg2
from passlib.hash import argon2

# Establecer la conexión a la base de datos
conn = psycopg2.connect(
    dbname="visualizador",
    user="visualizador",
    password="Estadisticas24",
    host="sigechaco.com.ar",
    port="5432"
)

# Crear un cursor para ejecutar consultas SQL
cur = conn.cursor()

# Obtener las contraseñas actuales de la tabla users_customuser
cur.execute("SELECT id, password FROM users_customuser")
rows = cur.fetchall()

# Actualizar las contraseñas cifrando con Argon2
for row in rows:
    user_id, current_password = row
    hashed_password = argon2.hash(current_password)
    cur.execute("UPDATE users_customuser SET password = %s WHERE id = %s", (hashed_password, user_id))

# Confirmar la transacción y cerrar la conexión
conn.commit()
conn.close()
