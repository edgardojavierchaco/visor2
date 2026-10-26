from django.urls import path, include
from apps.evaluaciones_educativas.views import dashboard
from apps.evaluaciones_educativas.ver_como import aplicar_ver_como

app_name='evaluaciones_educativas'

# Todo lo que esté acá responde como el usuario simulado en modo "Ver como".
# Las URLs de ver_como quedan afuera: siempre trabajan con el usuario real.
urlpatterns = aplicar_ver_como([
    path('', dashboard.dashboard, name='dashboard'),
    path('fluidez_2025/', include('apps.evaluaciones_educativas.urls.fluidez_2025', namespace='fluidez_2025')),
    path('fluidez_octubre_2026/', include('apps.evaluaciones_educativas.urls.fluidez_octubre_2026', namespace='fluidez_octubre_2026')),
    path('diagnostico_2026/', include('apps.evaluaciones_educativas.urls.diagnostico_2026', namespace='diagnostico_2026')),
    path('fluidez_2026/', include('apps.evaluaciones_educativas.urls.fluidez_2026', namespace='fluidez_2026')),
    path('diagnostico_2025/', include('apps.evaluaciones_educativas.urls.diagnostico_2025', namespace='diagnostico_2025')),
    path('validaciones_2026/', include('apps.evaluaciones_educativas.urls.validaciones_2026', namespace='validaciones_2026')),
    path('monitoreo_personas_2026/', include('apps.evaluaciones_educativas.urls.monitoreo_personas_2026', namespace='monitoreo_personas_2026')),
]) + [
    path('ver_como/', include('apps.evaluaciones_educativas.urls.ver_como', namespace='ver_como')),
]

