from django.urls import reverse, reverse_lazy, resolve
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta

from .models import DispositivoUsuario
from .utils_dispositivo import (
    generar_fingerprint,
    get_client_ip,
    obtener_geolocalizacion,
)
from .email_dispositivo import (
    enviar_email_dispositivo
)

from .models_session import (
    SesionUsuario
)

from django.contrib.sessions.models import (
    Session
)


# ============================================================
# LOGIN
# ============================================================

class LoginFormView(LoginView):

    template_name = 'login/login.html'

    # ========================================================
    # MAPA DE ROLES
    # ========================================================

    ROLE_REDIRECTS = {

        # Gestores
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
        'Aplicador': 'directores:institucional',
        'Infraestructura': 'archivos:portada_gestor',
        'Pof': 'archivos:portada_gestor',
    }

    # ========================================================
    # MAPA DE CATEGORÍAS
    # ========================================================

    CATEGORY_REDIRECTS = {

        'all': 'archivos:portada_gestor',
        'regional': 'archivos:portada_gestor',
        'propio': 'directores:institucional',
        'nivel': 'archivos:portada_gestor',
        'supervisor': 'archivos:portada_gestor',

    }

    # ========================================================
    # CONTEXTO
    # ========================================================

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['title'] = 'Iniciar Sesión'

        return context

    # ========================================================
    # RESOLVER REDIRECCIÓN
    # ========================================================

    def resolve_redirect_url(self, user):

        # ----------------------------------------------------
        # Verificar perfil
        # ----------------------------------------------------

        perfil = getattr(
            user,
            'perfil',
            None
        )

        if not perfil:

            return settings.LOGIN_REDIRECT_URL

        # ----------------------------------------------------
        # Verificar rol
        # ----------------------------------------------------

        rol_obj = getattr(
            perfil,
            'rol',
            None
        )

        if not rol_obj:

            return settings.LOGIN_REDIRECT_URL

        rol = getattr(
            rol_obj,
            'nombre',
            None
        )

        categoria = getattr(
            rol_obj,
            'categoria_acceso',
            None
        )

        # ====================================================
        # 1. PRIORIDAD: ROL
        # ====================================================

        if rol in self.ROLE_REDIRECTS:

            url_name = self.ROLE_REDIRECTS[rol]

            return reverse(url_name)

        # ====================================================
        # 2. FALLBACK: CATEGORÍA
        # ====================================================

        if categoria in self.CATEGORY_REDIRECTS:

            return reverse(
                self.CATEGORY_REDIRECTS[categoria]
            )

        # ====================================================
        # 3. FALLBACK FINAL
        # ====================================================

        return settings.LOGIN_REDIRECT_URL

    # ========================================================
    # LOGIN SUCCESS
    # ========================================================

    def get_success_url(self):

        request = self.request
        user = request.user

        # ----------------------------------------------------
        # Verificación de seguridad
        # ----------------------------------------------------

        if (
            not user.is_authenticated
            or not user.is_staff
        ):

            return reverse(
                'logueo:login'
            )

        # ====================================================
        # RESTAURAR ESTADO
        # ====================================================

        estado_obj = getattr(
            user,
            "estado",
            None
        )

        if estado_obj:

            estado = estado_obj.data or {}

            url = estado.get(
                "url"
            )

            if url:

                try:

                    # ----------------------------------------
                    # Verificar que sea una URL Django válida
                    # ----------------------------------------

                    resolve(url)

                    request.session[
                        'estado_restaurar'
                    ] = estado

                    return url

                except Exception:

                    pass

        # ====================================================
        # REDIRECCIÓN NORMAL
        # ====================================================

        return self.resolve_redirect_url(
            user
        )

    # ========================================================
    # FORM VALID
    # ========================================================

    def form_valid(self, form):

        # ====================================================
        # 1. AUTENTICAR CREDENCIALES
        # ====================================================

        user = authenticate(
            request=self.request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )

        if not user:

            return JsonResponse(
                {
                    'success': False,
                    'message': 'Credenciales incorrectas.'
                },
                status=401
            )

        # ====================================================
        # 2. OBTENER DATOS DEL DISPOSITIVO
        # ====================================================

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

        # ====================================================
        # 3. GEOLOCALIZACIÓN
        # ====================================================

        geo = obtener_geolocalizacion(
            ip
        ) or {}

        ubicacion = {

            "pais": geo.get(
                "pais",
                "Desconocido"
            ),

            "provincia": geo.get(
                "provincia",
                "Desconocido"
            ),

            "ciudad": geo.get(
                "ciudad",
                "Desconocido"
            ),

            "lat": float(
                geo.get("lat")
                or -27.451
            ),

            "lon": float(
                geo.get("lon")
                or -58.986
            ),
        }

        # ====================================================
        # 4. BUSCAR DISPOSITIVO
        # ====================================================

        dispositivo = (
            DispositivoUsuario.objects
            .filter(
                usuario=user,
                fingerprint=fingerprint
            )
            .first()
        )

        # ====================================================
        # 5. CREAR DISPOSITIVO SI NO EXISTE
        # ====================================================

        if not dispositivo:

            dispositivo = (
                DispositivoUsuario.objects.create(

                    usuario=user,

                    fingerprint=fingerprint,

                    ip=ip,

                    ubicacion=ubicacion,

                    user_agent=user_agent,

                    confirmado=False
                )
            )

        else:

            # ------------------------------------------------
            # Actualizar datos del dispositivo
            # ------------------------------------------------

            dispositivo.ip = ip

            dispositivo.ubicacion = ubicacion

            dispositivo.user_agent = user_agent

            dispositivo.save(
                update_fields=[
                    'ip',
                    'ubicacion',
                    'user_agent'
                ]
            )

        # ====================================================
        # 6. 🔴 DISPOSITIVO NO CONFIRMADO
        #
        # MUY IMPORTANTE:
        #
        # ACÁ NO SE EJECUTA login()
        # ====================================================

        if not dispositivo.confirmado:

            # ------------------------------------------------
            # Verificar correo
            # ------------------------------------------------

            if not user.correo:

                # --------------------------------------------
                # Por seguridad, si existiera una sesión,
                # cerrarla.
                # --------------------------------------------

                if self.request.user.is_authenticated:

                    SesionUsuario.objects.filter(
                        session_key=self.request.session.session_key
                    ).update(
                        activa=False
                    )

                    logout(
                        self.request
                    )

                return JsonResponse(
                    {
                        'success': False,
                        'nuevo_dispositivo': True,
                        'requiere_confirmacion': True,
                        'message': (
                            'El usuario no tiene un correo '
                            'electrónico configurado.'
                        )
                    },
                    status=403
                )

            # ------------------------------------------------
            # Verificar último envío
            # ------------------------------------------------

            hace_5_min = (
                timezone.now()
                - timedelta(
                    minutes=5
                )
            )

            if (
                dispositivo.fecha_envio_email
                and dispositivo.fecha_envio_email > hace_5_min
            ):

                # --------------------------------------------
                # IMPORTANTE:
                # NO llamar login()
                # --------------------------------------------

                return JsonResponse(
                    {
                        'success': False,
                        'nuevo_dispositivo': True,
                        'requiere_confirmacion': True,
                        'message': (
                            'Ya se envió un correo de '
                            'validación recientemente. '
                            'Revisá tu correo.'
                        )
                    },
                    status=403
                )

            # =================================================
            # ENVIAR CORREO
            # =================================================

            enviar_email_dispositivo(
                self.request,
                user,
                dispositivo
            )

            # ------------------------------------------------
            # Registrar fecha de envío
            # ------------------------------------------------

            dispositivo.fecha_envio_email = (
                timezone.now()
            )

            dispositivo.save(
                update_fields=[
                    'fecha_envio_email'
                ]
            )

            # =================================================
            # 🔴 GARANTÍA DE SEGURIDAD
            #
            # Si por alguna razón ya existiera una sesión
            # autenticada, cerrarla.
            # =================================================

            if self.request.user.is_authenticated:

                session_key = (
                    self.request.session.session_key
                )

                if session_key:

                    SesionUsuario.objects.filter(
                        session_key=session_key
                    ).update(
                        activa=False
                    )

                logout(
                    self.request
                )

            # =================================================
            # 🚫 NO HACER LOGIN
            # =================================================

            return JsonResponse(
                {
                    'success': False,
                    'nuevo_dispositivo': True,
                    'requiere_confirmacion': True,
                    'message': (
                        'Dispositivo no autorizado. '
                        'Revisá tu correo para confirmar '
                        'este dispositivo.'
                    )
                },
                status=403
            )

        # ====================================================
        # 7. 🟢 DISPOSITIVO CONFIRMADO
        #
        # RECIÉN ACÁ SE AUTENTICA LA SESIÓN
        # ====================================================

        login(
            self.request,
            user
        )

        # ====================================================
        # 8. OBTENER SESSION KEY
        # ====================================================

        session_key = (
            self.request.session.session_key
        )

        # ====================================================
        # 9. REGISTRAR SESIÓN
        # ====================================================

        SesionUsuario.objects.update_or_create(

            session_key=session_key,

            defaults={

                "usuario": user,

                "ip": ip,

                "ubicacion": ubicacion,

                "user_agent": user_agent,

                "activa": True
            }
        )

        # ====================================================
        # 10. BUSCAR OTRAS SESIONES
        # ====================================================

        otras = (
            SesionUsuario.objects
            .filter(
                usuario=user,
                activa=True
            )
            .exclude(
                session_key=session_key
            )
        )

        # ====================================================
        # 11. LOGIN CORRECTO
        # ====================================================

        return JsonResponse(
            {
                "success": True,

                "redirect_url": (
                    self.get_success_url()
                ),

                "otras_sesiones": (
                    otras.exists()
                ),

                "cantidad_sesiones": (
                    otras.count()
                )
            }
        )

    # ========================================================
    # FORM INVALID
    # ========================================================

    def form_invalid(self, form):

        return JsonResponse(
            {
                'success': False,
                'message': 'Credenciales incorrectas.'
            },
            status=401
        )

    # ========================================================
    # POST AJAX
    # ========================================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        if (
            request.headers.get(
                'x-requested-with'
            )
            == 'XMLHttpRequest'
        ):

            form = self.get_form()

            if form.is_valid():

                return self.form_valid(
                    form
                )

            return self.form_invalid(
                form
            )

        return super().post(
            request,
            *args,
            **kwargs
        )


