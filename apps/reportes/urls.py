#from django.urls import path
from config.urls import path
from django.views.generic import TemplateView
from . import views
from . import views_matric, views_infograf


app_name='reportes'

urlpatterns=[
    path('filtrado_cargos/',views.filtrado_cargos,name='filtrado_cargos'),
    path('filtrado_docentes/',views.filtrado_docentes,name='filtrado_docentes'),
    path('filtrado_horas/',views.filtrado_horas,name='filtrado_horas'),
    path('filtrado_aborigen/',views_matric.filtrado_aborigen,name='filtrado_aborigen'),
    path('filtrado_comesp/',views_matric.filtrado_comesp,name='filtrado_comesp'),
    path('filtrado_snu/',views_matric.filtrado_snu,name='filtrado_snu'),
    path('cargos/',views.filter_data_cargos,name='cargos'), # type: ignore
    path('docentes/',views.filter_data_docentes,name='docentes'), # type: ignore
    path('horas/',views.filter_data_horas,name='horas'), # type: ignore
    path('aborigen/',views_matric.filter_data_aborigen,name='aborigen'), # type: ignore
    path('comesp/',views_matric.filter_data_comesp,name='comesp'), # type: ignore
    path('snu/',views_matric.filter_data_snu,name='snu'), # type: ignore
    path('panel/', TemplateView.as_view(template_name='reportes/panel_reportes.html'),name='panel'),
    path('infografia/',TemplateView.as_view(template_name='reportes/panel_infografia.html'),name='infografia'),
    path('info1/',views_infograf.infografiaview,name='info1'),
    path('info2/',views_infograf.infografiaview2,name='info2')
]


