import re
import traceback
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView
from django.views import View
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Func, Value

from .models import GenerarInforme
from .forms import GenerarInformeForm
from apps.consultasge.models_padron import CapaUnicaOfertas


# =========================
# UTIL
# =========================
def get_cueanexos_usuario(user):
    usuario_limpio = re.sub(r'\D', '', user.username)

    return list(
        CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo__startswith='BI'
        ).values_list('cueanexo', flat=True)
    )


# =========================
# FORM VIEW
# =========================
class GenerarInformeView(LoginRequiredMixin, FormView):
    template_name = "biblioteca/generar_informe.html"
    form_class = GenerarInformeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cueanexos_usuario'] = get_cueanexos_usuario(self.request.user)
        return context

    def form_valid(self, form):
        try:
            cueanexos_usuario = [str(c) for c in get_cueanexos_usuario(self.request.user)]
            cueanexo = str(self.request.POST.get("cueanexo"))

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
            # 🔒 REGLA DE NO PENDIENTE
            # =========================
            if len(cueanexos_usuario) > 1:
                tiene_pendiente = GenerarInforme.objects.filter(
                    cueanexo__in=cueanexos_usuario,
                    estado="GENERADO"
                ).exists()

                if tiene_pendiente:
                    return JsonResponse({
                        "success": False,
                        "message": "Ya tenés un informe generado pendiente de envío. Debés enviarlo antes de crear otro."
                    })

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
            # GUARDAR
            # =========================
            obj = form.save(commit=False)
            obj.cueanexo = cueanexo
            obj.estado = "GENERADO"
            obj.save()
            
            self.request.session["cueanexo_activo"] = cueanexo

            return JsonResponse({
                "success": True,
                "message": "Informe generado correctamente",
                "redirect_url": reverse("bibliotecas:materialbibliografico_create")
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
        cueanexos_usuario = [str(c) for c in get_cueanexos_usuario(request.user)]

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