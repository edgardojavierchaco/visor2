from django import forms
from .models import Consulta, Respuesta


class ConsultaForm(forms.ModelForm):

    class Meta:
        model = Consulta
        fields = ["asunto", "mensaje", "categoria"]

        widgets = {
            "asunto": forms.TextInput(attrs={"class": "form-control"}),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "categoria": forms.Select(attrs={"class": "form-control"}),
        }
        
class RespuestaForm(forms.ModelForm):

    class Meta:
        model = Respuesta
        fields = ["mensaje"]
        widgets = {
            "mensaje": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Escriba su respuesta..."
                }
            )
        }