from django import forms

"""
Este módulo define un formulario de filtrado que permite seleccionar niveles, localidades y establecimientos. 
Está diseñado para ser utilizado con campos de selección dinámicamente cargados.

Clases:
    FiltroFormularioRadio: Formulario con tres campos de selección (nivel, localidad, establecimiento) que 
                           se rellenan dinámicamente con opciones desde el servidor.
"""

class FiltroFormularioRadio(forms.Form):
    """
    Formulario para filtrar por nivel, localidad y establecimiento.

    Atributos:
        nivel (ChoiceField): Campo de selección para los niveles, que se rellena dinámicamente.
        localidad (ChoiceField): Campo de selección para las localidades, que se rellena dinámicamente.
        establecimiento (ChoiceField): Campo de selección para los establecimientos, que se rellena dinámicamente.
    """
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
