from attr import fields
from django.forms import ModelForm
from apps.usuarios.models import UsuariosVisualizador
    
class UsuariosForm(ModelForm):
    class Meta:
        model=UsuariosVisualizador
        fields=['username','password','apellido','nombres','correo','telefono','nivelacceso','activo','is_staff','is_superuser']
