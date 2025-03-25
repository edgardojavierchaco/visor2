import hashlib

password = "30380789"
hashed_password = hashlib.sha256(password.encode()).hexdigest()

print(hashed_password)
