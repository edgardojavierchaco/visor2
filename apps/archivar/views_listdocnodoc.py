from django.db import connection
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.generic import View
from shapely import total_bounds
from apps.biblioteca.models import DocentePonMensual, NoDocentesMensual, FocalLicDocentes
from apps.biblioteca.forms import DocentePonMensualForm, NoDocentesMensualForm
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F


# Listar Nómina de Docentes
class DocentePonMensualListView(LoginRequiredMixin, ListView):    
    model = DocentePonMensual
    template_name = 'archivos/docentes/list_docentes.html'    

    def get_queryset(self):    
        # Obtenemos todos los docentes para el usuario actual
        docentes = DocentePonMensual.objects.all()
        return docentes

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                docentes_data = [
                    {
                        'id': docente.id,
                        'cueanexo': docente.cueanexo,
                        'cuof': docente.cuof,
                        'cuof_anexo': docente.cuof_anexo,
                        'ptaid': docente.ptaid,
                        'apellidos': docente.apellidos,
                        'nombres': docente.nombres,
                        'n_doc': docente.n_doc,
                        'cuil': docente.cuil,
                        'f_nac': docente.f_nac,
                        'sit_rev': docente.sit_rev,
                        'nivel': docente.nivel,
                        'ceic': docente.ceic,
                        'denom_cargo': docente.denom_cargo,
                        'f_desde': docente.f_desde,
                        'f_hasta': docente.f_hasta,
                        'regional': docente.regional,
                        'localidad': docente.localidad,
                    }
                    for docente in self.get_queryset()
                ]
                data['docentes'] = docentes_data
                print(docentes_data)
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nómina de Personal Docente (** Base de Datos PON)'        
        context['list_url'] = reverse_lazy('archivos:nom_doc')      
        context['entity'] = 'Docentes'

        # Obtenemos todos los docentes para pasarlos al contexto
        context['docentes'] = self.get_queryset()

        return context

# Listar Nómina de No Docentes
class NoDocentePonMensualListView(LoginRequiredMixin, ListView):    
    model = NoDocentesMensual
    template_name = 'archivos/docentes/list_nodocentes.html'    

    def get_queryset(self):    
        # Filtra los docentes por 'cueanexo' del usuario logueado        
        nodocentes= NoDocentesMensual.objects.all()
        print('no docentes',nodocentes)
        return nodocentes
    
    @method_decorator(csrf_exempt)  # No es recomendable deshabilitar CSRF sin necesidad
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')  # Usar .get() por si la clave no está presente
            if action == 'searchdata':
                # Obtiene los datos de los docentes según el filtro
                nodocentes_data = [
                    {
                        'id': docente.id,
                        'cueanexo': docente.cueanexo or '',  
                        'cuof': docente.cuof or '',  
                        'cuof_anexo': docente.cuof_anexo or '',
                        'ptaid': docente.ptaid or '',
                        'apellidos': docente.apellidos or '',
                        'nombres': docente.nombres or '',
                        'ndoc': docente.ndoc or '',
                        'cuil': docente.cuil or '',
                        'f_nac': docente.f_nac or '',
                        'denom_cargo': docente.denom_cargo or '',
                        'categ': docente.categ or '',
                        'gpo': docente.gpo or '',
                        'apart': docente.apart or '',
                        'f_desde': docente.f_desde or '',
                        'f_hasta': docente.f_hasta or '',
                        'regional': docente.regional or '',
                        'localidad': docente.localidad or '',
                    }
                    for docente in self.get_queryset()
                ]

                data['nodocentes'] = nodocentes_data  # Renombrado para consistencia
                print('data de no docentes:', nodocentes_data)  
            else:
                data['error'] = 'Acción no reconocida'  # Mensaje más claro
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nómina de Personal No Docente (** Base de Datos PON)'        
        context['list_url'] = reverse_lazy('archivos:nom_ndoc')      
        context['entity'] = 'No Docentes'
        
        context['nodocentes'] = self.get_queryset()
        
        return context


class DocentePonMensualSumaListView(LoginRequiredMixin, ListView):
    model = DocentePonMensual
    template_name = 'archivos/docentes/list_docentes_sum.html'

    def get_queryset(self):
        # Obtener el CUIL desde la URL
        cuil = self.kwargs.get('cuil')

        # Agrupar por CUIL y Cargo, sumando la carga horaria
        docentes = (
            DocentePonMensual.objects
            .filter(cuil=cuil)  # Filtra por CUIL recibido
            .values('cuil', 'denom_cargo')
            .annotate(total_horas=Sum('carga_horaria'))
            .order_by('cuil', 'denom_cargo')
        )

        # Calcular el total general de carga horaria
        total_general = DocentePonMensual.objects.filter(cuil=cuil).aggregate(total=Sum('carga_horaria'))['total'] or 0

        # Agrupar Focalizados por CUIL y descripción
        afectaciones_agrupadas = (
            FocalLicDocentes.objects
            .filter(cuil=cuil)
            .values('cuil')
            .annotate(ptatipo=F('ptatipo'), total_afectaciones=Sum('hs_cat'))
            .order_by('cuil', 'ptatipo')
        )

        total_afectaciones_general = sum(item['total_afectaciones'] or 0 for item in afectaciones_agrupadas)

        # Agrupar Licencias por CUIL y descripción
        licencias_agrupadas = (
            FocalLicDocentes.objects
            .filter(cuil=cuil)
            .values('cuil')
            .annotate(ptatipo=F('desc_lic'), total_licencias=Sum('lic_hs'))
            .order_by('cuil', 'desc_lic')
        )

        total_licencias_general = sum(item['total_licencias'] or 0 for item in licencias_agrupadas)

        return docentes, total_general, afectaciones_agrupadas, total_afectaciones_general, licencias_agrupadas, total_licencias_general

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nómina de Personal Docente (** Base de Datos PON)'
        context['list_url'] = reverse_lazy('archivos:nom_doc')
        context['entity'] = 'Docentes'

        docentes, total_general, afectaciones_agrupadas, total_afectaciones_general, licencias_agrupadas, total_licencias_general = self.get_queryset()
        print(docentes, total_general, afectaciones_agrupadas, total_afectaciones_general, licencias_agrupadas, total_licencias_general)
        context['docentes'] = docentes
        context['total_general'] = total_general
        context['afectaciones_agrupadas'] = afectaciones_agrupadas
        context['total_afectaciones_general'] = total_afectaciones_general
        context['licencias_agrupadas'] = licencias_agrupadas
        context['total_licencias_general'] = total_licencias_general

        return context
