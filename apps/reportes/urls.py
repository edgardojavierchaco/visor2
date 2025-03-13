#from django.urls import path
from config.urls import path
from django.views.generic import TemplateView
from . import views
from . import views_matric, views_infograf, views_listados, views_carrerastitulos, views_infodocatividad
from .views_matric_cueanexo import filtrado_matriccueanexo, filter_data_matric_cueanexo
from .views_matric_disc_cueanexo import filtrado_matric_disc_ini_cueanexo, filter_data_matric_disc_ini_cueanexo
from .views_matric_disc_prim_cueanexo import filter_data_matric_disc_prim_cueanexo, filtrado_matric_disc_prim_cueanexo
from .views_matric_disc_sec_cueanexo import filter_data_matric_disc_sec_cueanexo, filtrado_matric_disc_sec_cueanexo
from apps.reportes import views_matric_cueanexo
from .views_tabla import tabla_view, get_table_data, obtener_columnas_cargos

app_name='reportes'

urlpatterns=[
    path('filtrado_cargos/',views.filtrado_cargos,name='filtrado_cargos'),
    path('filtrado_docentes/',views.filtrado_docentes,name='filtrado_docentes'),
    path('filtrado_docentes_pasiva/',views.filtrado_docentes_pasiva,name='filtrado_docentes_pasiva'),
    path('filtrado_horas/',views.filtrado_horas,name='filtrado_horas'),
    path('filtrado_aborigen/',views_matric.filtrado_aborigen,name='filtrado_aborigen'),
    path('filtrado_comesp/',views_matric.filtrado_comesp,name='filtrado_comesp'),
    path('filtrado_snu/',views_matric.filtrado_snu,name='filtrado_snu'),
    path('filtrado_matricueanexo/',filtrado_matriccueanexo,name='filtrado_matricueanexo'),
    path('filtrado_matri_disc_ini_cueanexo/',filtrado_matric_disc_ini_cueanexo,name='filtrado_matri_disc_ini_cueanexo'),
    path('filtrado_matri_disc_prim_cueanexo/',filtrado_matric_disc_prim_cueanexo,name='filtrado_matri_disc_prim_cueanexo'),
    path('filtrado_matri_disc_sec_cueanexo/',filtrado_matric_disc_sec_cueanexo,name='filtrado_matri_disc_sec_cueanexo'),
    path('cargos/',views.filter_data_cargos,name='cargos'), # type: ignore
    path('docentes/',views.filter_data_docentes,name='docentes'), # type: ignore
    path('docentes_pasiva/',views.filter_data_docentes_pasiva,name='docentes_pasiva'), # type: ignore
    path('horas/',views.filter_data_horas,name='horas'), # type: ignore
    path('aborigen/',views_matric.filter_data_aborigen,name='aborigen'), # type: ignore
    path('comesp/',views_matric.filter_data_comesp,name='comesp'), # type: ignore
    path('snu/',views_matric.filter_data_snu,name='snu'), # type: ignore
    path('panel/', TemplateView.as_view(template_name='reportes/panel_reportes.html'),name='panel'),
    path('infografia/',TemplateView.as_view(template_name='reportes/panel_infografia.html'),name='infografia'),
    path('info1/',views_infograf.infografiaview,name='info1'),
    path('info2/',views_infograf.infografiaview2,name='info2'),
    path('consulta_ofertas/',views_listados.consulta_ofertas,name='consulta_ofertas'),   
    path('consulta_ofertas_reg/',views_listados.consulta_ofertas_reg,name='consulta_ofertas_reg'), 
    path('consulta_titulos/', views_carrerastitulos.consulta_carrerastitulos, name='consulta_titulos'),
    path('equipo/', views_infograf.equipoview,name='equipo'),
    path('datoscarreras/',views_carrerastitulos.datoscarreras,name='datoscarreras'),
    path('docactividad/',views_infodocatividad.consulta_docentes_actividad, name='docactividad'),
    path('matric_cueanexo/',filter_data_matric_cueanexo,name='matric_cueanexo'), # type: ignore
    path('matric_disc_ini_cueanexo/',filter_data_matric_disc_ini_cueanexo, name='matric_disc_ini_cueanexo'), # type: ignore
    path('matric_disc_prim_cueanexo/',filter_data_matric_disc_prim_cueanexo, name='matric_disc_prim_cueanexo'), # type: ignore
    path('matric_disc_sec_cueanexo/',filter_data_matric_disc_sec_cueanexo, name='matric_disc_sec_cueanexo'), # type: ignore
    path('tabla/', tabla_view, name='tabla'),
    path('get_data/', get_table_data, name='get_data'),
    path('obtener_cargos/', obtener_columnas_cargos, name='obtener_columnas_cargos'),
]


