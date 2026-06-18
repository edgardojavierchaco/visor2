from config.urls import path
from .views import *
from .views_reset_cuil import (
    ResetPasswordCUILView, 
    ConfirmResetCUILView
)

app_name='logueo'

urlpatterns=[
    # LOGIN
    path('',LoginFormView.as_view(),name='login'),    
    path('logout/',CustomLogoutView.as_view(),name='logout'),
    
    # --------------------------------
    # CONFIRMAR DISPOSITIVO
    # --------------------------------
    path(
        'confirmar-dispositivo/<uuid:token>/',
        confirmar_dispositivo,
        name='confirmar_dispositivo'
    ),
    
    # --------------------------------
    # CERRAR OTRAS SESIONES
    # --------------------------------
    path(
        'cerrar-otras-sesiones/',
        cerrar_otras_sesiones,
        name='cerrar_otras_sesiones'
    ),

    # --------------------------------
    # RESET CUIL
    # --------------------------------
    path('reset-cuil/', ResetPasswordCUILView.as_view(), name='reset_cuil'),
    path('confirm-reset-cuil/', ConfirmResetCUILView.as_view(), name='confirm_reset_cuil'),
]
