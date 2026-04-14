from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic.edit import FormView
from .models import GenerarInforme
from .forms import GenerarInformeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.consultasge.models_padron import CapaUnicaOfertas
from django.db.models import F, Func, Value, CharField
import re

class GenerarInformeView(LoginRequiredMixin, FormView):
    template_name = "biblioteca/generar_informe.html"
    form_class = GenerarInformeForm               
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario_logueado = self.request.user.username

        # Limpiar caracteres no numéricos del CUIT/CUIL
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        # Obtener primer cueanexo del usuario
        cueanexo_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)

        context['cueanexo_usuario'] = cueanexo_qs.first() if cueanexo_qs.exists() else ''
        return context
        
    def form_valid(self, form):
        # 🔹 Obtener usuario logueado correctamente
        usuario_logueado = self.request.user.username  
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)
        print("Usuario logueado:", usuario_logueado)  # Debug: Verificar el usuario logueado
        
        # 🔹 Obtener todos los cueanexos que cumplan la condición
        cueanexos_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)
        
        cueanexos = list(cueanexos_qs)  # Convertir a lista para manejarlo
        print("CUEANEXOS encontrados:", cueanexos_qs)  # Debug: Verificar los cueanexos obtenidos
        
        if not cueanexos:
            return JsonResponse({'success': False, 'message': "No se encontraron cueanexos para este usuario."})
        
        meses = form.cleaned_data['meses']
        annos = form.cleaned_data['annos']

        # 🔹 Comprobar si ya existe un informe para el mismo cueanexo, mes y año
        existentes = GenerarInforme.objects.filter(
            cueanexo__in=cueanexos,
            meses=meses,
            annos=annos
        )
        if existentes.exists():
            return JsonResponse({'success': False, 'message': "Ya existe un informe generado para este mes y año."})

        # 🔹 Guardar el informe para cada cueanexo
        for cue in cueanexos:
            informe = form.save(commit=False)
            informe.cueanexo = cue
            informe.estado = 'GENERADO'
            informe.save()

        # 🔹 Redirigir con datos
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
