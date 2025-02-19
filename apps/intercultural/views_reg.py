from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, resolve_url
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import VistaAlumnosBilingue, Alumnos_Bilingue
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin


class VistaAlumnosBilingueListRegView(LoginRequiredMixin, ListView):
    model = VistaAlumnosBilingue
    template_name = 'intercultural/alumnos/list_reg.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):       
        return VistaAlumnosBilingue.objects.all()
        

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Alumnos Bilingües cargados'
        context['create_url'] = reverse_lazy('intercultural:alumnos_create')
        context['list_url'] = reverse_lazy('intercultural:alumnos_list_reg')
        context['update_url'] = reverse_lazy('intercultural:alumnos_update', args=[0]) 
        context['entity'] = 'Alumnos Bilingües'
        return context


class VistaAlumnosBilingueListRegView2(LoginRequiredMixin, ListView):
    model = VistaAlumnosBilingue
    template_name = 'intercultural/alumnos/list_reg_cue.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):       
        queryset = Alumnos_Bilingue.objects.all()  # Inicialmente, toma todos los registros

        # Filtrar por 'cueanexo' si está presente en la solicitud
        cueanexo = self.request.POST.get('cueanexo', None)
        print(cueanexo)
        if cueanexo:
            queryset = queryset.filter(cueanexo=cueanexo)
        
        return queryset
        

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  
        cueanexo = self.kwargs.get('cueanexo', None)       
        context['title'] = 'Listado de Alumnos Bilingües cargados' 
        context['create_url'] = reverse_lazy('intercultural:alumnos_create')
        context['list_url'] = resolve_url('intercultural:alumnos_list_reg_cue', cueanexo) if cueanexo else ''
     
        context['entity'] = 'Alumnos Bilingües'
        return context


