from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views import defaults as default_views
from apps import establecimientos
from apps.dashboard.views import dash
from apps.mapas.views2 import *
from apps.establecimientos.views import establecimientos
#from apps.chat.views import homeChat, roomChat, private_chat
from apps.archivar.views import ArchivoCreateView, ArchivosListView, BuscarPDFView
from apps.mapoteca.views import ver_mapas
from apps.normativa.views import ver_normas

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dash/',dash,name='dash'),   
    path('cargar/', include('apps.archivar.urls', namespace='cargar')),        
    path('mapoteca/',include('apps.mapoteca.urls',namespace='mapoteca')),
    path('lex/',include('apps.normativa.urls',namespace='lex')),
    #path('roomp/<int:room_id>/private_chat/',private_chat, name='private_chat'),
    path('mapapuntos/',mapapuntos,name='mapapuntos'),
    path('dibujararea/',obtenerdatos,name='dibujararea'),
    path('login/',include('apps.login.urls',namespace='login')),
    path('portada/',include('apps.dashboard.urls',namespace='portada')),
    path('escuelas/',establecimientos,name='escuelas'),
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
    path('equipo/',TemplateView.as_view(template_name='equipo.html'),name='equipo'),
    path('videoteca/',include('apps.videoteca.urls',namespace='videoteca')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


if settings.DEBUG:
    # Agregar rutas de error y depuración solo en modo DEBUG
    urlpatterns += [
        path('400/', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        path('403/', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        path('404/', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        path('500/', default_views.server_error),
    ]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Agregar rutas de debug_toolbar si está instalado
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

