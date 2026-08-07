# -*- coding: utf-8 -*-

import re

from django import forms
from django.utils import timezone

from .models import (
    CefActividad,
    CefBeneficioSinoTipo,
    CefCiclo,
    CefDatosRelevamiento,
    CefDiaSemana,
    CefDocenteGrupo,
    CefEspacioComedorTipo,
    CefEstadoMaterialTipo,
    CefFuenteFinanciamientoTipo,
    CefGrupo,
    CefInscripcion,
    CefInventarioMaterial,
    CefInventarioMaterialEstado,
    CefMaterial,
    CefNivelActividad,
    CefOrientacionTipo,
    CefPrestacionTipo,
    CefRangoEtario,
    CefTurno,
)


def _solo_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _texto_normalizado(valor):
    texto = str(valor or "").strip().lower()
    return texto.translate(str.maketrans("áéíóúüñ", "aeiouun"))


def _queryset_activos(modelo):
    return modelo.objects.filter(activo=True)


def _normalizar_placeholder_vacio(field):
    if (
        isinstance(field, forms.ModelChoiceField)
        and getattr(field, "empty_label", None) == "---------"
    ):
        field.empty_label = "Seleccione"
        return

    if isinstance(field, forms.ChoiceField) and not isinstance(
        field,
        forms.ModelChoiceField,
    ):
        choices = list(field.choices)
        if (
            choices
            and choices[0][0] in ("", None)
            and str(choices[0][1]) == "---------"
        ):
            choices[0] = (choices[0][0], "Seleccione")
            field.choices = choices


def _aplicar_clases_bootstrap(field):
    _normalizar_placeholder_vacio(field)
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
        if not isinstance(widget, forms.SelectMultiple):
            widget.attrs["data-cef-select"] = "true"
    else:
        nueva = "form-control"

    widget.attrs["class"] = f"{clases} {nueva}".strip()


