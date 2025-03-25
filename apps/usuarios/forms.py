from django import forms
from django.forms import ModelForm

from apps.usuarios.models import UsuariosVisualizador

class UsuariosForm(ModelForm):
    class Meta:
        model=UsuariosVisualizador
        fields=['username','password','apellido','nombres','correo','telefono','nivelacceso','activo','is_staff','is_superuser']

    def clean_username(self):
        username = self.cleaned_data['username']
        if not username.startswith('22') or not username.isdigit() or len(username) != 9:
            raise forms.ValidationError('El nombre de usuario debe comenzar con 22 y tener una extensión de 9 dígitos.')
        return username
    
    def save(self,request,*args,**kwargs):
        data={}
        form=super()
        try:
            if form.is_valid():
                form.save()
            else:
                data['error']=form.errors
        except Exception as e:
            data['error']=str(e)
        return data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asignar mensaje de error personalizado para el campo 'username'
        self.fields['username'].error_messages = {
            'unique': 'Ese usuario ya existe.'
        }