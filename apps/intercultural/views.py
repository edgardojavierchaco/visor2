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
from apps.bnhpersonas_old.utils import get_ofertas_usuario
from .middleware import UserCueanexoMiddleware


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

    def get_queryset(self):
        cueanexos = getattr(self.request, 'cueanexos_validos', set())

        return Alumnos_Bilingue.objects.filter(
            cueanexo__in=cueanexos
        )

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}

        try:
            action = request.POST.get('action')

            if action == 'searchdata':
                data = [
                    i.toJSON()
                    for i in self.get_queryset()
                ]
            else:
                data['error'] = 'Acción inválida'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'title': 'Listado de Alumnos Bilingües cargados',
            'create_url': reverse_lazy('intercultural:alumnos_create'),
            'list_url': reverse_lazy('intercultural:alumnos_list'),
            'update_url': reverse_lazy('intercultural:alumnos_update', args=[0]),
            'entity': 'Alumnos Bilingües'
        })

        return context


class AlumnosBilingueListView2(LoginRequiredMixin, ListView):
    model = Alumnos_Bilingue
    template_name = 'intercultural/alumnos/list.html'

    def get_queryset(self):
        cueanexos = getattr(self.request, 'cueanexos_validos', set())

        return Alumnos_Bilingue.objects.filter(
            cueanexo__in=cueanexos
        )

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}

        try:
            action = request.POST.get('action')

            if action == 'searchdata':
                data = [
                    i.toJSON()
                    for i in self.get_queryset()
                ]
            else:
                data['error'] = 'Acción inválida'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'title': 'Listado de Alumnos Bilingües cargados',
            'create_url': reverse_lazy('intercultural:alumnos_create'),
            'list_url': reverse_lazy('intercultural:alumnos_list'),
            'update_url': reverse_lazy('intercultural:alumnos_update', args=[0]),
            'entity': 'Alumnos Bilingües'
        })

        return context
    

