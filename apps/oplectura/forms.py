from attr import fields
from django import forms
from .models import DocenteGradoSeccion

class CargarDocenteGradoSeccion(forms.ModelForm):
    class Meta:
        model = DocenteGradoSeccion
        fields= '__all__'
