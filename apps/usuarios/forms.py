from django.forms import ModelForm
from apps.usuarios.models import UsuariosVisualizador

class UsuariosForm(ModelForm):
    class Meta:
        model=UsuariosVisualizador
        fields='__all__'
        