# ============================================================
# CONFIRMAR DISPOSITIVO
# ============================================================

def confirmar_dispositivo(
    request,
    token
):

    # ========================================================
    # BUSCAR DISPOSITIVO
    # ========================================================

    dispositivo = get_object_or_404(
        DispositivoUsuario,
        token=token
    )

    # ========================================================
    # VALIDAR TOKEN
    # ========================================================

    if not dispositivo.token_valido():

        return render(
            request,
            'login/token_expirado.html'
        )

    # ========================================================
    # CONFIRMAR DISPOSITIVO
    # ========================================================

    dispositivo.confirmado = True

    dispositivo.save(
        update_fields=[
            'confirmado'
        ]
    )

    # ========================================================
    # MOSTRAR CONFIRMACIÓN
    # ========================================================

    return render(
        request,
        'login/dispositivo_confirmado.html'
    )


# ============================================================
# CERRAR OTRAS SESIONES
# ============================================================

def cerrar_otras_sesiones(
    request
):

    # ========================================================
    # VERIFICAR AUTENTICACIÓN
    # ========================================================

    if not request.user.is_authenticated:

        return JsonResponse(
            {
                'success': False,
                'message': 'Usuario no autenticado.'
            },
            status=401
        )

    # ========================================================
    # SESIÓN ACTUAL
    # ========================================================

    actual = (
        request.session.session_key
    )

    # ========================================================
    # OTRAS SESIONES
    # ========================================================

    sesiones = (
        SesionUsuario.objects
        .filter(
            usuario=request.user,
            activa=True
        )
        .exclude(
            session_key=actual
        )
    )

    # ========================================================
    # ELIMINAR SESIONES
    # ========================================================

    for sesion in sesiones:

        Session.objects.filter(
            session_key=sesion.session_key
        ).delete()

        sesion.activa = False

        sesion.save(
            update_fields=[
                'activa'
            ]
        )

    # ========================================================
    # RESPUESTA
    # ========================================================

    return JsonResponse(
        {
            'success': True
        }
    )


# ============================================================
# LOGOUT
# ============================================================

class CustomLogoutView(
    LogoutView
):

    next_page = reverse_lazy(
        'dash:portada'
    )

    # ========================================================
    # POST
    # ========================================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        # ====================================================
        # MARCAR SESIÓN COMO INACTIVA
        # ====================================================

        if request.session.session_key:

            SesionUsuario.objects.filter(

                session_key=(
                    request.session.session_key
                )

            ).update(
                activa=False
            )

        # ====================================================
        # CERRAR SESIÓN DJANGO
        # ====================================================

        logout(
            request
        )

        # ====================================================
        # REDIRECCIONAR
        # ====================================================

        return redirect(
            self.next_page
        )

    # ========================================================
    # PERMITIR GET
    # ========================================================

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
