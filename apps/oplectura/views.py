from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from .models import RegDocporSeccion, RegEvaluacionFluidezLectora
from .forms import RegDocporSeccionEdicionForm, RegDocporSeccionForm, RegEvaluacionFluidezLectoraForm, FiltroEvaluacionForm, RegAlumnosFluidezLectoraForm, RegEvaluacionFluidezLectoraDirectoresForm
from .forms import RegAlumnosFluidezLectoraDirectorForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode

@method_decorator(login_required, name='dispatch')
class CreateRegDocporSeccionView(CreateView):
    model = RegDocporSeccion
    form_class = RegDocporSeccionForm
    template_name = 'oplectura/regdocporseccion.html'
    success_url = reverse_lazy('oplectura:cargar')  
    
    
    def form_valid(self, form):
        regdocporseccion = form.save(commit=False)
        regdocporseccion.save(user=self.request.user)
        regdocporseccion.save()
        return super().form_valid(form)
    

@method_decorator(login_required, name='dispatch')
class ListadoDocentesView(ListView):
    model=RegDocporSeccion
    template_name='oplectura/listadodocentes.html'
    context_object_name='docentesporseccion'
    
    def get_queryset(self):
        return RegDocporSeccion.objects.filter(cueanexo=self.request.user.username)
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Docentes'
        return context

#edición
class EditarDocentesView(UpdateView):
    model = RegDocporSeccion
    form_class = RegDocporSeccionEdicionForm
    template_name = 'oplectura/editardocentes.html'
    success_url = reverse_lazy('oplectura:listados')

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegDocporSeccion, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Validación'
        return context

    def form_valid(self, form):
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)

#eliminación
class EliminarDocentesView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(RegDocporSeccion, id=user_id)
        user.delete()
        return redirect('oplectura:listados')


def RegistrarEvaluacionLectora(request):
    if request.method == 'POST':
        form = RegEvaluacionFluidezLectoraForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('oplectura:evaluacion')  
    else:
        form = RegEvaluacionFluidezLectoraForm()
    return render(request, 'oplectura/registro_evaluacion_lectura.html', {'form': form})


#listado de alumnos
class ListadoEvaluacionLectora(ListView):
    model=RegEvaluacionFluidezLectora     
    template_name='oplectura/listadoevaluacionlectora.html' 
    context_object_name='evaluacionlectora'   
    print(context_object_name)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        cueanexo = self.request.GET.get('cueanexo')
        grado = self.request.GET.get('grado')
        seccion = self.request.GET.get('seccion')

        if cueanexo:
            queryset = queryset.filter(cueanexo=cueanexo)
        if grado:
            queryset = queryset.filter(grado=grado)
        if seccion:
            queryset = queryset.filter(seccion=seccion)

        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Alumnos'
        context['form']=FiltroEvaluacionForm(self.request.GET or None, user=self.request.user)
        return context


#edición evaluación alumnos
class EditarEvaluacionAlumnosView(UpdateView):
    model = RegEvaluacionFluidezLectora
    form_class = RegEvaluacionFluidezLectoraForm
    template_name = 'oplectura/editarevaluacionalumnos.html'
    

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Evaluación'
        return context

    def form_valid(self, form):
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)

    def get_success_url(self):
        # Usamos reverse_lazy para construir la URL de éxito
        base_url = reverse_lazy('oplectura:evaluacion')
        query_string = urlencode({'cueanexo': 0, 'grado': 'TERCERO', 'seccion': 'A'})
        return f"{base_url}?{query_string}"
    

#eliminación evaluación alumnos
class EliminarEvaluacionAlumnoView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)
        user.delete()
        
        # Construir la URL completa con los parámetros de consulta
        url = reverse('oplectura:evaluacion') + '?cueanexo=0&grado=TERCERO&seccion=A'
        
        return redirect(url)

# agregar alumno para el aplicador
class RegAlumnosFluidezLectoraCreateView(CreateView):
    model = RegEvaluacionFluidezLectora
    form_class = RegAlumnosFluidezLectoraForm
    template_name = 'oplectura/regalumnosfluidezlectora_form.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registro de Alumnos'
        return context
    
    def get_success_url(self):
        # Usamos reverse_lazy para construir la URL de éxito
        base_url = reverse_lazy('oplectura:evaluacion')
        query_string = urlencode({'cueanexo': 0, 'grado': 'TERCERO', 'seccion': 'A'})
        return f"{base_url}?{query_string}"
    
# agregar alumno por director
class RegAlumnosFluidezLectoraDirectorCreateView(CreateView):
    model = RegEvaluacionFluidezLectora
    form_class = RegAlumnosFluidezLectoraDirectorForm
    template_name = 'oplectura/regalumnosfluidezlectoradirector_form.html'
    success_url = reverse_lazy('oplectura:listado_alumnos')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registro de Alumnos'
        return context
    
    

#listado de alumnos para directores
class ListadoAlumnosDirectoresView(ListView):
    model=RegEvaluacionFluidezLectora     
    template_name='oplectura/listadoalumnosevaluacion.html' 
    context_object_name='evaluacionlectora'   
    print(context_object_name)
    
    def get_queryset(self):     
        queryset = super().get_queryset()   
        usuario = self.request.user

        if usuario:
            queryset = queryset.filter(cueanexo=usuario)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Alumnos'        
        return context

#edición de alumnos para directores
class EditarAlumnosDirectoresView(UpdateView):
    model = RegEvaluacionFluidezLectora
    form_class = RegEvaluacionFluidezLectoraDirectoresForm
    template_name = 'oplectura/editaralumnosdirectores.html'
    success_url = reverse_lazy('oplectura:listado_alumnos')  

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Alumno'
        return context

    def form_valid(self, form):
        # Simplemente llamamos al form_valid de la superclase
        return super().form_valid(form)
    
    

#eliminación alumnos directores
class EliminarEvaluacionAlumnoDirectoresView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)
        user.delete()
        return redirect('oplectura:listado_alumnos')
        


