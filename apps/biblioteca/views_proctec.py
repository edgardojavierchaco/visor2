from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import ProcesosTecnicos, TipoMaterialBiblio, es_planilla_biblioteca_nueva
from .forms import ProcesosTecnicosForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Func, F, Sum, Value 
from .mixins import InformeBloqueoMixin
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

# =========================
# 🔹 UTIL
# =========================
class ProcTecCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = ProcesosTecnicos
    form_class = ProcesosTecnicosForm
    template_name = 'biblioteca/pem/proctec/create.html'
    success_url = reverse_lazy('bibliotecas:proctec_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['periodo'] = self.get_periodo_activo()
        return kwargs
        
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




        
        context['title'] = 'Carga de Procesos Técnicos'
        context['entity'] = 'Procesos_Técnicos'
        context['list_url'] = self.success_url
        context['action'] = 'add'        
        
        return context


#===========================
# UPDATE
#===========================
class ProcTecUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = ProcesosTecnicos
    form_class = ProcesosTecnicosForm
    template_name = 'biblioteca/pem/proctec/create.html'
    success_url = reverse_lazy('bibliotecas:proctec_list')
    url_redirect = success_url

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['periodo'] = self.get_periodo_activo()
        return kwargs

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


        
        context['title'] = 'Edición de Procesos Técnicos'
        context['entity'] = 'Procesos_Técnicos'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        

                
        return context


#=====================
# DELETE
#=====================
class ProcTecDeleteView(LoginRequiredMixin, InformeBloqueoMixin, DeleteView):
    model = ProcesosTecnicos
    template_name = 'biblioteca/pem/proctec/delete.html'
    success_url = reverse_lazy('bibliotecas:proctec_list')
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

    
        context['title'] = 'Eliminación de Procesos Técnicos'
        context['entity'] = 'Procesos_Técnicos'
        context['list_url'] = self.success_url
        return context

#=========================
# LIST
#=========================
class ProcTecListView(LoginRequiredMixin, InformeBloqueoMixin, ListView):
    model = ProcesosTecnicos
    template_name = 'biblioteca/pem/proctec/list_proctec.html'  
    
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
            'material'
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

        periodo = self.get_periodo_activo()
        planilla_nueva = es_planilla_biblioteca_nueva(
            periodo.meses,
            periodo.annos,
        )

        registros_por_material = {}
        procesos_ordenados = (
            self.model._meta.get_field('procesos').choices
            if planilla_nueva
            else (
                ('SELLADOS', 'SELLADOS'),
                ('INVENTARIADOS', 'INVENTARIADOS'),
                ('CLASIFICADOS', 'CLASIFICADOS'),
                ('CATALOGADOS', 'CATALOGADOS'),
                ('RESTAURADOS', 'RESTAURADOS'),
                ('BAJAS', 'BAJAS'),
            )
        )
        orden_procesos = {
            codigo: indice
            for indice, (codigo, _etiqueta) in enumerate(procesos_ordenados)
        }

        for registro in context.get('object_list') or ():
            total = registro.total or 0
            if total <= 0:
                continue

            etiqueta = (
                'Inventario total'
                if registro.procesos == 'INVENTARIO TOTAL'
                else f"Total {registro.procesos.lower()}"
            )
            registros_por_material.setdefault(registro.material_id, []).append({
                'proceso': registro.procesos,
                'etiqueta': etiqueta,
                'total': total,
            })

        materiales_activos = TipoMaterialBiblio.objects.order_by('pk')
        if planilla_nueva:
            materiales_activos = materiales_activos.filter(
                pk__in=(1, 2, 3, 4, 5, 6)
            )

        context['resumen_procesos_material'] = []
        for material in materiales_activos:
            procesos = registros_por_material.get(material.pk, [])
            procesos.sort(
                key=lambda item: orden_procesos.get(item['proceso'], 999)
            )
            context['resumen_procesos_material'].append({
                'id': material.pk,
                'nombre': material.nom_material,
                'procesos': procesos,
            })

        context['title'] = 'Listado de Procesos Técnicos'
        context['create_url'] = reverse_lazy('bibliotecas:proctec_create')
        context['list_url'] = reverse_lazy('bibliotecas:proctec_list')
        context['update_url'] = reverse_lazy('bibliotecas:proctec_update', args=[0]) 
        context['hide_lock_button'] = False    
        context['generar_pdf_button'] = True,  
        context['before_url'] = reverse_lazy('bibliotecas:instituciones_list')
        context['next_url'] = reverse_lazy('bibliotecas:aguapey_list')
        context['entity'] = 'Procesos Técnicos'
        return context
