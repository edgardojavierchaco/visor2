from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views import defaults as default_views
from apps.usuarios.views import usuarios_list
from apps.login.views import LoginFormView
from apps.dashboard.views import DashboardView
from apps.confidencial.views_supervisor import *


urlpatterns = [
    path('admin/', admin.site.urls),    
    path('', TemplateView.as_view(template_name='home.html'), name='home'),    
    path('cards/', TemplateView.as_view(template_name='presentacion.html'), name='cards'),  
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico')),    
    path('header/', TemplateView.as_view(template_name='layouts/header.html'), name='encabezado'),
    path('sidebar/', TemplateView.as_view(template_name='layouts/sidebar.html'), name='menu_lateral'),
    path('footer/', TemplateView.as_view(template_name='layouts/footer.html'), name='footer'),
    path('map/', include('apps.mapas.urls', namespace='map')),
    path('usuarios/',include('apps.usuarios.urls', namespace='usuarios')),    
    path('login/', include('apps.login.urls',namespace='acceso')),
    path('error_conexion/', TemplateView.as_view(template_name='error_conexion.html'), name='error_conexion'),
    path('consulta_vacia/', TemplateView.as_view(template_name='consulta_vacia.html'), name='consulta_vacia'),
    path('repo/', include('apps.reportes.urls', namespace='repo')),       
    path('equipo/',TemplateView.as_view(template_name='equipo.html'),name='equipo'),
    path('videoteca/',include('apps.videoteca.urls',namespace='videoteca')),
    path('dashboard/',DashboardView.as_view() ,name='dashboard'),
    path('confi/',include('apps.confidencial.urls',namespace='confidencial')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


if settings.DEBUG:
    # Agregar rutas de error y depuración solo en modo DEBUG
    urlpatterns += [
        path('400/', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        path('403/', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        path('404/', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        path('500/', default_views.server_error),
    ]
    
    # Agregar rutas de debug_toolbar si está instalado
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

