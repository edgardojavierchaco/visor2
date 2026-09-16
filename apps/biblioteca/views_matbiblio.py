from django.forms import ValidationError
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import MaterialBibliografico
from .forms import MaterialBibliograficoForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from typing import Any, Optional
from .mixins import InformeBloqueoMixin

# =========================
# 🔹 CUEANEXOS DEL USUARIO
# =========================
class MaterialBibliograficoCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = MaterialBibliografico
    form_class = MaterialBibliograficoForm
    template_name = 'biblioteca/pem/matbibl/create.html'
    success_url = reverse_lazy('bibliotecas:materialbibliografico_list')    
    
    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        try:
            action = request.POST.get('action')

            if action == 'add':
                form = self.get_form()

                if form.is_valid():
                    instance = form.save(commit=False)
                    self.aplicar_periodo_activo(instance)
                    instance.save()
                    form.save_m2m()
                    return JsonResponse(instance.toJSON())
                else:
                    return JsonResponse({
                        'error': True,
                        'errors': form.errors
                    })

            return JsonResponse({'error': 'Acción no válida'})

        except Exception as e:
            return JsonResponse({'error': str(e)})

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)





        context['title'] = 'Carga Servicio Material Bibliográfico'
        context['entity'] = 'Material'
        context['list_url'] = self.success_url
        context['action'] = 'add'

        return context    


#editar
class MaterialBibliograficoUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = MaterialBibliografico
    form_class = MaterialBibliograficoForm
    template_name = 'biblioteca/pem/matbibl/create.html'
    success_url = reverse_lazy('bibliotecas:materialbibliografico_list')
    
     # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        try:
            action = request.POST.get('action')

            if action == 'edit':
                form = self.get_form()

                if form.is_valid():
                    instance = form.save(commit=False)
                    self.aplicar_periodo_activo(instance)
                    instance.save()
                    form.save_m2m()
                    return JsonResponse(instance.toJSON())
                else:
                    return JsonResponse({
                        "error": True,
                        "errors": form.errors
                    })

            return JsonResponse({
                "error": True,
                "message": "Acción no válida"
            })

        except Exception as e:
            return JsonResponse({
                "error": True,
                "message": str(e)
            })

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)





        context['title'] = 'Edición Servicio Material Bibliográfico'
        context['entity'] = 'Material'
        context['list_url'] = self.success_url
        context['action'] = 'edit'

        return context


#Eliminar
class MaterialBibliograficoDeleteView(LoginRequiredMixin, InformeBloqueoMixin, DeleteView):
    model = MaterialBibliografico
    template_name = 'biblioteca/pem/matbibl/delete.html'
    success_url = reverse_lazy('bibliotecas:materialbibliografico_list')

    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        # 🚨 BLOQUEO POR INFORME ENVIADO
        try:
            self.object.delete()

            return JsonResponse({
                "success": True,
                "message": "Registro eliminado correctamente"
            })

        except Exception as e:
            return JsonResponse({
                "error": True,
                "message": str(e)
            })

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['title'] = 'Eliminación Servicio Material Bibliográfico'
        context['entity'] = 'Material'
        context['list_url'] = self.success_url
        context['action'] = 'delete'

        return context


# =========================
# LIST VIEW
# =========================
class MaterialBibliograficoListView(LoginRequiredMixin, InformeBloqueoMixin, ListView):
    model = MaterialBibliografico
    template_name = 'biblioteca/pem/matbibl/list_matbiblio.html'

    # =========================
    # SESSION
    # =========================
    def get_queryset(self):
        periodo = self.get_periodo_activo()
        return self.model.objects.filter(
            cueanexo=str(periodo.cueanexo),
            mes=periodo.meses,
            anio=periodo.annos,
        ).select_related(
            'servicio', 'turnos', 't_material'
        ).order_by('-anio', '-mes')

    def post(self, request, *args, **kwargs):
        try:
            if request.POST.get('action') == 'searchdata':

                data = [obj.toJSON() for obj in self.get_queryset()]

                return JsonResponse(data, safe=False)

            return JsonResponse({
                'error': True,
                'message': 'Acción no válida'
            })

        except Exception as e:
            import traceback
            print(traceback.format_exc())

            return JsonResponse({
                'error': True,
                'message': str(e)
            }, status=500)

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)


        context['title'] = 'Listado de Material Bibliográfico'
        context['create_url'] = reverse_lazy('bibliotecas:materialbibliografico_create')
        context['list_url'] = reverse_lazy('bibliotecas:materialbibliografico_list')
        context['update_url'] = reverse_lazy('bibliotecas:materialbibliografico_update', args=[0])
        context['hide_lock_button'] = False    
        context['generar_pdf_button'] = True,    
        context['next_url'] = reverse_lazy('bibliotecas:servref_list')
        context['entity'] = 'Material Bibliografico'
        return context
