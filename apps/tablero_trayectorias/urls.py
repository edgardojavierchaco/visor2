from django.urls import path
from . import views
app_name='trayectorias'
urlpatterns=[
 path('',views.dashboard,name='dashboard'),
 path('guia/',views.guia,name='guia'),
 path('api/datos/',views.datos,name='datos'),
 path('api/exportar/',views.exportar,name='exportar'),
]
