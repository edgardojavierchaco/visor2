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
    archivos = forms.FileField(
        required=False,
        label="Adjuntar archivos",
        # Quitamos el widget del constructor para evitar el ValueError de Django
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Respuesta
        fields = ['mensaje']
        widgets = {
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Escriba su respuesta...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inyectamos el atributo 'multiple' después de la inicialización
        # Esto evita la validación del __init__ del widget que causa el error
        self.fields['archivos'].widget.attrs.update({'multiple': True})