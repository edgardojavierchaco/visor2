# apps/especial/forms.py
# -*- coding: utf-8 -*-
import re
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField
from django.utils import timezone
from .models import (
    AlumnoSeccion,
    CatalogoTipoEstructuraEspecial,
    CatalogoTipoRangoEtario,
    EspecialCiclo,
    EspecialAlumnoBanco,
    EspecialDocenteBanco,
    DocenteSeccion,
    ModalidadDictadoTipo,
    PADRON_DB_ALIAS,
    EspecialPadronOferta,
    SeccionEspecial,
    SeccionTipo,
    TurnoTipo,
    normalizar_cueanexo,
    solo_digitos,
)

def _aplicar_clases_bootstrap(field):
    widget = field.widget
    clases = widget.attrs.get("class", "")
    if isinstance(widget, forms.CheckboxSelectMultiple):
        return
    if isinstance(widget, forms.CheckboxInput):
        widget.attrs["class"] = f"{clases} form-check-input".strip()
        return
    if isinstance(widget, forms.Textarea):
        nueva = "form-control"
    elif isinstance(widget, forms.Select):
        nueva = "form-select"
    else:
        nueva = "form-control"
    widget.attrs["class"] = f"{clases} {nueva}".strip()

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

class EspecialBusquedaDocenteForm(forms.Form):
    """Formulario de búsqueda de docente por CUIL."""
    cuil = forms.CharField(
        max_length=13,
        required=True,
        label="CUIL del Docente",
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


class EspecialMatriculaCompartidaForm(forms.Form):
    """Normaliza y valida la matrícula compartida contra el padrón general."""

    cueanexo_matricula_compartida = forms.CharField(
        max_length=30,
        required=False,
    )

    def __init__(
        self,
        *args,
        cueanexo_actual="",
        matricula_compartida_habilitada=False,
        padron_queryset=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.cueanexo_actual = normalizar_cueanexo(cueanexo_actual)
        self.matricula_compartida_habilitada = bool(matricula_compartida_habilitada)
        self.padron_queryset = (
            padron_queryset
            if padron_queryset is not None
            else EspecialPadronOferta.objects.using(PADRON_DB_ALIAS)
        )
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean(self):
        cleaned_data = super().clean()
        cueanexo_raw = cleaned_data.get("cueanexo_matricula_compartida") or ""
        cueanexo = normalizar_cueanexo(
            cueanexo_raw
        )

        if not self.matricula_compartida_habilitada:
            if str(cueanexo_raw).strip():
                self.add_error(
                    "cueanexo_matricula_compartida",
                    "La matrícula compartida no está habilitada para este CUE-Anexo.",
                )
            cleaned_data["matricula_compartida"] = None
            return cleaned_data

        if not cueanexo:
            self.add_error(
                "cueanexo_matricula_compartida",
                "Este establecimiento tiene oferta Integración y requiere indicar el CUE-Anexo de matrícula compartida.",
            )
            return cleaned_data

        if cueanexo == self.cueanexo_actual:
            self.add_error(
                "cueanexo_matricula_compartida",
                "El CUE-Anexo asociado no puede ser igual al CUE-Anexo actual.",
            )
            return cleaned_data

        if not self.padron_queryset.filter(cueanexo=cueanexo).exists():
            self.add_error(
                "cueanexo_matricula_compartida",
                "El CUE-Anexo asociado no existe en el padrón general.",
            )
            return cleaned_data

        cleaned_data["matricula_compartida"] = cueanexo
        return cleaned_data


class EspecialBajaMotivoForm(forms.Form):
    """Formulario de motivo obligatorio para la baja del banco Especial."""

    motivo_baja = forms.CharField(
        label="Motivo de baja",
        max_length=EspecialAlumnoBanco._meta.get_field("motivo_baja").max_length,
        required=True,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean_motivo_baja(self):
        motivo = (self.cleaned_data.get("motivo_baja") or "").strip()
        if not motivo:
            raise forms.ValidationError("Debe indicar el motivo de la baja.")
        return motivo


class EspecialBajaDocenteForm(forms.Form):
    """Formulario de baja general y traslado de un docente del banco Especial."""

    MOTIVOS = (
        ("fallecimiento", "Fallecimiento"),
        ("finalizacion", "Finalización"),
        ("renuncia", "Renuncia"),
        ("jubilacion", "Jubilación"),
        ("retiro", "Retiro"),
        ("traslado", "Traslado"),
    )

    motivo_baja = forms.ChoiceField(label="Motivo de baja", choices=MOTIVOS)
    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    cueanexo_destino = forms.CharField(
        label="CUE-Anexo de destino",
        required=False,
        max_length=9,
        widget=forms.TextInput(attrs={
            "class": "form-control cef-docente-cueanexo-destino",
            "maxlength": "9",
            "inputmode": "numeric",
            "pattern": "[0-9]{9}",
            "placeholder": "Ej.: 220015500",
        }),
    )
    ciclo_destino = forms.ModelChoiceField(
        label="Ciclo destino",
        required=False,
        queryset=EspecialCiclo.objects.filter(cerrado=False).order_by("anio"),
    )

    def __init__(self, *args, cueanexo_origen="", ciclo_origen=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cueanexo_origen = normalizar_cueanexo(cueanexo_origen)
        self.ciclo_origen = ciclo_origen
        siguiente = (
            EspecialCiclo.objects.filter(anio=ciclo_origen.anio + 1).first()
            if ciclo_origen
            else None
        )
        if siguiente and not self.is_bound:
            self.fields["ciclo_destino"].initial = siguiente.pk
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean_cueanexo_destino(self):
        destino = (self.cleaned_data.get("cueanexo_destino") or "").strip()
        if destino and not re.fullmatch(r"[0-9]{9}", destino):
            raise forms.ValidationError("El CUE-Anexo debe contener exactamente 9 dígitos numéricos.")
        return destino

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("motivo_baja") != "traslado":
            cleaned_data["cueanexo_destino"] = ""
            cleaned_data["ciclo_destino"] = None
            return cleaned_data
        destino = cleaned_data.get("cueanexo_destino")
        ciclo_destino = cleaned_data.get("ciclo_destino")
        if not destino:
            self.add_error("cueanexo_destino", "Indicá el CUE-Anexo de destino.")
        elif destino == self.cueanexo_origen:
            self.add_error("cueanexo_destino", "El destino debe ser distinto del origen.")
        elif not EspecialPadronOferta.objects.using(PADRON_DB_ALIAS).filter(
            cueanexo=destino
        ).exists():
            self.add_error("cueanexo_destino", "El CUE-Anexo ingresado no existe.")
        if not ciclo_destino:
            self.add_error("ciclo_destino", "Seleccioná el ciclo destino.")
        elif self.ciclo_origen and ciclo_destino.anio <= self.ciclo_origen.anio:
            self.add_error("ciclo_destino", "El ciclo destino debe ser posterior al de origen.")
        return cleaned_data


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
            "cd_tipo_seccion": SeccionTipo.objects.all(),
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
        
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def save(self, user=None, commit=True):
        ciclo = super().save(commit=False)
        if user:
            ciclo.creado_por = user
            ciclo.actualizado_por = user
        if commit:
            ciclo.save()
        return ciclo

class EspecialInscripcionForm(forms.ModelForm):
    """Formulario para inscribir/alumno a sección (AlumnoSeccion)."""
    class Meta:
        model = AlumnoSeccion
        fields = [
            "estado",
            "fecha_inscripcion",
            "fecha_baja",
            "motivo_baja",
            "observaciones",
        ]
        widgets = {
            "fecha_inscripcion": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fecha_baja": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "estado": "Estado",
            "fecha_inscripcion": "Fecha de inscripción",
            "fecha_baja": "Fecha de baja",
            "motivo_baja": "Motivo de baja",
            "observaciones": "Observaciones",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not getattr(self.instance, "pk", None):
            self.fields["fecha_inscripcion"].initial = timezone.localdate
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

class EspecialDocenteSeccionForm(forms.ModelForm):
    """Formulario para asignar docente a sección."""
    class Meta:
        model = DocenteSeccion
        fields = [
            "rol",
            "estado",
            "fecha_desde",
            "fecha_hasta",
            "observaciones",
        ]
        widgets = {
            "fecha_desde": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fecha_hasta": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "rol": "Rol en la sección",
            "estado": "Estado en esta sección",
            "fecha_desde": "Fecha de asignación",
            "fecha_hasta": "Fecha de finalización",
            "observaciones": "Observaciones",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rol_sin_cambios = False
        
        if not self.is_bound and not getattr(self.instance, "pk", None):
            self.fields["fecha_desde"].initial = timezone.localdate
            
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get("rol")
        self.rol_sin_cambios = bool(
            self.instance.pk and rol and rol == self.instance.rol
        )
        return cleaned_data
