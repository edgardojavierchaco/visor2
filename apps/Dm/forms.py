from django import forms

class FormMensajes(forms.Form):
    mensaje=forms.CharField(widget=forms.Textarea(attrs={
        'class': 'formulario_ms',
        'placeholder':'Escribe tu mensaje'
    }
    ))

class CanalEleccionForm(forms.Form):
    CANALES = [
        ('SIE', 'SIE'),
        ('RelevamientoAnual', 'Relevamiento Anual'),
    ]
    
    canal = forms.ChoiceField(choices=CANALES, label="Selecciona un canal", widget=forms.RadioSelect)

