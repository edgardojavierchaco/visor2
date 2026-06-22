from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.conf import settings
from apps.usuarios.models import EstadoUsuario
from typing import cast
from apps.usuarios.models import UsuariosVisualizador
from django.urls import resolve, reverse
from .models import DispositivoUsuario
from .utils_dispositivo import generar_fingerprint, get_client_ip
from .email_dispositivo import (
    enviar_email_dispositivo
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render
)

from .models_session import (
    SesionUsuario
)

from django.contrib.sessions.models import (
    Session
)

from django.contrib.auth import (
    authenticate,
    login,
    logout
)

from django.utils import timezone
from datetime import timedelta


class LoginFormView(LoginView):
    template_name = 'login/login.html'

    # --------------------------
    # 🎯 MAPA DE ROLES
    # --------------------------
    ROLE_REDIRECTS = {
        'Administrador': 'archivos:portada_gestor',
        'Gestor': 'archivos:portada_gestor',

        # Funcionarios
        'Ministro': 'archivos:portada_gestor',
        'Subsecretario': 'archivos:portada_gestor',
        'Director General': 'archivos:portada_gestor',
        'Director de Nivel': 'archivos:portada_gestor',

        # Otros
        'Director': 'directores:institucional',
        'Regional': 'archivos:portada_gestor',
        'Supervisor': 'archivos:portada_gestor',
        #'Renpe': 'archivos:portada_gestor_renpe',
        #'Evaluacion': 'oplectura:portada_eval',
        'Aplicador': 'directores:institucional',
        #'Director_Privada': 'directores:institucional',
        #'DirGral_Privada': 'privada:dashboard',
    }

    # --------------------------
    # 🧠 MAPA DE CATEGORÍAS
    # --------------------------
    CATEGORY_REDIRECTS = {
        'all': 'archivos:portada_gestor',
        'regional': 'archivos:portada_gestor',
        'propio': 'directores:institucional',
        'nivel': 'archivos:portada_gestor',
        'supervisor': 'archivos:portada_gestor',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar Sesión'
        return context

    # --------------------------
    # 🚀 RESOLVER REDIRECCIÓN
    # --------------------------
    def resolve_redirect_url(self, user):
        if not hasattr(user, 'perfil') or not user.perfil.rol:
            return settings.LOGIN_REDIRECT_URL

        rol = user.perfil.rol.nombre
        categoria = user.perfil.rol.categoria_acceso

        # 🎯 1. PRIORIDAD: ROL
        if rol in self.ROLE_REDIRECTS:
            url_name = self.ROLE_REDIRECTS[rol]

            # caso especial Aplicador (querystring)
            if rol == 'Aplicador':
                return reverse(url_name) + '?cueanexo=0&grado=TERCERO&seccion=A'

            return reverse(url_name)

        # 🧠 2. FALLBACK: CATEGORÍA
        if categoria in self.CATEGORY_REDIRECTS:
            return reverse(self.CATEGORY_REDIRECTS[categoria])

        return settings.LOGIN_REDIRECT_URL
    
    # =========================
    # 🔥 LOGIN SUCCESS
    # =========================
    def get_success_url(self):
        request = self.request
        user = request.user

        if not user.is_authenticated or not user.is_staff:
            return reverse('logueo:login')
        
        # =========================
        # 🔥 RESTAURAR ESTADO
        # =========================
        estado_obj = getattr(user, "estado", None)

        if estado_obj:
            estado = estado_obj.data or {}
            url = estado.get("url")

            if url:
                try:
                    resolve(url)  
                    request.session['estado_restaurar'] = estado
                    return url
                except:
                    pass  

        # 🎯 fallback normal
        return self.resolve_redirect_url(user)
    
    # =========================
    # 🔥 FORM VALID
    # =========================
    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )

        if user is not None:
            user=form.get_user()            
            
            # =====================
            # DETECCIÓN DISPOSITIVO
            # =====================

            fingerprint = generar_fingerprint(
                self.request
            )

            ip = get_client_ip(
                self.request
            )

            user_agent = self.request.META.get(
                'HTTP_USER_AGENT',
                ''
            )

            dispositivo = (
                DispositivoUsuario.objects.filter(
                    usuario=user,
                    fingerprint=fingerprint,
                    confirmado=True
                ).first()
            )

            # ---------------------
            # NUEVO DISPOSITIVO
            # ---------------------
            if not dispositivo:

                dispositivo = (
                    DispositivoUsuario.objects.filter(
                        usuario=user,
                        fingerprint=fingerprint,
                        confirmado=False
                    ).first()
                )
                
                if not dispositivo:
                
                    dispositivo = (
                        DispositivoUsuario.objects.create(
                            usuario=user,
                            fingerprint=fingerprint,
                            ip=ip,
                            user_agent=user_agent,
                            confirmado=False
                        )
                    )
                
                dispositivo.ip = ip
                dispositivo.user_agent = user_agent
                dispositivo.save()
                
                if not user.correo:

                    return JsonResponse({
                        'success': False,
                        'message': (
                            'Tu usuario no tiene'
                            'correo configurado. '
                        )
                    })
                
                hace_5_minutos = (
                    timezone.now() -
                    timedelta(minutes=5)
                )

                fecha_control = getattr(
                    dispositivo,
                    'fecha_envio_email',
                    None
                )
                
                if (
                    fecha_control and
                    fecha_control > hace_5_minutos
                ):

                    return JsonResponse({
                        'success': False,
                        'nuevo_dispositivo': True,
                        'message': (
                            'Ya se envió un coreo de '
                            'autorización recientemente. '
                            'Revisa tu bandeja de entrada.'
                        )
                    })
                    
                enviado = enviar_email_dispositivo(
                    self.request,
                    user,
                    dispositivo
                )

                if not enviado:

                    return JsonResponse({
                        'success': False,
                        'message': (
                            'Tu solicitud fue registrada. '
                            'El correo de autorización será '
                            'enviado automáticamente cuando '
                            'el servicio de correo vuelva '
                            'a estar disponible.'
                        )
                    })

                dispositivo.fecha_envio_email = (
                    timezone.now()
                )

                dispositivo.save(
                    update_fields=[
                        'fecha_envio_email'
                    ]
                )

                return JsonResponse({
                    'success': False,
                    'nuevo_dispositivo': True,
                    'message': (
                        'Detectamos un nuevo '
                        'dispositivo. '
                        'Revisá tu correo '
                        'para autorizarlo.'
                    )
                })

            # ---------------------
            # DISPOSITIVO CONOCIDO
            # ---------------------
            login(self.request, user)
            
            dispositivo.ip = ip
            dispositivo.user_agent = user_agent
            dispositivo.save()
            
            session_key = (
                self.request.session.session_key
            )

            SesionUsuario.objects.update_or_create(
                session_key=session_key,
                defaults={
                    'usuario': user,
                    'ip': ip,
                    'user_agent': user_agent,
                    'activa': True
                }
            )

            # ------------------
            # OTRAS SESIONES
            # ------------------

            otras_sesiones = (
                SesionUsuario.objects.filter(
                    usuario=user,
                    activa=True
                )
                .exclude(
                    session_key=session_key
                )
            )

            if user.is_staff:
                return JsonResponse({
                    'success': True,
                    'redirect_url': self.get_success_url(),
                    'otras_sesiones':
                        otras_sesiones.exists(),

                    'cantidad_sesiones':
                        otras_sesiones.count()
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Aún no estás autorizado.'
                })

        return JsonResponse({
            'success': False,
            'message': 'Credenciales incorrectas.'
        })
        
    # --------------------------
    # INVALID
    # --------------------------
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'message': 'Credenciales incorrectas.',
            'template': 'login/login.html'
        })

    # --------------------------
    # AJAX
    # --------------------------
    def post(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = self.get_form()
            return self.form_valid(form) if form.is_valid() else self.form_invalid(form)
        return super().post(request, *args, **kwargs)


# ==========================
# CONFIRMAR DISPOSITIVO
# ==========================
def confirmar_dispositivo(
    request,
    token
):

    dispositivo = (
        get_object_or_404(
            DispositivoUsuario,
            token=token
        )
    )

    if (
        not dispositivo
        .token_valido()
    ):

        return render(
            request,
            'login/token_expirado.html'
        )

    dispositivo.confirmado = True
    dispositivo.save()

    return render(
        request,
        'login/dispositivo_confirmado.html'
    )
    
    
# ==========================
# CERRAR OTRAS SESIONES
# ==========================
def cerrar_otras_sesiones(
    request
):

    if not request.user.is_authenticated:

        return JsonResponse({
            'success': False
        })

    actual = (
        request.session.session_key
    )

    sesiones = (
        SesionUsuario.objects.filter(
            usuario=request.user,
            activa=True
        )
        .exclude(
            session_key=actual
        )
    )

    for s in sesiones:

        Session.objects.filter(
            session_key=s.session_key
        ).delete()

        s.activa = False
        s.save()

    return JsonResponse({
        'success': True
    })


class CustomLogoutView(LogoutView):

    next_page = reverse_lazy(
        'dash:portada'
    )

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        # marcar sesión cerrada
        if request.session.session_key:

            SesionUsuario.objects.filter(
                session_key=
                    request.session.session_key
            ).update(
                activa=False
            )

        logout(request)

        return redirect(
            self.next_page
        )

    # permitir GET
    def get(
        self,
        request,
        *args,
        **kwargs
    ):
        return self.post(
            request,
            *args,
            **kwargs
        )
