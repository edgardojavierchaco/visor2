from django import forms
from .models import AsignacionSupervisorEscuela


class AsignacionForm(forms.ModelForm):

    class Meta:
        model = AsignacionSupervisorEscuela
        fields = [
            "cueanexo",
            "nom_est",
            "region_loc",
            "oferta",
            "localidad",
            "fecha_desde",
            "fecha_hasta",
        ]