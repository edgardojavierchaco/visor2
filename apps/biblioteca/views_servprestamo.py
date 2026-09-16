from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import ServicioPrestamo
from .forms import ServicioPrestamoForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import InformeBloqueoMixin

# =========================
# 🔹 UTIL
# =========================
class ServiciosPrestamoCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = ServicioPrestamo
    form_class = ServicioPrestamoForm
    template_name = 'biblioteca/pem/servprestamo/create.html'
    success_url = reverse_lazy('bibliotecas:servprestamo_list')    
    
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




        
        context['title'] = 'Carga Servicios de Préstamos'
        context['entity'] = 'Servicios_Préstamo'
        context['list_url'] = self.success_url
        context['action'] = 'add'        
            
        return context


#===========================
# UPDATE
#===========================
class ServiciosPrestamoUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = ServicioPrestamo
    form_class = ServicioPrestamoForm
    template_name = 'biblioteca/pem/servprestamo/create.html'
    success_url = reverse_lazy('bibliotecas:servprestamo_list')
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


        
        context['title'] = 'Edición Servicios de Préstamos'
        context['entity'] = 'Servicios_Préstamo'
        context['list_url'] = self.success_url
        context['action'] = 'edit'        
        

            
        return context


#=====================
# DELETE
#=====================
class ServiciosPrestamoDeleteView(LoginRequiredMixin, InformeBloqueoMixin, DeleteView):
    model = ServicioPrestamo
    template_name = 'biblioteca/pem/servprestamo/delete.html'
    success_url = reverse_lazy('bibliotecas:servprestamo_list')
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

    
        context['title'] = 'Eliminación Servicios de Préstamos'
        context['entity'] = 'Servicios_Préstamo'
        context['list_url'] = self.success_url
        
        return context


#=========================
# LIST
#=========================
class ServiciosPrestamoListView(LoginRequiredMixin, InformeBloqueoMixin, ListView):
    model = ServicioPrestamo
    template_name = 'biblioteca/pem/servprestamo/list_servprestamo.html'
      
    
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
            'servicio', 'turnos'
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


    

        context['title'] = 'Listado de Servicios de Préstamos cargado'
        context['create_url'] = reverse_lazy('bibliotecas:servprestamo_create')
        context['list_url'] = reverse_lazy('bibliotecas:servprestamo_list')
        context['update_url'] = reverse_lazy('bibliotecas:servprestamo_update', args=[0]) 
        context['hide_lock_button'] = False    
        context['generar_pdf_button'] = True,    
        context['before_url'] = reverse_lazy('bibliotecas:servrefvirtual_list')
        context['next_url'] = reverse_lazy('bibliotecas:infopedago_list')
        context['entity'] = 'Servicios_Préstamo'
        return context
