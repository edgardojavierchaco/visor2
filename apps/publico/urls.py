from config.urls import path
from .views import publico
from apps.publico import views

app_name='publico'

urlpatterns=[
    path('',views.publico,name='publico'),
]