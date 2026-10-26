from django.urls import path
from apps.evaluaciones_educativas.views import ver_como

app_name = "ver_como"

urlpatterns = [
    path('', ver_como.selector, name='selector'),
    path('iniciar/', ver_como.iniciar, name='iniciar'),
    path('edicion/', ver_como.cambiar_edicion, name='edicion'),
    path('salir/', ver_como.salir, name='salir'),
]
