import re

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.bnhpersonas.models import Personas

from .mixins import InformeBloqueoMixin
from .models import BibliotecariosCue
from .forms import BibliotecariosCueForm
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


# =========================
# UTIL: PERSONA BNH (SOLO LECTURA)
# =========================
def _normalizar_cuil(cuil):
    return re.sub(r'\D', '', cuil or '')


def _buscar_persona_bnh(cuil):
    cuil = _normalizar_cuil(cuil)
    if len(cuil) != 11:
        return None
    return (
        Personas.objects
        .filter(cuil=cuil)
        .values('cuil', 'dni', 'apellido', 'nombre')
        .first()
    )


class BibliotecarioPersonaLookupView(
    LoginRequiredMixin,
    InformeBloqueoMixin,
    View,
):
    """Consulta de identidad BNH por CUIL para un período editable."""

    def get(self, request, *args, **kwargs):
        cuil = _normalizar_cuil(request.GET.get('cuil'))
        if len(cuil) != 11:
            return JsonResponse({
                'error': True,
                'message': 'Ingresá un CUIL válido de 11 dígitos.',
            }, status=400)

        persona = _buscar_persona_bnh(cuil)
        if persona is None:
            return JsonResponse({
                'error': True,
                'message': 'No se encontró una persona con ese CUIL en BNH.',
            }, status=404)

        return JsonResponse({
            'error': False,
            'persona': {
                'cuil': persona['cuil'] or '',
                'dni': persona['dni'] or '',
                'apellido': persona['apellido'] or '',
                'nombre': persona['nombre'] or '',
            },
        })


class BibliotecariosCueCreateView(LoginRequiredMixin, InformeBloqueoMixin,CreateView):
    model = BibliotecariosCue
    form_class = BibliotecariosCueForm
    template_name = 'biblioteca/pem/personal/create.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        data = kwargs.get('data')
        self.persona_bnh_error = None

        if data is None:
            return kwargs

        data = data.copy()
        cuil = _normalizar_cuil(data.get('cuil'))
        data['cuil'] = cuil

        if len(cuil) != 11:
            self.persona_bnh_error = 'Ingresá un CUIL válido de 11 dígitos.'
        else:
            persona = _buscar_persona_bnh(cuil)
            if persona is None:
                self.persona_bnh_error = 'No se encontró una persona con ese CUIL en BNH.'
            else:
                # BNH es la fuente de identidad para las altas nuevas.
                data['n_doc'] = persona['dni'] or ''
                data['apellidos'] = persona['apellido'] or ''
                data['nombres'] = persona['nombre'] or ''

        kwargs['data'] = data
        return kwargs

    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        try:
            action = request.POST.get('action')

            if action == 'add':

                form = self.get_form()

                if self.persona_bnh_error:
                    return JsonResponse({
                        'error': True,
                        'errors': {
                            'cuil': [self.persona_bnh_error]
                        }
                    })

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




        
        context['title'] = 'Personal bibliotecario'
        context['entity'] = 'Personal'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        

        return context


# =========================================================
# UPDATE
# =========================================================
class BibliotecariosCueUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = BibliotecariosCue
    form_class = BibliotecariosCueForm
    template_name = 'biblioteca/pem/personal/create.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')
    url_redirect = success_url

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        data = kwargs.get('data')

        if data is None:
            return kwargs

        data = data.copy()
        objeto = self.get_object()
        # La identidad histórica del registro no se modifica desde campos ocultos.
        data['cuil'] = objeto.cuil
        data['n_doc'] = objeto.n_doc
        data['apellidos'] = objeto.apellidos
        data['nombres'] = objeto.nombres
        kwargs['data'] = data
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


    
        context['title'] = 'Personal bibliotecario'
        context['entity'] = 'Personal'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        

            
        return context


# =========================================================
# DELETE
# =========================================================
class BibliotecariosCueDeleteView(LoginRequiredMixin, InformeBloqueoMixin, DeleteView):
    model = BibliotecariosCue
    template_name = 'biblioteca/pem/personal/delete.html'
    success_url = reverse_lazy('bibliotecas:bibliotecario_list')
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

        
        context['title'] = 'Eliminación Personal'
        context['entity'] = 'Personal'
        context['list_url'] = self.success_url
        return context


#=========================
# LIST
#=========================
class BibliotecariosCueListView(LoginRequiredMixin, InformeBloqueoMixin, ListView):
    model = BibliotecariosCue
    template_name = 'biblioteca/pem/personal/list_bibliotecario.html'    

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
            'turno', 'licencia_permiso', 'situacion_laboral'
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


    

        context['title'] = 'Personal bibliotecario'
        context['section_nav_title'] = 'Listado de Personal Bibliotecario'
        context['create_url'] = reverse_lazy('bibliotecas:bibliotecario_create')
        context['list_url'] = reverse_lazy('bibliotecas:bibliotecario_list')
        context['update_url'] = reverse_lazy('bibliotecas:bibliotecario_update', args=[0])
        context['generar_pdf_button'] = False
        context['generar_pdf_url'] = reverse_lazy('bibliotecas:generar_pdf')
        context['before_url'] = reverse_lazy('bibliotecas:fondos_list')
        context['entity'] = 'Personal'
        
        return context
        
