from django import forms
from django.core.exceptions import ValidationError
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
    
    def clean(self):
        cleaned = super().clean()
        fd = cleaned.get("fecha_desde")
        fh = cleaned.get("fecha_hasta")
        if fd and fh and fh < fd:
            raise ValidationError("La fecha hasta no puede ser menor que fecha desde")
        return cleaned