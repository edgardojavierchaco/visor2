from django.http import JsonResponse
from django.views import View
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.usuarios.models import UsuariosVisualizador, PasswordChangeLog

import random

MAX_INTENTOS = 5
BLOQUEO_MINUTOS = 10


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


# ===============================
# 🔐 ENVIAR CÓDIGO
# ===============================
class ResetPasswordCUILView(View):

    def post(self, request):
        if request.headers.get('x-requested-with') != 'XMLHttpRequest':
            return JsonResponse({'success': False})

        cuil = request.POST.get('cuil')
        ip = get_client_ip(request)

        usuario = UsuariosVisualizador.objects.filter(username=cuil).first()

        if usuario and usuario.correo:
            codigo = str(random.randint(100000, 999999))

            cache.set(f"reset_{cuil}", codigo, timeout=300)
            cache.set(f"user_{cuil}", usuario.pk, timeout=300)

            send_mail(
                'Código de recuperación',
                f'Tu código es: {codigo}',
                settings.EMAIL_HOST_USER,
                [usuario.correo],
                fail_silently=False,
            )

        return JsonResponse({
            'success': True,
            'message': 'Si el usuario existe, se envió un código.'
        })


# ===============================
# 🔐 CONFIRMAR RESET
# ===============================
class ConfirmResetCUILView(View):

    def post(self, request):
        if request.headers.get('x-requested-with') != 'XMLHttpRequest':
            return JsonResponse({'success': False})

        cuil = request.POST.get('cuil')
        codigo = request.POST.get('codigo')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')  # 🔥 CLAVE

        ip = get_client_ip(request)

        # 🔥 VALIDACIÓN
        if not password or not password2:
            return JsonResponse({
                'success': False,
                'message': 'Completá todos los campos'
            })

        if password != password2:
            return JsonResponse({
                'success': False,
                'message': 'Las contraseñas no coinciden'
            })

        codigo_guardado = cache.get(f"reset_{cuil}")

        if codigo_guardado != codigo:
            return JsonResponse({
                'success': False,
                'message': 'Código inválido'
            })

        user_id = cache.get(f"user_{cuil}")

        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'Sesión expirada'
            })

        usuario = UsuariosVisualizador.objects.get(pk=user_id)

        try:
            validate_password(password, usuario)
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': " ".join(e.messages)
            })

        # 🔐 ENCRIPTADO
        usuario.set_password(password)
        usuario.save()

        # limpieza
        cache.delete(f"reset_{cuil}")
        cache.delete(f"user_{cuil}")

        # auditoría (opcional)
        try:
            PasswordChangeLog.objects.create(
                usuario=usuario,
                ip=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                tipo='reset'
            )
        except:
            pass

        return JsonResponse({
            'success': True,
            'message': 'Contraseña actualizada correctamente'
        })
