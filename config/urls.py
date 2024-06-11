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

urlpatterns = [
    path('admin/', admin.site.urls),
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
    path('cards/', TemplateView.as_view(template_name='presentacion.html'), name='cards'),
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico')),
    path('header/', TemplateView.as_view(template_name='layouts/header.html'), name='encabezado'),
    path('sidebar/', TemplateView.as_view(template_name='layouts/sidebar.html'), name='menu_lateral'),
    path('footer/', TemplateView.as_view(template_name='layouts/footer.html'), name='footer'),
    path('map/', include('apps.mapas.urls', namespace='map')),
    path('usua/', include('apps.usuarios.urls', namespace='usua')),
    path('error_conexion/', TemplateView.as_view(template_name='error_conexion.html'), name='error_conexion'),
    path('consulta_vacia/', TemplateView.as_view(template_name='consulta_vacia.html'), name='consulta_vacia'),
    path('repo/', include('apps.reportes.urls', namespace='repo')),    
    path('videoteca/', include('apps.videoteca.urls', namespace='videoteca')),   
    path('acceso/',include('apps.regacceso.urls', namespace='acceso')),
    path('operativo/',include('apps.lectocomp.urls',namespace='operativo')),
    path('indicador/',include('apps.indicadores.urls',namespace='indicador')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

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
