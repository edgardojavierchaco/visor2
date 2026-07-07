# apps/especial/forms.py
# -*- coding: utf-8 -*-

import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField

from .models import (
    AlumnoSeccion,
    CatalogoTipoEstructuraEspecial,
    CatalogoTipoRangoEtario,
    EspecialCiclo,
    ModalidadDictadoTipo,
    SeccionEspecial,
    seccion_tipo,
    TurnoTipo,
    normalizar_cueanexo,
    seccion_tipo,
)


class EspecialBusquedaAlumnoForm(forms.Form):
    """Formulario de búsqueda de alumno por CUIL."""
    cuil = forms.CharField(
        max_length=13,
        required=True,
        label="CUIL",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej: 20-12345678-9",
            "pattern": r"\d{11}|[\d-]{13}",
        }),
    )

    def clean_cuil(self):
        cuil = re.sub(r"\D", "", self.cleaned_data.get("cuil", ""))
        if len(cuil) != 11:
            raise ValidationError("El CUIL debe tener 11 dígitos.")
        return cuil


class EspecialSeccionForm(forms.ModelForm):
    """Formulario de creación/edición de sección de Educación Especial."""
    class Meta:
        model = SeccionEspecial
        fields = [
            "cd_tipo_seccion",
            "tipo_estructura_especial",
            "nombre_seccion",
            "descripcion",
            "capacidad_total",
            "turno",
            "rango_etario",
            "modalidad",
            "lugar_dictado",
            "estado",
        ]
        labels = {
            "cd_tipo_seccion": "Tipo de sección",
            "tipo_estructura_especial": "Tipo de estructura especial",
            "rango_etario": "Rango etario",
            "modalidad": "Modalidad de dictado",
            "turno": "Turno",
            "nombre_seccion": "Nombre de la sección",
            "capacidad_total": "Capacidad total",
            "lugar_dictado": "Lugar de dictado",
            "estado": "Estado",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "lugar_dictado": forms.TextInput(attrs={"class": "form-control"}),
            "nombre_seccion": forms.TextInput(attrs={"class": "form-control"}),
            "capacidad_total": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "cd_tipo_seccion": forms.Select(attrs={"class": "form-select"}),
            "tipo_estructura_especial": forms.Select(attrs={"class": "form-select"}),
            "turno": forms.Select(attrs={"class": "form-select"}),
            "rango_etario": forms.Select(attrs={"class": "form-select"}),
            "modalidad": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, ciclo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ciclo = ciclo

        # Mapeo de campos y sus querysets
        campos_catalogo = {
            "cd_tipo_seccion": seccion_tipo.objects.all(),
            "tipo_estructura_especial": CatalogoTipoEstructuraEspecial.objects.all(),
            "turno": TurnoTipo.objects.all(),
            "rango_etario": CatalogoTipoRangoEtario.objects.all(),
            "modalidad": ModalidadDictadoTipo.objects.all(),
        }

        for nombre_campo, queryset in campos_catalogo.items():
            field = self.fields.get(nombre_campo)
            if isinstance(field, ModelChoiceField):
                field.queryset = queryset
                field.label_from_instance = lambda obj: getattr(obj, "descripcion", str(obj))

    def clean_capacidad_total(self):
        capacidad = self.cleaned_data.get("capacidad_total")
        if capacidad is not None and capacidad < 1:
            raise ValidationError("La capacidad debe ser mayor a 0.")
        return capacidad

    def clean_nombre_seccion(self):
        nombre = self.cleaned_data.get("nombre_seccion", "").strip()
        if not nombre:
            raise ValidationError("El nombre de la sección es obligatorio.")
        return nombre

    def save(self, commit=True):
        seccion = super().save(commit=False)
        if self.ciclo:
            seccion.ciclo = self.ciclo
        if commit:
            seccion.save()
        return seccion


class EspecialCicloForm(forms.ModelForm):
    """Formulario de creación de ciclo lectivo."""
    class Meta:
        model = EspecialCiclo
        fields = ["anio", "descripcion", "fecha_inicio", "fecha_fin", "activo", "actual"]
        labels = {
            "anio": "Año",
            "descripcion": "Descripción",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de fin",
            "activo": "Activo",
            "actual": "Ciclo actual",
        }
        widgets = {
            "anio": forms.NumberInput(attrs={"class": "form-control", "min": 1900, "max": 2100}),
            "descripcion": forms.TextInput(attrs={"class": "form-control"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "actual": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def save(self, user=None, commit=True):
        ciclo = super().save(commit=False)
        if user:
            ciclo.creado_por = user
            ciclo.actualizado_por = user
        if commit:
            ciclo.save()
        return ciclo