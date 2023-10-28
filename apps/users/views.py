from typing import Any, Dict
from django import http
from django.contrib.auth.views import LoginView
from django.forms import TextInput
from django.shortcuts import redirect

class LoginFormView(LoginView):
    template_name='users/login.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/cards/')
        print(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Iniciar Sesión'
        return context
    