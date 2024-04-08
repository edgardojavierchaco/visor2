from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from apps.usuarios.backends import UsuariosVisualizadorBackend  # Importa tu backend personalizado desde la aplicación usuarios
from apps.usuarios.models import UsuariosVisualizador


class LoginFormView(LoginView):
    template_name = 'login/login.html'

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        print(username, password)
        # Autenticar al usuario utilizando las credenciales proporcionadas
        user = UsuariosVisualizadorBackend().authenticate(self.request,username=username, password=password)
        print(user)
        if user is not None:
            # Las credenciales son válidas, iniciar sesión para el usuario
            login(self.request, user)

            # Redirigir según el nivel de acceso del usuario
            nivel_acceso = user.nivelacceso.tacceso
            if nivel_acceso == 'Publico':
                return redirect('/cards/')
            elif nivel_acceso == 'Director/a':
                return redirect('/usuarios/listado/')
            else:
                return redirect('ruta_para_otro_nivel')
        else:
            # Si las credenciales son inválidas, renderizar el formulario de inicio de sesión con un mensaje de error
            return self.form_invalid(form)

