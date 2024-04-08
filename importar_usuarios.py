import psycopg2
from apps.users.models import CustomUser

def load_data():
    try:
        connection = psycopg2.connect(
            user="visualizador",
            password="Estadisticas24",
            host="sigechaco.com.ar",
            port="5432",
            database="visualizador"
        )
        
        cursor = connection.cursor()
        
        cursor.execute("SELECT nombre, contraseña, email, activo, nombrecompleto, nivelacceso, telefono FROM usuarios_visor")
        rows = cursor.fetchall()
        
        for row in rows:
            nombre, contraseña, email, activo, nombrecompleto, nivelacceso, telefono = row
            # Aquí puedes aplicar la lógica de encriptación de la contraseña si es necesario
            CustomUser.objects.create(nombre=nombre, contraseña=contraseña, email=email, activo=activo,nombrecompleto=nombrecompleto, nivelacceso=nivelacceso, telefono=telefono)
            
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    load_data()
