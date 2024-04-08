import hashlib

def hash_password(password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    return hashed_password

# Ejemplo de uso
password = "30380789"
hashed_password = hash_password(password)
print("Hash de la contraseña:", hashed_password)
