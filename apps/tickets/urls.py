from django.urls import path
from apps.tickets import views

app_name='sge'

urlpatterns = [

    path("nuevo/",views.crear_ticket,name="crear_ticket"),

    path("mis/",views.mis_tickets,name="mis_tickets"),

    path("gestor/",views.tickets_gestor,name="tickets_gestor"),

    path("<int:id>/",views.ver_ticket,name="ver_ticket"),

    path("<int:id>/cerrar/",views.cerrar_ticket,name="cerrar_ticket"),

]