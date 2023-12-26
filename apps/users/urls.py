#from django.urls import path
from config.urls import path
from apps.users.views import tu_vista

app_name='users'

urlpatterns=[
    path('login/', view=tu_vista, name='login'),
]
