# views.py
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .models import Datos_Personal_Cenpe
from .forms import DatosPersonalCenpeForm
from django.contrib.auth.mixins import LoginRequiredMixin

class DatosPersonalCenpeCreateView(LoginRequiredMixin, CreateView):
    model = Datos_Personal_Cenpe
    form_class = DatosPersonalCenpeForm
    template_name = 'cenpe/crear_datos_personales.html'
    success_url = reverse_lazy('home')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  # Establecer el username del usuario logueado
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)