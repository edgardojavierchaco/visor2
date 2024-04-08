# apps/users/views.py

from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import check_password  # Importa esta línea
from django.shortcuts import render, redirect
from apps.users.models import Usuarios

def tu_vista(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Username: {username}, Password: {password}")

        # Autenticar al usuario en la base de datos 'visualizador'
        user = authenticate(request, username=username, password=password)
        print(f"User: {user}")

        if user is not None:
            # Las credenciales son válidas, iniciar sesión
            print("Credenciales válidas")
            if user.check_password(password):
                print("Contraseña válida")
                login(request, user)
                return redirect('/cards/')
            else:
                print("Contraseña no válida")
        else:
            # Las credenciales no son válidas, puedes manejar esto como desees
            print("Credenciales no válidas")
            return render(request, 'users/login.html', {'error_message': 'Credenciales no válidas'})

    return render(request, 'users/login.html')
