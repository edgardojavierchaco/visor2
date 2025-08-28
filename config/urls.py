from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.views import defaults as default_views
from apps.dashboard.views import directores
from apps.mapas.views2 import mapapuntos, obtenerdatos
from apps.establecimientos.views import establecimientos
from apps.evaluaciones.views import cargar_respuestas, ver_puntajes
from apps.unidadgestion import views_pers_doc_central
from apps.operativoschaco.views import guardar_examen, examen_guardado

urlpatterns = [
    path('admin/', admin.site.urls),
    path('al/',include('apps.alumnos.urls', namespace='al')),
    path('dash/', directores, name='dash'),
    path('director/',include('apps.directores.urls',namespace='director')),
    path('cargar/', include('apps.archivar.urls', namespace='cargar')),
    path('mapoteca/', include('apps.mapoteca.urls', namespace='mapoteca')),
    path('lex/', include('apps.normativa.urls', namespace='lex')),
    path('mapapuntos/', mapapuntos, name='mapapuntos'),
    path('dibujararea/', obtenerdatos, name='dibujararea'),
    path('login/', include('apps.login.urls', namespace='login')),
    path('portada/', include('apps.dashboard.urls', namespace='portada')),
    path('escuelas/', establecimientos, name='escuelas'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),    
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico')),    
    path('map/', include('apps.mapas.urls', namespace='map')),
    path('usua/', include('apps.usuarios.urls', namespace='usua')),
    path('error_conexion/', TemplateView.as_view(template_name='error_conexion.html'), name='error_conexion'),
    path('consulta_vacia/', TemplateView.as_view(template_name='consulta_vacia.html'), name='consulta_vacia'),
    path('repo/', include('apps.reportes.urls', namespace='repo')),    
    path('videoteca/', include('apps.videoteca.urls', namespace='videoteca')),   
    path('acceso/',include('apps.regacceso.urls', namespace='acceso')),
    path('lect/',include('apps.lectocomp.urls',namespace='lect')),
    path('indicador/',include('apps.indicadores.urls',namespace='indicador')),
    path('doc/',include('apps.asistendoc.urls',namespace='doc')),   
    path('censo/',include('apps.cenpe.urls',namespace='censo')) ,
    path('operativo/',include('apps.oplectura.urls', namespace='operativo')),
    path('super/',include('apps.supervisores.urls', namespace='super')), 
    path('sup/',include('apps.superescuela.urls', namespace='sup')),    
    path('contador/',include('apps.cuenta_regresiva.urls',namespace='contador')),
    path('organica/',include('apps.pof.urls',namespace='organica')),
    path('select2/', include('django_select2.urls')),       
    path('evaluacion/<int:alumno_id>/<int:evaluacion_id>/', cargar_respuestas, name='cargar_respuestas'),
    path('puntajes/<int:alumno_id>/', ver_puntajes, name='ver_puntajes'),
    path('evaluaciones/',include('apps.evaluaciones.urls',namespace='evaluaciones')),
    path('central/',include('apps.unidadgestion.urls',namespace='central')),
    path('uegp/',include('apps.uegp.urls',namespace='uegp')),
    path('chaco/',include('apps.funcionarios.urls',namespace='chaco')),
    path('rl/',include('apps.represlegales.urls',namespace='rl')),
    path('indigena/',include('apps.intercultural.urls',namespace='indigena')),
    path('bbl/',include('apps.biblioteca.urls',namespace='bbl')),
    path('indic/',include('apps.indicadoresie.urls',namespace='indic')),
    path('infra/',include('apps.infraestructura.urls',namespace='infra')), 
    path('pregunta/',include('apps.operativoschaco.urls',namespace='pregunta')), 
    path('examendiag/',include('apps.operativchaco.urls',namespace='examendiag')),
    path('consultas/', include('apps.consultas.urls', namespace='consultas_api')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),    

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path('400/', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        path('403/', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        path('404/', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        path('500/', default_views.server_error),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