class CefCicloForm(forms.Form):
    anio = forms.IntegerField(
        label="Año",
        min_value=1900,
        max_value=2100,
    )
    descripcion = forms.CharField(
        label="Descripción",
        required=False,
        max_length=120,
    )
    fecha_inicio = forms.DateField(
        label="Fecha inicio (referencia)",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    fecha_fin = forms.DateField(
        label="Fecha fin (referencia)",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    activo = forms.BooleanField(
        label="Activo",
        required=False,
        initial=True,
    )
    actual = forms.BooleanField(
        label="Marcar como ciclo actual",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean_anio(self):
        anio = self.cleaned_data["anio"]
        if CefCiclo.objects.filter(anio=anio).exists():
            raise forms.ValidationError("Ya existe un ciclo con ese año.")
        return anio

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error(
                "fecha_fin",
                "La fecha de fin no puede ser anterior a la fecha de inicio.",
            )

        if cleaned_data.get("actual"):
            cleaned_data["activo"] = True

        return cleaned_data

    def save(self, user=None):
        return CefCiclo.objects.create(
            anio=self.cleaned_data["anio"],
            descripcion=self.cleaned_data.get("descripcion", ""),
            fecha_inicio=self.cleaned_data.get("fecha_inicio"),
            fecha_fin=self.cleaned_data.get("fecha_fin"),
            activo=self.cleaned_data.get("activo", False),
            actual=self.cleaned_data.get("actual", False),
            creado_por=user,
            actualizado_por=user,
        )


class CefCicloEdicionForm(forms.ModelForm):
    class Meta:
        model = CefCiclo
        fields = ["descripcion", "fecha_fin"]
        widgets = {
            "fecha_fin": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }
        labels = {
            "descripcion": "Descripción",
            "fecha_fin": "Fecha fin (referencia)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean_fecha_fin(self):
        fecha_fin = self.cleaned_data.get("fecha_fin")
        if (
            self.instance.fecha_inicio
            and fecha_fin
            and fecha_fin < self.instance.fecha_inicio
        ):
            raise forms.ValidationError(
                "La fecha de fin no puede ser anterior a la fecha de inicio."
            )
        return fecha_fin

    def save(self, user=None):
        ciclo = super().save(commit=False)
        ciclo.actualizado_por = user
        ciclo.save(
            update_fields=[
                "descripcion",
                "fecha_fin",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        return ciclo


class CefAsistenciaFechaForm(forms.Form):
    fecha = forms.DateField(
        label="Fecha de la jornada",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["fecha"].initial = timezone.localdate
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)


class CefDatosRelevamientoForm(forms.ModelForm):
    class Meta:
        model = CefDatosRelevamiento
        fields = [
            "beneficio_alimentario_gratuito",
            "fuente_financiamiento",
            "prestacion_tipo",
            "espacio_comedor",
            "c_orientacion",
            "observaciones",
        ]
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "beneficio_alimentario_gratuito": "Beneficio alimentario gratuito",
            "fuente_financiamiento": "Fuente de financiamiento",
            "prestacion_tipo": "Tipo de prestación",
            "espacio_comedor": "Espacio comedor",
            "c_orientacion": "Orientación",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["beneficio_alimentario_gratuito"].queryset = _queryset_activos(
            CefBeneficioSinoTipo
        )
        self.fields["fuente_financiamiento"].queryset = _queryset_activos(
            CefFuenteFinanciamientoTipo
        )
        self.fields["prestacion_tipo"].queryset = _queryset_activos(CefPrestacionTipo)
        self.fields["espacio_comedor"].queryset = _queryset_activos(
            CefEspacioComedorTipo
        )
        self.fields["c_orientacion"].queryset = _queryset_activos(CefOrientacionTipo)

        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def _no_corresponde(self, modelo):
        return modelo.objects.filter(activo=True, codigo=-1).first()

    @property
    def no_corresponde_fuente_id(self):
        item = self._no_corresponde(CefFuenteFinanciamientoTipo)
        return item.pk if item else ""

    @property
    def no_corresponde_prestacion_id(self):
        item = self._no_corresponde(CefPrestacionTipo)
        return item.pk if item else ""

    def catalogos_faltantes(self):
        faltantes = []
        chequeos = [
            ("Beneficio alimentario", CefBeneficioSinoTipo),
            ("Fuente de financiamiento", CefFuenteFinanciamientoTipo),
            ("Tipo de prestación", CefPrestacionTipo),
            ("Espacio comedor", CefEspacioComedorTipo),
            ("Orientación", CefOrientacionTipo),
        ]

        for etiqueta, modelo in chequeos:
            if not modelo.objects.filter(activo=True).exists():
                faltantes.append(etiqueta)

        if not self._no_corresponde(CefFuenteFinanciamientoTipo):
            faltantes.append("Fuente de financiamiento: opción No corresponde")
        if not self._no_corresponde(CefPrestacionTipo):
            faltantes.append("Tipo de prestación: opción No corresponde")

        return faltantes

    def _beneficio_requiere_no_corresponde(self, beneficio):
        if not beneficio:
            return False

        nombre = _texto_normalizado(getattr(beneficio, "nombre", ""))
        return (
            getattr(beneficio, "codigo", None) == -1
            or nombre in {"no", "sin informacion"}
            or "sin informacion" in nombre
        )

    def clean(self):
        cleaned_data = super().clean()
        beneficio = cleaned_data.get("beneficio_alimentario_gratuito")

        if self._beneficio_requiere_no_corresponde(beneficio):
            fuente = self._no_corresponde(CefFuenteFinanciamientoTipo)
            prestacion = self._no_corresponde(CefPrestacionTipo)

            if not fuente or not prestacion:
                raise forms.ValidationError(
                    "Faltan catálogos para completar esta carga: opción No corresponde."
                )

            cleaned_data["fuente_financiamiento"] = fuente
            cleaned_data["prestacion_tipo"] = prestacion

        return cleaned_data


class CefGrupoForm(forms.ModelForm):
    class Meta:
        model = CefGrupo
        fields = [
            "actividad",
            "nivel",
            "rango_etario",
            "turno",
            "hora_inicio",
            "hora_fin",
            "cupo_maximo",
            "observaciones",
        ]
        widgets = {
            "hora_inicio": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "hora_fin": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "actividad": "Actividad",
            "nivel": "Nivel",
            "rango_etario": "Rango etario",
            "turno": "Turno",
            "hora_inicio": "Hora inicio",
            "hora_fin": "Hora fin",
            "cupo_maximo": "Cupo máximo",
        }

    def __init__(self, *args, ciclo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["actividad"].queryset = (
            CefActividad.objects.filter(activo=True)
            .select_related("eje", "codigo_ra")
            .order_by("orden", "nombre")
        )
        self.fields["nivel"].queryset = _queryset_activos(CefNivelActividad)
        self.fields["rango_etario"].queryset = _queryset_activos(CefRangoEtario)
        self.fields["turno"].queryset = (
            CefTurno.objects.filter(activo=True, ciclo=ciclo)
            if ciclo
            else CefTurno.objects.none()
        )
        self.fields["cupo_maximo"].required = False

        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)


class CefGrupoDiasForm(forms.Form):
    dias = forms.ModelMultipleChoiceField(
        label="Días de funcionamiento",
        queryset=CefDiaSemana.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={"required": "Seleccioná al menos un día de funcionamiento."},
    )

    def __init__(self, *args, **kwargs):
        dias_iniciales = kwargs.pop("dias_iniciales", None)
        super().__init__(*args, **kwargs)
        self.fields["dias"].queryset = CefDiaSemana.objects.filter(
            activo=True
        ).order_by("orden", "numero")
        if dias_iniciales is not None and not self.is_bound:
            self.fields["dias"].initial = dias_iniciales


class CefInventarioMaterialForm(forms.ModelForm):
    class Meta:
        model = CefInventarioMaterial
        fields = [
            "material",
            "observaciones",
        ]
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "material": "Material",
            "observaciones": "Observaciones generales",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["material"].queryset = (
            CefMaterial.objects.filter(activo=True)
            .order_by("orden", "nombre")
        )
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)


class CefInventarioMaterialObservacionesForm(forms.ModelForm):
    class Meta:
        model = CefInventarioMaterial
        fields = ["observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "observaciones": "Observaciones generales",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_clases_bootstrap(self.fields["observaciones"])


class CefInventarioMaterialEstadoForm(forms.ModelForm):
    class Meta:
        model = CefInventarioMaterialEstado
        fields = [
            "estado",
            "cantidad",
        ]
        labels = {
            "estado": "Estado",
            "cantidad": "Cantidad de unidades",
        }

    def __init__(self, *args, **kwargs):
        inventario_material = kwargs.pop("inventario_material", None)
        super().__init__(*args, **kwargs)

        if inventario_material is not None:
            self.instance.inventario_material = inventario_material

        estados = CefEstadoMaterialTipo.objects.filter(activo=True).order_by(
            "orden",
            "codigo",
            "nombre",
        )
        inventario_material = getattr(
            self.instance,
            "inventario_material",
            None,
        )
        if inventario_material and getattr(inventario_material, "pk", None):
            usados = CefInventarioMaterialEstado.objects.filter(
                inventario_material=inventario_material,
                estado_id__isnull=False,
            ).exclude(pk=getattr(self.instance, "pk", None)).values_list(
                "estado_id",
                flat=True,
            )
            estados = estados.exclude(pk__in=usados)

            if self.is_bound:
                estado_enviado = self.data.get(self.add_prefix("estado"))
                if estado_enviado and str(estado_enviado).isdigit():
                    estados = estados | CefEstadoMaterialTipo.objects.filter(
                        activo=True,
                        pk=estado_enviado,
                    )

        estado_field = self.fields["estado"]
        estado_field.queryset = estados.order_by("orden", "codigo", "nombre")
        estado_field.required = True
        estado_field.empty_label = "Seleccioná un estado"
        estado_field.label_from_instance = lambda estado: estado.nombre

        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get("estado")

        inventario_material = getattr(
            self.instance,
            "inventario_material",
            None,
        )
        if (
            estado
            and inventario_material
            and getattr(inventario_material, "pk", None)
        ):
            repetido = CefInventarioMaterialEstado.objects.filter(
                inventario_material=inventario_material,
                estado=estado,
            ).exclude(pk=getattr(self.instance, "pk", None))
            if repetido.exists():
                self.add_error(
                    "estado",
                    "Ese estado ya está cargado para el material. "
                    "Editá su cantidad.",
                )

        return cleaned_data


class CefBusquedaAlumnoForm(forms.Form):
    cuil = forms.CharField(
        label="CUIL del alumno",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "placeholder": "Ingresá 11 dígitos",
            }
        ),
    )

    def clean_cuil(self):
        cuil = _solo_digitos(self.cleaned_data.get("cuil"))
        if not cuil:
            raise forms.ValidationError("Ingresá el CUIL del alumno.")
        if len(cuil) != 11:
            raise forms.ValidationError("El CUIL del alumno debe tener 11 dígitos.")
        return cuil


class CefBajaMotivoForm(forms.Form):
    motivo_baja = forms.CharField(
        label="Motivo de baja",
        max_length=255,
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


class CefInscripcionForm(forms.ModelForm):
    class Meta:
        model = CefInscripcion
        fields = [
            "fecha_inscripcion",
            "observaciones",
        ]
        widgets = {
            "fecha_inscripcion": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "fecha_inscripcion": "Fecha de inscripción",
            "observaciones": "Observaciones",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not getattr(self.instance, "pk", None):
            self.fields["fecha_inscripcion"].initial = timezone.localdate
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)


class CefBusquedaDocenteForm(forms.Form):
    cuil = forms.CharField(
        label="CUIL del profesor",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "placeholder": "Ingresá 11 dígitos",
            }
        ),
    )

    def clean_cuil(self):
        cuil = _solo_digitos(self.cleaned_data.get("cuil"))
        if not cuil:
            raise forms.ValidationError("Ingresá el CUIL del profesor.")
        if len(cuil) != 11:
            raise forms.ValidationError("El CUIL del profesor debe tener 11 dígitos.")
        return cuil


class CefDocenteGrupoForm(forms.ModelForm):
    class Meta:
        model = CefDocenteGrupo
        fields = [
            "rol",
            "fecha_desde",
            "observaciones",
        ]
        widgets = {
            "fecha_desde": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "rol": "Rol en el grupo",
            "fecha_desde": "Fecha de asignación",
            "observaciones": "Observaciones",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_desde"].required = True
        if not self.is_bound and not getattr(self.instance, "pk", None):
            self.fields["fecha_desde"].initial = timezone.localdate
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)
