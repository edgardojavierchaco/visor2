from django import forms

class FiltroFormularioRadio(forms.Form):
    nivel = forms.ChoiceField(
        choices=[],  # Las opciones se cargan dinámicamente
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'nivel-select'})
    )
    localidad = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'localidad-select'})
    )
    establecimiento = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'establecimiento-select'})
    )
