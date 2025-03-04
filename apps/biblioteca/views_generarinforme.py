from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic.edit import FormView
from .models import GenerarInforme
from .forms import GenerarInformeForm
from django.contrib.auth.mixins import LoginRequiredMixin

class GenerarInformeView(LoginRequiredMixin, FormView):
    template_name = "biblioteca/generar_informe.html"
    form_class = GenerarInformeForm

    def form_valid(self, form):
        usuario = self.request.user.username
        meses = form.cleaned_data['meses']
        annos = form.cleaned_data['annos']

        # Comprobar si ya existe un informe para el mismo cueanexo, mes y año
        if GenerarInforme.objects.filter(cueanexo=usuario, meses=meses, annos=annos).exists():
            return JsonResponse({'success': False, 'message': "Ya existe un informe generado para este mes y año."})

        # Guardar el informe
        informe = form.save(commit=False)
        informe.cueanexo = usuario
        informe.estado = 'GENERADO'
        informe.save()

        # Redirigir con datos
        url = reverse("bibliotecas:materialbibliografico_create") 

        return JsonResponse({'success': True, 'message': "Informe generado exitosamente.", 'redirect_url': url})

    def form_invalid(self, form):
        return JsonResponse({'success': False, 'message': "Error al procesar el formulario."})



class CambiarEstadoView(View):
    """Cambia el estado de 'GENERADO' a 'ENVIADO' cuando se genera el PDF."""
    def get(self, request, informe_id):
        informe = get_object_or_404(GenerarInforme, id=informe_id)
        
        if informe.estado == "GENERADO":
            informe.estado = "ENVIADO"
            informe.save()
            return JsonResponse({"success": True, "message": "Estado cambiado a ENVIADO."})
        
        return JsonResponse({"success": False, "message": "El estado ya está en ENVIADO."})
