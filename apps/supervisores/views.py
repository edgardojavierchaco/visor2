from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Supervisor, EscuelaSupervisor, DirectoresRegionales
from .forms import FiltroRegionalForm, SupervisorForm, EscuelaForm

#################################
#    Vistas para Supervisor     #
#################################
class SupervisorListView(ListView):
    model = Supervisor
    template_name = 'supervisores/lista_supervisores.html'
    context_object_name = 'supervisores'   
    
    def get_queryset(self):
        queryset = super().get_queryset()
        regional = self.request.GET.get('region')     

        if regional:
            queryset = queryset.filter(region__iexact=regional)        
        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        form = FiltroRegionalForm(self.request.GET or None, user=self.request.user)
        context['form']= form
        context['title'] = 'Listado de Supervisores'
        return context


class SupervisorCreateView(CreateView):
    model = Supervisor
    form_class = SupervisorForm
    template_name = 'supervisores/crear_supervisor.html'
    success_url = reverse_lazy('supervis:lista_supervisores')
    

class SupervisorUpdateView(UpdateView):
    model = Supervisor
    form_class = SupervisorForm
    template_name = 'supervisores/crear_supervisor.html'
    success_url = reverse_lazy('supervis:lista_supervisores')
    
    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(Supervisor, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Supervisor'
        return context

    def form_valid(self, form):
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)


class SupervisorDeleteView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(Supervisor, id=user_id)
        user.delete()
        return redirect('supervis:lista_supervisores')
    

##############################################
#    Vistas para Escuelas por Supervisor     #
##############################################
class EscuelaListView(ListView):
    model = EscuelaSupervisor
    template_name = 'supervisores/lista_escuelas.html'
    context_object_name = 'escuelas'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        regional = self.request.GET.get('region')     

        if regional:
            queryset = queryset.filter(region_esc__iexact=regional)        
        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)        
        form = FiltroRegionalForm(self.request.GET or None, user=self.request.user)
        context['form']= form
        context['title'] = 'Listado de Escuelas'
        return context
    

class EscuelaCreateView(CreateView):
    model = EscuelaSupervisor
    form_class = EscuelaForm
    template_name = 'supervisores/crear_escuela.html'
    success_url = reverse_lazy('supervis:lista_escuelas')   
    
   

class EscuelaUpdateView(UpdateView):
    model = EscuelaSupervisor
    form_class = EscuelaForm
    template_name = 'supervisores/crear_escuela.html'
    success_url = reverse_lazy('supervis:lista_escuelas')
    
    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(EscuelaSupervisor, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Escuela'
        return context

    def form_valid(self, form):
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)
    
    

class EscuelasDeleteView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(EscuelaSupervisor, id=user_id)
        user.delete()
        return redirect('supervis:lista_escuelas')
    

#################################
#    Vistas para Regionales     #
#################################
class DirectorRegionalListView(ListView):
    model = DirectoresRegionales
    template_name = 'supervisores/lista_directores_regionales.html'
    context_object_name = 'directores'
    
    def get_queryset(self):
        return DirectoresRegionales.objects.all
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Directores Regionales'
        return context

class DirectorRegionalCreateView(CreateView):
    model = DirectoresRegionales
    fields = '__all__'
    template_name = 'supervisores/crear_director_regional.html'
    success_url = reverse_lazy('supervis:lista_directores_regionales')
    

class DirectorRegionalUpdateView(UpdateView):
    model = DirectoresRegionales
    fields = '__all__'
    template_name = 'supervisores/crear_director_regional.html'
    success_url = reverse_lazy('supervis:lista_directores_regionales')
    

class DirectorRegionalDeleteView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(DirectoresRegionales, id=user_id)
        user.delete()
        return redirect('supervis:eliminar_director_regional')