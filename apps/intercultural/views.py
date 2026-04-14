from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import Alumnos_Bilingue, EscuelasBilingues
from .forms import Alumno_BilingueForm, Nivel_curso
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

def buscar_escuelas(request):
    term = request.GET.get('term', '')
    if term:
        # Filtra las escuelas por el término de búsqueda
        escuelas = EscuelasBilingues.objects.filter(cueanexo__icontains=term)  # Filtra por cueanexo
        results = [{
            'id': escuela.id,
            'text': escuela.cueanexo,  # Lo que se muestra en el autocompletado
            'nom_est': escuela.nom_est  # Lo que se usará para llenar el campo de escuela
        } for escuela in escuelas]
    else:
        results = []

    return JsonResponse(results, safe=False)

def cargar_alumno_bilingue(request):
    if request.method == "POST":
        form = Alumno_BilingueForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("lista_alumnos")  # Redirige a la lista de alumnos después de guardar
    else:
        form = Alumno_BilingueForm()

    return render(request, "intercultural/alumno_bilingue_form.html", {"form": form})

def filtrar_cursos(request):
    nivel = request.GET.get('nivel')
    cursos = Nivel_curso.objects.filter(nivel=nivel)  # Filtrar los cursos según el nivel
    results = [{'id': curso.id, 'curso': curso.curso} for curso in cursos]
    return JsonResponse(results, safe=False)


class AlumnosBilingueListView(LoginRequiredMixin, ListView):
    model = Alumnos_Bilingue
    template_name = 'intercultural/alumnos/list.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):       
        return Alumnos_Bilingue.objects.filter(cueanexo=self.request.user.username)
        

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
        context['list_url'] = reverse_lazy('intercultural:alumnos_list')
        context['update_url'] = reverse_lazy('intercultural:alumnos_update', args=[0]) 
        context['entity'] = 'Alumnos Bilingües'
        return context


class AlumnosBilingueListView2(LoginRequiredMixin, ListView):
    model = Alumnos_Bilingue
    template_name = 'intercultural/alumnos/list_comun.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):       
        return Alumnos_Bilingue.objects.filter(cueanexo=self.request.user.username)
        

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
        context['create_url'] = reverse_lazy('intercultural:alumnos_create_comun')
        context['list_url'] = reverse_lazy('intercultural:alumnos_list')
        context['update_url'] = reverse_lazy('intercultural:alumnos_update', args=[0]) 
        context['entity'] = 'Alumnos Bilingües'
        return context

class AlumnosBilingueCreateView(LoginRequiredMixin, CreateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create.html'
    success_url = reverse_lazy('intercultural:alumnos_list')
    #permission_required = 'apps.add_client'
    url_redirect = success_url
    
    def form_valid(self, form):
        form.instance.cueanexo = self.request.user.username
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)    
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Carga Cantidad Alumnos'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['cueanexo'] = self.request.user.username
        return context


class AlumnosBilingueCreateView2(LoginRequiredMixin, CreateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create_comun.html'
    success_url = reverse_lazy('intercultural:alumnos_list')
    #permission_required = 'apps.add_client'
    url_redirect = success_url
    
    def form_valid(self, form):
        form.instance.cueanexo = self.request.user.username
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'add':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)    
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Carga Cantidad Alumnos'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['cueanexo'] = self.request.user.username
        return context



class AlumnosBilingueUpdateView(LoginRequiredMixin, UpdateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create.html'
    success_url = reverse_lazy('intercultural:alumnos_list')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición Cantidad de Alumnos'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['cueanexo'] = self.request.user.username
        return context


class AlumnosBilingueUpdateView2(LoginRequiredMixin, UpdateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create_comun.html'
    success_url = reverse_lazy('intercultural:alumnos_list_comun')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'edit':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición Cantidad de Alumnos'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['cueanexo'] = self.request.user.username
        return context


class AlumnosBilingueDeleteView(LoginRequiredMixin, DeleteView):
    model = Alumnos_Bilingue
    template_name = 'intercultural/alumnos/delete.html'
    success_url = reverse_lazy('intercultural:alumnos_list')
    #permission_required = 'apps.delete_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.object.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación Cantidad de Alumnos Bilingües'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        return context


class AlumnosBilingueDeleteView2(LoginRequiredMixin, DeleteView):
    model = Alumnos_Bilingue
    template_name = 'intercultural/alumnos/delete.html'
    success_url = reverse_lazy('intercultural:alumnos_list_comun')
    #permission_required = 'apps.delete_client'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.object.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación Cantidad de Alumnos Bilingües'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        return context

