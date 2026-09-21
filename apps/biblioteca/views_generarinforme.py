import traceback
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView
from django.views import View
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import GenerarInforme
from .forms import GenerarInformeForm
from .mixins import get_cueanexos_usuario


def _estado_cueanexos_usuario(user):
    cueanexos_autorizados = list(dict.fromkeys(
        str(cueanexo) for cueanexo in get_cueanexos_usuario(user)
    ))
    cueanexos_ocupados = {
        str(cueanexo)
        for cueanexo in GenerarInforme.objects.filter(
            cueanexo__in=cueanexos_autorizados,
            estado="GENERADO",
        ).values_list('cueanexo', flat=True)
    }
    cueanexos_con_generado = [
        cueanexo
        for cueanexo in cueanexos_autorizados
        if cueanexo in cueanexos_ocupados
    ]
    cueanexos_disponibles = [
        cueanexo
        for cueanexo in cueanexos_autorizados
        if cueanexo not in cueanexos_ocupados
    ]
    return (
        cueanexos_autorizados,
        cueanexos_con_generado,
        cueanexos_disponibles,
    )


# =========================
# FORM VIEW
# =========================
class GenerarInformeView(LoginRequiredMixin, FormView):
    template_name = "biblioteca/generar_informe.html"
    form_class = GenerarInformeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Biblioteca | Nuevo período'
        (
            cueanexos_usuario,
            cueanexos_con_generado,
            cueanexos_disponibles,
        ) = _estado_cueanexos_usuario(self.request.user)
        context.update({
            'cueanexos_usuario': cueanexos_usuario,
            'cueanexos_con_generado': cueanexos_con_generado,
            'cueanexos_disponibles': cueanexos_disponibles,
            'cueanexo_unico': (
                cueanexos_usuario[0] if len(cueanexos_usuario) == 1 else None
            ),
            'sin_cueanexos_disponibles': not cueanexos_disponibles,
        })
        return context

    def form_valid(self, form):
        try:
            (
                cueanexos_usuario,
                cueanexos_con_generado,
                _cueanexos_disponibles,
            ) = _estado_cueanexos_usuario(self.request.user)

            if not cueanexos_usuario:
                return JsonResponse({
                    "success": False,
                    "message": "No tenés CUE-Anexos autorizados para crear un período.",
                })

            if len(cueanexos_usuario) == 1:
                cueanexo = cueanexos_usuario[0]
            else:
                cueanexo_post = self.request.POST.get("cueanexo")
                cueanexo = str(cueanexo_post).strip() if cueanexo_post else ""

            meses = form.cleaned_data['meses']
            annos = form.cleaned_data['annos']

            # =========================
            # VALIDACIONES BÁSICAS
            # =========================
            if not cueanexo:
                return JsonResponse({"success": False, "message": "Seleccione un cueanexo"})

            if cueanexo not in cueanexos_usuario:
                return JsonResponse({"success": False, "message": "Cueanexo inválido"})

            # =========================
            # VALIDAR DUPLICADO
            # =========================
            existe = GenerarInforme.objects.filter(
                cueanexo=cueanexo,
                meses=meses,
                annos=annos
            ).exists()

            if existe:
                return JsonResponse({"success": False, "message": "Ya existe informe para ese período"})

            # =========================
            # VALIDAR PENDIENTE DEL CUE
            # =========================
            if cueanexo in cueanexos_con_generado:
                return JsonResponse({
                    "success": False,
                    "message": "Ese CUE-Anexo ya tiene un período pendiente de envío. Debés enviarlo antes de crear otro.",
                })

            # =========================
            # GUARDAR
            # =========================
            obj = form.save(commit=False)
            obj.cueanexo = cueanexo
            obj.estado = "GENERADO"
            obj.save()
            
            self.request.session["cueanexo_activo"] = cueanexo
            self.request.session["biblioteca_periodo_activo_id"] = obj.pk

            return JsonResponse({
                "success": True,
                "message": "Informe generado correctamente",
                "redirect_url": (
                    f'{reverse("bibliotecas:materialbibliografico_create")}'
                    f'?periodo={obj.pk}'
                ),
            })

        except Exception as e:
            print(traceback.format_exc())
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    def form_invalid(self, form):
        return JsonResponse({
            "success": False,
            "message": "Formulario inválido",
            "errors": form.errors
        })


# =========================
# AJAX DUPLICADO
# =========================
class VerificarInformeAjax(View):

    def get(self, request):
        cueanexos_usuario = list(dict.fromkeys(
            str(cueanexo) for cueanexo in get_cueanexos_usuario(request.user)
        ))

        cueanexo = str(request.GET.get('cueanexo'))
        meses = request.GET.get('meses')
        annos = request.GET.get('annos')

        if cueanexo not in cueanexos_usuario:
            return JsonResponse({
                "existe": False,
                "error": True,
                "message": "Cueanexo inválido"
            })

        existe = GenerarInforme.objects.filter(
            cueanexo=cueanexo,
            meses=meses,
            annos=annos
        ).exists()

        return JsonResponse({"existe": existe})


# =========================
# CAMBIO DE ESTADO
# =========================
class CambiarEstadoView(View):

    def get(self, request, informe_id):
        informe = get_object_or_404(GenerarInforme, id=informe_id)

        if informe.estado == "GENERADO":
            informe.estado = "ENVIADO"
            informe.save()
            return JsonResponse({"success": True})

        return JsonResponse({"success": False})
