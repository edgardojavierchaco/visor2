from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.conf import settings


class LoginFormView(LoginView):
    template_name = 'login/login.html'

    # --------------------------
    # 🎯 MAPA DE ROLES
    # --------------------------
    ROLE_REDIRECTS = {
        'Administrador': 'archivos:portada_gestor',
        'Gestor': 'archivos:portada_gestor',

        # Funcionarios
        'Ministro': 'funcionario:portada_func',
        'Subsecretario': 'funcionario:portada_func',
        'Director General': 'funcionario:portada_func',
        'Director de Nivel': 'funcionario:portada_func',

        # Otros
        'Director': 'directores:institucional',
        'Regional': 'oplectura:portada_regional',
        'Supervisor': 'operativo:portada_supervisor',
        'Renpe': 'archivos:portada_gestor_renpe',
        'Evaluacion': 'oplectura:portada_eval',
        'Aplicador': 'oplectura:evaluacion',
        'Director_Privada': 'directores:institucional',
        'DirGral_Privada': 'privada:dashboard',
    }

    # --------------------------
    # 🧠 MAPA DE CATEGORÍAS
    # --------------------------
    CATEGORY_REDIRECTS = {
        'all': 'archivos:portada_gestor',
        'regional': 'oplectura:portada_regional',
        'propio': 'directores:institucional',
        'nivel': 'funcionario:portada_func',
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar Sesión'
        return context

    # --------------------------
    # 🚀 RESOLVER REDIRECCIÓN
    # --------------------------
    def resolve_redirect_url(self, user):
        if not hasattr(user, 'perfil') or not user.perfil.rol:
            return settings.LOGIN_REDIRECT_URL

        rol = user.perfil.rol.nombre
        categoria = user.perfil.rol.categoria_acceso

        # 🎯 1. PRIORIDAD: ROL
        if rol in self.ROLE_REDIRECTS:
            url_name = self.ROLE_REDIRECTS[rol]

            # caso especial Aplicador (querystring)
            if rol == 'Aplicador':
                return reverse(url_name) + '?cueanexo=0&grado=TERCERO&seccion=A'

            return reverse(url_name)

        # 🧠 2. FALLBACK: CATEGORÍA
        if categoria in self.CATEGORY_REDIRECTS:
            return reverse(self.CATEGORY_REDIRECTS[categoria])

        return settings.LOGIN_REDIRECT_URL

    def get_success_url(self):
        user = self.request.user

        if not user.is_authenticated or not user.is_staff:
            return reverse('login')

        return self.resolve_redirect_url(user)

    def form_valid(self, form):
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )

        if user is not None:
            login(self.request, user)

            if user.is_staff:
                return JsonResponse({
                    'success': True,
                    'redirect_url': self.get_success_url()
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Aún no estás autorizado.'
                })

        return JsonResponse({
            'success': False,
            'message': 'Credenciales incorrectas.'
        })

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'message': 'Credenciales incorrectas.',
            'template': 'login/login.html'
        })

    def post(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            form = self.get_form()
            return self.form_valid(form) if form.is_valid() else self.form_invalid(form)
        return super().post(request, *args, **kwargs)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('dash:portada')
    
    # Permitir GET además de POST
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)