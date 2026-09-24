import re
from urllib.parse import urlencode

from django.db import connection
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
        .values('id', 'cuil', 'dni', 'apellido', 'nombre')
        .first()
    )


def _obtener_actividades_bnh(persona_id, cueanexo):
    """Devuelve las actividades BNH no eliminadas de la persona en el CUE-Anexo."""
    if not persona_id or not cueanexo:
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                ra.id,
                ra.ceic_id,
                COALESCE(ceic.descripcion, ''),
                ra.sit_revista_id,
                COALESCE(sr.descrip_sitrev, ''),
                ra.f_desde,
                ra.f_hasta,
                COALESCE(ra.turno, ''),
                COALESCE(ra.estado, ''),
                COALESCE(ra.validacion, '')
            FROM bnh.registro_actividades ra
            LEFT JOIN bnh.nomenclador_ceic ceic
                ON ceic.c_ceic = ra.ceic_id
            LEFT JOIN bnh.situacion_revista sr
                ON sr.cod_sitrev = ra.sit_revista_id
            WHERE ra.persona_id = %s
              AND ra.cueanexo = %s
              AND ra.eliminado IS NOT TRUE
            ORDER BY ra.f_desde DESC NULLS LAST, ra.id DESC
            """,
            [persona_id, str(cueanexo)],
        )
        filas = cursor.fetchall()

    return [
        {
            'id': fila[0],
            'ceic_id': fila[1],
            'cargo': fila[2] or '',
            'situacion_revista_id': fila[3],
            'situacion_revista': fila[4] or '',
            'f_desde': fila[5],
            'f_hasta': fila[6],
            'turno': fila[7] or '',
            'estado': fila[8] or '',
            'validacion': fila[9] or '',
        }
        for fila in filas
    ]


def _url_alta_personal_bnh(cuil, periodo):
    retorno = reverse('bibliotecas:bibliotecario_create')
    retorno_params = {
        'periodo': periodo.pk,
        'cuil': cuil,
        'reconsultar_bnh': '1',
    }
    retorno = f"{retorno}?{urlencode(retorno_params)}"

    params = {
        'cuil': cuil,
        'next': retorno,
        'return_label': 'Volver a Personal bibliotecario',
    }
    return f"/bnh/carga-personal/?{urlencode(params)}"


def _url_vincular_personal_bnh():
    # La ruta está confirmada; no se agregan parámetros no verificados.
    return '/bnh/personas/vincular/'


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
                'message': 'El CUIL ingresado no es válido. Verificá los 11 dígitos.',
            }, status=400)

        periodo = self.get_periodo_activo()
        persona = _buscar_persona_bnh(cuil)

        if persona is None:
            return JsonResponse({
                'error': False,
                'estado': 'persona_no_existe',
                'message': 'La persona no está registrada en BNH.',
                'persona': None,
                'accion': {
                    'label': 'Dar de alta en BNH',
                    'icon': 'person_add',
                    'url': _url_alta_personal_bnh(cuil, periodo),
                },
            })

        persona_json = {
            'cuil': persona['cuil'] or '',
            'dni': persona['dni'] or '',
            'apellido': persona['apellido'] or '',
            'nombre': persona['nombre'] or '',
        }

        actividades = _obtener_actividades_bnh(persona['id'], periodo.cueanexo)
        if not actividades:
            return JsonResponse({
                'error': False,
                'estado': 'persona_sin_vinculacion',
                'message': (
                    'La persona existe en BNH, pero todavía no está vinculada '
                    'a esta institución.'
                ),
                'persona': persona_json,
                'accion': {
                    'label': 'Vincular existente',
                    'icon': 'link',
                    'url': _url_vincular_personal_bnh(),
                },
            })

        if len(actividades) == 1:
            mensaje = 'Personal encontrado con un cargo en esta institución.'
        else:
            mensaje = (
                'Personal encontrado con varios cargos en esta institución. '
                'Seleccioná el que corresponde a este registro.'
            )

        return JsonResponse({
            'error': False,
            'estado': 'persona_vinculada',
            'message': mensaje,
            'persona': persona_json,
            'actividades': actividades,
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
        self.actividad_bnh_error = None
        self.actividad_bnh = None

        if data is None:
            return kwargs

        data = data.copy()
        cuil = _normalizar_cuil(data.get('cuil'))
        data['cuil'] = cuil

        if len(cuil) != 11:
            self.persona_bnh_error = 'El CUIL ingresado no es válido. Verificá los 11 dígitos.'
        else:
            persona = _buscar_persona_bnh(cuil)
            if persona is None:
                self.persona_bnh_error = 'La persona no está registrada en BNH.'
            else:
                actividades = _obtener_actividades_bnh(
                    persona['id'],
                    self.get_periodo_activo().cueanexo,
                )

                if not actividades:
                    self.persona_bnh_error = (
                        'La persona existe en BNH, pero todavía no está vinculada '
                        'a esta institución.'
                    )
                else:
                    actividad_id = str(data.get('bnh_actividad_id') or '').strip()

                    if actividad_id:
                        self.actividad_bnh = next(
                            (
                                actividad
                                for actividad in actividades
                                if str(actividad['id']) == actividad_id
                            ),
                            None,
                        )
                        if self.actividad_bnh is None:
                            self.actividad_bnh_error = (
                                'El cargo seleccionado ya no está disponible para esta persona '
                                'en la institución. Reconsultá BNH.'
                            )
                    elif len(actividades) == 1:
                        self.actividad_bnh = actividades[0]
                        data['bnh_actividad_id'] = str(self.actividad_bnh['id'])
                    else:
                        self.actividad_bnh_error = (
                            'Seleccioná el cargo de BNH que corresponde a este registro.'
                        )

                    if self.actividad_bnh is not None:
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

                if self.persona_bnh_error or self.actividad_bnh_error:
                    errors = {}
                    if self.persona_bnh_error:
                        errors['cuil'] = [self.persona_bnh_error]
                    if self.actividad_bnh_error:
                        errors['bnh_actividad_id'] = [self.actividad_bnh_error]
                    return JsonResponse({
                        'error': True,
                        'errors': errors,
                    })

                if form.is_valid():
                    actividad = self.actividad_bnh or {}
                    turno_nombre = (actividad.get('turno') or '').strip()

                    instance = form.save(commit=False)
                    self.aplicar_periodo_activo(instance)

                    # Snapshot laboral de la actividad BNH elegida para este período.
                    instance.cargo = actividad.get('cargo') or None
                    instance.situacion_revista = actividad.get('situacion_revista') or None
                    instance.f_ingreso = actividad.get('f_desde') or None
                    instance.f_hasta = actividad.get('f_hasta') or None
                    instance.turno_bnh = turno_nombre or None

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
        context['bnh_cuil_inicial'] = _normalizar_cuil(
            self.request.GET.get('cuil')
        )
        context['bnh_reconsultar'] = (
            self.request.GET.get('reconsultar_bnh') == '1'
        )

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
        
