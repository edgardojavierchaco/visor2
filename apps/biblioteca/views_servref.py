from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import ServicioReferencia, ServiciosMatBiblio, es_planilla_biblioteca_nueva
from .forms import ServicioReferenciaForm
from .mixins import InformeBloqueoMixin

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator


# =========================
# 🔹 UTIL
# =========================
class ServiciosReferenciaCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = ServicioReferencia
    form_class = ServicioReferenciaForm
    template_name = 'biblioteca/pem/servref/create.html'
    success_url = reverse_lazy('bibliotecas:servref_list')

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





        context['title'] = 'Carga Servicios de Referencia'
        context['entity'] = 'Servicios_Referencia'
        context['list_url'] = self.success_url
        context['action'] = 'add'

        return context


#===========================
# UPDATE
#===========================
class ServiciosReferenciaUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = ServicioReferencia
    form_class = ServicioReferenciaForm
    template_name = 'biblioteca/pem/servref/create.html'
    success_url = reverse_lazy('bibliotecas:servref_list')
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



        context['title'] = 'Edición Servicios de Referencia'
        context['entity'] = 'Servicios_Referencia'
        context['list_url'] = self.success_url
        context['action'] = 'edit'



        return context



#=====================
# DELETE
#=====================
class ServiciosReferenciaDeleteView(LoginRequiredMixin, InformeBloqueoMixin, DeleteView):
    model = ServicioReferencia
    template_name = 'biblioteca/pem/servref/delete.html'
    success_url = reverse_lazy('bibliotecas:servref_list')
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


        context['title'] = 'Eliminación Servicios de Referencia'
        context['entity'] = 'Servicios_Referencia'
        context['list_url'] = self.success_url

        return context


#=========================
# LIST
#=========================
class ServiciosReferenciaListView(LoginRequiredMixin, InformeBloqueoMixin, ListView):
    model = ServicioReferencia
    template_name = 'biblioteca/pem/servref/list_servref.html'

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

        registros_por_servicio = {}

        for registro in context.get('object_list') or ():
            varones = registro.varones or 0
            total = registro.total or 0
            if varones <= 0 and total <= 0:
                continue

            servicio = registros_por_servicio.setdefault(
                registro.servicio_id,
                {
                    'turnos': {},
                    'varones': 0,
                    'total': 0,
                },
            )
            turno_id = registro.turnos_id
            turno = servicio['turnos'].setdefault(
                turno_id,
                {
                    'orden': turno_id,
                    'nombre': registro.turnos.nom_turno,
                    'varones': 0,
                    'total': 0,
                },
            )
            turno['varones'] += varones
            turno['total'] += total
            servicio['varones'] += varones
            servicio['total'] += total

        periodo = self.get_periodo_activo()
        codigos_servicio = (
            (211, 212)
            if es_planilla_biblioteca_nueva(
                periodo.meses,
                periodo.annos,
            )
            else (210, 211, 212, 213)
        )
        servicios_activos = (
            ServiciosMatBiblio.objects
            .filter(cod_servicio__in=codigos_servicio)
            .order_by('cod_servicio', 'pk')
        )

        context['resumen_referencia_servicios'] = []
        for servicio in servicios_activos:
            resumen = registros_por_servicio.get(
                servicio.pk,
                {
                    'turnos': {},
                    'varones': 0,
                    'total': 0,
                },
            )
            turnos = list(resumen['turnos'].values())
            turnos.sort(key=lambda item: item['orden'])

            context['resumen_referencia_servicios'].append({
                'id': servicio.pk,
                'nombre': servicio.nom_servicio,
                'turnos': turnos,
                'varones': resumen['varones'],
                'total': resumen['total'],
            })

        context['title'] = 'Listado de Servicios de Referencia'
        context['create_url'] = reverse_lazy('bibliotecas:servref_create')
        context['list_url'] = reverse_lazy('bibliotecas:servref_list')
        context['update_url'] = reverse_lazy('bibliotecas:servref_update', args=[0])

        context['hide_lock_button'] = False
        context['generar_pdf_button'] = True
        context['before_url'] = reverse_lazy('bibliotecas:materialbibliografico_list')
        context['next_url'] = reverse_lazy('bibliotecas:servrefvirtual_list')

        context['entity'] = 'Servicios_Referencia'

        return context
