from django.urls import path, re_path
from .views import (
    mensajes_privados,
    DetailMs,
    CanalDetailView,
    Inbox,
    unirse_canal,
    elegir_canal,
    ChatView,
    obtener_mensajes,
)
from uuid import UUID

app_name='dm'

urlpatterns = [
    re_path(r'canal/(?P<pk>[\w-]+)', CanalDetailView.as_view()),
    path('chat/<str:username>', mensajes_privados),
    path('ms/<str:username>', DetailMs.as_view(), name='detailms'),
    path('inbox/', Inbox.as_view(), name='inbox'),
    path('unirse/<str:canal_nombre>/', unirse_canal, name='unirse_canal'),
    path('elegir-canal/', elegir_canal, name='elegir_canal'),    
    path('chat/<uuid:canal_id>/', ChatView.as_view(), name='chat'),
    path('api/mensajes/<uuid:canal_id>/', obtener_mensajes, name='obtener_mensajes'),
]
