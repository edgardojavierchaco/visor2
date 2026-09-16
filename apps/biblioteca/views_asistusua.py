from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import AsistenciaUsuarios
from .forms import AsistenciaUsuariosForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Func, Value, CharField
from .mixins import InformeBloqueoMixin

# =========================
# 🔹 UTIL
# =========================
class AsistUsuarioCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = AsistenciaUsuarios
    form_class = AsistenciaUsuariosForm
    template_name = 'biblioteca/pem/asistusua/create.html'
    success_url = reverse_lazy('bibliotecas:asistusua_list')
    
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




        
        context['title'] = 'Carga de Asistencia de Usuarios'
        context['entity'] = 'Asistencia'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        
        return context


#===========================
# UPDATE
#===========================
class AsistUsuaUpdateView(LoginRequiredMixin, InformeBloqueoMixin,UpdateView):
    model = AsistenciaUsuarios
    form_class = AsistenciaUsuariosForm
    template_name = 'biblioteca/pem/asistusua/create.html'
    success_url = reverse_lazy('bibliotecas:asistusua_list')
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


        
        context['title'] = 'Edición de Asistencia de Usuarios'
        context['entity'] = 'Asistencia'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        

            
        return context


#=====================
# DELETE
#=====================
class AsistUsuaDeleteView(LoginRequiredMixin, InformeBloqueoMixin,DeleteView):
    model = AsistenciaUsuarios
    template_name = 'biblioteca/pem/asistusua/delete.html'
    success_url = reverse_lazy('bibliotecas:asistusua_list')
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

    
        context['title'] = 'Eliminación de Asistencia de Usuarios'
        context['entity'] = 'Asistencia'
        context['list_url'] = self.success_url
        
        return context


#=========================
# LIST
#=========================
class AsistUsuaListView(LoginRequiredMixin, InformeBloqueoMixin, ListView):
    model = AsistenciaUsuarios
    template_name = 'biblioteca/pem/asistusua/list_asistusua.html' 
    
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


        

        context['title'] = 'Listado de Asistencia de Usuarios'
        context['create_url'] = reverse_lazy('bibliotecas:asistusua_create')
        context['list_url'] = reverse_lazy('bibliotecas:asistusua_list')
        context['update_url'] = reverse_lazy('bibliotecas:asistusua_update', args=[0]) 
        context['hide_lock_button'] = False      
        context['generar_pdf_button'] = True,  
        context['before_url']=reverse_lazy('bibliotecas:infopedago_list')
        context['next_url'] = reverse_lazy('bibliotecas:instituciones_list')
        context['entity'] = 'Asistencia'
        return context

