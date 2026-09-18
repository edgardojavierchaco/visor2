from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import InstitucionesPrestaServicios, Escuelas
from .forms import InstitucionesPrestaServiciosForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import InformeBloqueoMixin

# =========================
# 🔹 UTIL
# =========================
class InstitucionesCreateView(LoginRequiredMixin, InformeBloqueoMixin,CreateView):
    model = InstitucionesPrestaServicios
    form_class = InstitucionesPrestaServiciosForm
    template_name = 'biblioteca/pem/instituciones/create.html'
    success_url = reverse_lazy('bibliotecas:instituciones_list')

    
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

            return JsonResponse({
                'error': True,
                'message': 'Acción no válida'
            })

        except Exception as e:
            return JsonResponse({
                'error': True,
                'message': str(e)
            })

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)




        
        context['title'] = 'Carga de Instituciones Presta Servicios'
        context['entity'] = 'Instituciones'
        context['list_url'] = self.success_url
        context['action'] = 'add'        
            
        return context


#===========================
# UPDATE
#===========================
class InstitucionesUpdateView(LoginRequiredMixin, InformeBloqueoMixin,UpdateView):
    model = InstitucionesPrestaServicios
    form_class = InstitucionesPrestaServiciosForm
    template_name = 'biblioteca/pem/instituciones/create.html'
    success_url = reverse_lazy('bibliotecas:instituciones_list')
    url_redirect = success_url

    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        # 🔒 BLOQUEO
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


        
        context['title'] = 'Edición de Instituciones'
        context['entity'] = 'Instituciones'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        

            
        return context


#=====================
# DELETE
#=====================
class InstitucionesDeleteView(LoginRequiredMixin, InformeBloqueoMixin,DeleteView):
    model = InstitucionesPrestaServicios
    template_name = 'biblioteca/pem/instituciones/delete.html'
    success_url = reverse_lazy('bibliotecas:instituciones_list')
    url_redirect = success_url

    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        # 🔒 BLOQUEO
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

    
        context['title'] = 'Eliminación de Instituciones'
        context['entity'] = 'Instituciones'
        context['list_url'] = self.success_url
        
        return context


#=========================
# LIST
#=========================
class InstitucionesListView(LoginRequiredMixin, InformeBloqueoMixin, ListView):
    model = InstitucionesPrestaServicios
    template_name = 'biblioteca/pem/instituciones/list_instituciones.html'
    
    # =========================
    # SESSION
    # =========================
    def get_queryset(self):
        periodo = self.get_periodo_activo()
        return self.model.objects.filter(
            cueanexo=str(periodo.cueanexo),
            mes=periodo.meses,
            anio=periodo.annos,
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


    

        context['title'] = 'Listado de Instituciones Presta Servicios'
        context['create_url'] = reverse_lazy('bibliotecas:instituciones_create')
        context['list_url'] = reverse_lazy('bibliotecas:instituciones_list')
        context['update_url'] = reverse_lazy('bibliotecas:instituciones_update', args=[0]) 
        context['entity'] = 'Instituciones'
        context['hide_lock_button'] = False      
        context['generar_pdf_button'] = True,  
        context['before_url'] = reverse_lazy('bibliotecas:asistusua_list')
        context['next_url'] = reverse_lazy('bibliotecas:proctec_list')
        return context


class ObtenerEscuelaView(View):
    def get(self, request, *args, **kwargs):
        cueanexo_parcial = request.GET.get('cueanexo', None)
        if cueanexo_parcial:
            escuelas = Escuelas.objects.filter(cueanexo__icontains=cueanexo_parcial)[:10]
            results = []
            for escuela in escuelas:
                results.append({
                    'cueanexo': escuela.cueanexo,
                    'nom_est': escuela.nom_est,
                })
            return JsonResponse(results, safe=False)
        return JsonResponse([], safe=False)
