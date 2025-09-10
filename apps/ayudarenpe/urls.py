from django.urls import path
from . import views

app_name = "ayudarenpe"

urlpatterns = [
    path("", views.index, name="index"),
    path("faq/", views.faq_list, name="faq_list"),
    path("glosario/", views.glosario_list, name="glosario_list"),
]