class AlumnosBilingueCreateView(LoginRequiredMixin, CreateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create.html'
    success_url = reverse_lazy('intercultural:alumnos_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cueanexos = getattr(self.request, 'cueanexos_validos', set())

        context.update({
            'title': 'Carga Cantidad Alumnos',
            'entity': 'Alumnos Bilingües',
            'list_url': self.success_url,
            'action': 'add',
            'cueanexos_list': list(cueanexos),
            'cueanexo_unico': list(cueanexos)[0] if len(cueanexos) == 1 else None,
        })

        return context

    def post(self, request, *args, **kwargs):

        try:
            action = request.POST.get('action')

            if action != 'add':
                return JsonResponse({'error': 'Acción inválida'})

            cueanexo = str(request.POST.get('cueanexo', '')).strip()

            if not cueanexo:
                return JsonResponse({'error': 'No se recibió CUE/Anexo'})

            cueanexos_validos = getattr(request, 'cueanexos_validos', set())

            print("RECIBIDO:", cueanexo)
            print("VALIDOS:", cueanexos_validos)

            if cueanexo not in cueanexos_validos:
                return JsonResponse({
                    'error': 'CUE/Anexo no autorizado',
                    'recibido': cueanexo,
                    'validos': list(cueanexos_validos)
                })

            form = self.get_form()

            if not form.is_valid():
                return JsonResponse({'error': form.errors})

            obj = form.save(commit=False)
            obj.cueanexo = cueanexo
            obj.save()

            return JsonResponse({'success': True, 'id': obj.id})

        except Exception as e:
            return JsonResponse({'error': str(e)})    


class AlumnosBilingueCreateView2(LoginRequiredMixin, CreateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create.html'
    success_url = reverse_lazy('intercultural:alumnos_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cueanexos = getattr(self.request, 'cueanexos_validos', set())

        context.update({
            'title': 'Carga Cantidad Alumnos',
            'entity': 'Alumnos Bilingües',
            'list_url': self.success_url,
            'action': 'add',
            'cueanexos_list': list(cueanexos),
            'cueanexo_unico': list(cueanexos)[0] if len(cueanexos) == 1 else None,
        })

        return context

    def post(self, request, *args, **kwargs):

        try:
            action = request.POST.get('action')

            if action != 'add':
                return JsonResponse({'error': 'Acción inválida'})

            cueanexo = str(request.POST.get('cueanexo', '')).strip()

            if not cueanexo:
                return JsonResponse({'error': 'No se recibió CUE/Anexo'})

            cueanexos_validos = getattr(request, 'cueanexos_validos', set())

            print("RECIBIDO:", cueanexo)
            print("VALIDOS:", cueanexos_validos)

            if cueanexo not in cueanexos_validos:
                return JsonResponse({
                    'error': 'CUE/Anexo no autorizado',
                    'recibido': cueanexo,
                    'validos': list(cueanexos_validos)
                })

            form = self.get_form()

            if not form.is_valid():
                return JsonResponse({'error': form.errors})

            obj = form.save(commit=False)
            obj.cueanexo = cueanexo
            obj.save()

            return JsonResponse({'success': True, 'id': obj.id})

        except Exception as e:
            return JsonResponse({'error': str(e)})      
        
        
class AlumnosBilingueUpdateView(LoginRequiredMixin, UpdateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create.html'
    success_url = reverse_lazy('intercultural:alumnos_list')
    url_redirect = success_url

    # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # =========================
    # CONTEXTO (MISMA LÓGICA QUE CREATE)
    # =========================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ofertas = get_ofertas_usuario(self.request.user)
        cueanexos = list(ofertas.values_list('cueanexo', flat=True))

        context['title'] = 'Edición Cantidad de Alumnos'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        context['action'] = 'edit'

        context['cueanexos_list'] = cueanexos
        context['cueanexo_unico'] = cueanexos[0] if len(cueanexos) == 1 else None

        return context

    # =========================
    # POST AJAX
    # =========================
    def post(self, request, *args, **kwargs):
        data = {}

        try:
            action = request.POST.get('action')

            if action == 'edit':

                form = self.get_form()
                cueanexo = request.POST.get('cueanexo')

                # 🔥 cueanexos válidos del usuario
                cueanexos_validos = list(
                    get_ofertas_usuario(request.user)
                    .values_list('cueanexo', flat=True)
                )

                # =========================
                # VALIDACIÓN SEGURIDAD
                # =========================
                if not cueanexo:
                    return JsonResponse({'error': 'Debe seleccionar un CUE/Anexo'})

                if cueanexo not in cueanexos_validos:
                    return JsonResponse({'error': 'CUE/Anexo no autorizado'})

                # =========================
                # VALIDAR FORM
                # =========================
                if form.is_valid():
                    form.instance.cueanexo = cueanexo
                    obj = form.save()

                    data = {
                        'success': True,
                        'id': obj.id
                    }
                else:
                    data['error'] = form.errors

            else:
                data['error'] = 'No ha ingresado a ninguna opción'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data)


class AlumnosBilingueUpdateView2(LoginRequiredMixin, UpdateView):
    model = Alumnos_Bilingue
    form_class = Alumno_BilingueForm
    template_name = 'intercultural/alumnos/create.html'
    success_url = reverse_lazy('intercultural:alumnos_list')
    url_redirect = success_url

    # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    # =========================
    # CONTEXTO (MISMA LÓGICA QUE CREATE)
    # =========================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ofertas = get_ofertas_usuario(self.request.user)
        cueanexos = list(ofertas.values_list('cueanexo', flat=True))

        context['title'] = 'Edición Cantidad de Alumnos'
        context['entity'] = 'Alumnos Bilingües'
        context['list_url'] = self.success_url
        context['action'] = 'edit'

        context['cueanexos_list'] = cueanexos
        context['cueanexo_unico'] = cueanexos[0] if len(cueanexos) == 1 else None

        return context

    # =========================
    # POST AJAX
    # =========================
    def post(self, request, *args, **kwargs):
        data = {}

        try:
            action = request.POST.get('action')

            if action == 'edit':

                form = self.get_form()
                cueanexo = request.POST.get('cueanexo')

                # 🔥 cueanexos válidos del usuario
                cueanexos_validos = list(
                    get_ofertas_usuario(request.user)
                    .values_list('cueanexo', flat=True)
                )

                # =========================
                # VALIDACIÓN SEGURIDAD
                # =========================
                if not cueanexo:
                    return JsonResponse({'error': 'Debe seleccionar un CUE/Anexo'})

                if cueanexo not in cueanexos_validos:
                    return JsonResponse({'error': 'CUE/Anexo no autorizado'})

                # =========================
                # VALIDAR FORM
                # =========================
                if form.is_valid():
                    form.instance.cueanexo = cueanexo
                    obj = form.save()

                    data = {
                        'success': True,
                        'id': obj.id
                    }
                else:
                    data['error'] = form.errors

            else:
                data['error'] = 'No ha ingresado a ninguna opción'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data)


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

