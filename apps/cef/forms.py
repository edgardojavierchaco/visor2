# -*- coding: utf-8 -*-

import re

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Q

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
from .services import (
    fecha_operativa_predeterminada,
    validar_cambio_inicio_ciclo,
    validar_fechas_oficiales_ciclo,
    validar_fecha_inscripcion_grupo,
    validar_fecha_interactiva_ciclo,
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
        label="Fecha de inicio oficial",
        required=True,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    fecha_fin = forms.DateField(
        label="Fecha de fin prevista",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
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
        if cleaned_data.get("anio") and not any(
            campo in self.errors for campo in ("fecha_inicio", "fecha_fin")
        ):
            try:
                validar_fechas_oficiales_ciclo(
                    cleaned_data["anio"],
                    cleaned_data.get("fecha_inicio"),
                    cleaned_data.get("fecha_fin"),
                )
            except ValidationError as exc:
                self.add_error(None, exc)
        return cleaned_data

    def save(self, user=None):
        fecha_inicio, fecha_fin = validar_fechas_oficiales_ciclo(
            self.cleaned_data["anio"],
            self.cleaned_data.get("fecha_inicio"),
            self.cleaned_data.get("fecha_fin"),
        )
        return CefCiclo.objects.create(
            anio=self.cleaned_data["anio"],
            descripcion=self.cleaned_data.get("descripcion", ""),
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activo=True,
            actual=True,
            cerrado=False,
            creado_por=user,
            actualizado_por=user,
        )


class CefCicloEdicionForm(forms.ModelForm):
    class Meta:
        model = CefCiclo
        fields = ["descripcion", "fecha_inicio", "fecha_fin"]
        widgets = {
            "fecha_inicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }
        labels = {
            "fecha_inicio": "Fecha de inicio oficial",
            "descripcion": "Descripción",
            "fecha_fin": "Fecha de fin prevista",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fecha_inicio_anterior = self.instance.fecha_inicio
        self.fields["fecha_inicio"].required = True
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean(self):
        cleaned_data = super().clean()
        if not any(campo in self.errors for campo in ("fecha_inicio", "fecha_fin")):
            try:
                fecha_inicio, _ = validar_fechas_oficiales_ciclo(
                    self.instance.anio,
                    cleaned_data.get("fecha_inicio"),
                    cleaned_data.get("fecha_fin"),
                )
                validar_cambio_inicio_ciclo(
                    self.instance,
                    fecha_inicio,
                    fecha_inicio_anterior=self._fecha_inicio_anterior,
                )
            except ValidationError as exc:
                self.add_error(None, exc)
        return cleaned_data

    def save(self, user=None):
        ciclo = super().save(commit=False)
        validar_fechas_oficiales_ciclo(ciclo.anio, ciclo.fecha_inicio, ciclo.fecha_fin)
        validar_cambio_inicio_ciclo(
            ciclo, ciclo.fecha_inicio, fecha_inicio_anterior=self._fecha_inicio_anterior,
        )
        ciclo.actualizado_por = user
        ciclo.save(
            update_fields=[
                "descripcion",
                "fecha_inicio",
                "fecha_fin",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        return ciclo


class CefCicloAnualForm(forms.Form):
    fecha_inicio = forms.DateField(
        label="Fecha de inicio oficial",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    fecha_fin = forms.DateField(
        label="Fecha de fin prevista",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    def __init__(self, *args, anio_destino, **kwargs):
        self.anio_destino = anio_destino
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean(self):
        cleaned_data = super().clean()
        if not any(campo in self.errors for campo in ("fecha_inicio", "fecha_fin")):
            try:
                validar_fechas_oficiales_ciclo(
                    self.anio_destino,
                    cleaned_data.get("fecha_inicio"),
                    cleaned_data.get("fecha_fin"),
                )
            except ValidationError as exc:
                self.add_error(None, exc)
        return cleaned_data


class CefAsistenciaFechaForm(forms.Form):
    fecha = forms.DateField(
        label="Fecha de asistencia",
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date", "autocomplete": "off"},
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

        # Este select controla en vivo Fuente y Prestación mediante un listener
        # DOM nativo en editar_datos_cueanexo_cef.html. Al estar enriquecido con
        # Select2, debe volver a emitir change nativo igual que el buscador de alumnos.
        self.fields["beneficio_alimentario_gratuito"].widget.attrs[
            "data-cef-select-native-change"
        ] = "true"

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
        filtro_actividad = Q(activo=True)
        if self.instance.pk:
            filtro_actividad |= Q(pk=self.instance.actividad_id)
        self.fields["actividad"].queryset = (
            CefActividad.objects.filter(filtro_actividad)
            .select_related("eje", "codigo_ra")
            .order_by("orden", "nombre")
        )
        self.fields["nivel"].queryset = _queryset_activos(CefNivelActividad)
        self.fields["rango_etario"].queryset = _queryset_activos(CefRangoEtario)
        self.fields["turno"].queryset = CefTurno.objects.filter(
            activo=True
        ).order_by("orden", "nombre")
        if self.instance.pk:
            for campo, modelo in (
                ("nivel", CefNivelActividad),
                ("rango_etario", CefRangoEtario),
                ("turno", CefTurno),
            ):
                queryset = modelo.objects.filter(
                    Q(activo=True) | Q(pk=getattr(self.instance, f"{campo}_id"))
                )
                self.fields[campo].queryset = (
                    queryset.order_by("orden", "nombre") if campo == "turno"
                    else queryset
                )
        self.fields["cupo_maximo"].required = True
        self.fields["cupo_maximo"].error_messages["required"] = (
            "Indicá un cupo máximo mayor a cero."
        )

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
    tipo_doc = forms.ChoiceField(
        label="Tipo de documento",
        choices=(),
        required=True,
        widget=forms.Select(
            attrs={
                "data-cef-select": "1",
                "data-cef-select-style": "bnh",
                "data-cef-select-dropdown-parent": "body",
                "data-cef-select-search-threshold": "10",
                "data-cef-select-native-change": "true",
            }
        ),
    )
    nro_doc = forms.CharField(
        label="Número de documento",
        max_length=30,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Según el tipo seleccionado",
            }
        ),
    )
    cuil = forms.CharField(
        label="CUIL",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "Opcional · 11 dígitos",
            }
        ),
    )
    apellidos = forms.CharField(
        label="Apellidos",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Apellidos",
            }
        ),
    )
    nombres = forms.CharField(
        label="Nombres",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Nombres",
            }
        ),
    )
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )
    sexo = forms.ChoiceField(
        label="Sexo",
        choices=(),
        required=False,
        widget=forms.Select(
            attrs={
                "data-cef-select": "1",
                "data-cef-select-style": "bnh",
                "data-cef-select-dropdown-parent": "body",
                "data-cef-select-search-threshold": "10",
                "data-cef-select-native-change": "true",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        alumno_model = apps.get_model("bnhalumnos", "Alumno")
        tipo_model = alumno_model._meta.get_field("tipo_doc").remote_field.model
        opciones = list(tipo_model.objects.all().order_by("pk"))
        self.fields["tipo_doc"].choices = [(str(item.pk), str(item)) for item in opciones]

        sexo_model = alumno_model._meta.get_field("sexo").remote_field.model
        opciones_sexo = list(sexo_model.objects.all().order_by("pk"))
        self.fields["sexo"].choices = [
            ("", "Seleccione"),
            *((str(item.pk), str(item)) for item in opciones_sexo),
        ]

        codigos = {str(item.pk) for item in opciones}
        if not self.is_bound:
            self.initial["tipo_doc"] = (
                "1"
                if "1" in codigos
                else (str(opciones[0].pk) if opciones else "")
            )

    def clean(self):
        cleaned_data = super().clean()
        tipo_id = cleaned_data.get("tipo_doc")
        if not tipo_id:
            return cleaned_data

        alumno_model = apps.get_model("bnhalumnos", "Alumno")
        tipo_model = alumno_model._meta.get_field("tipo_doc").remote_field.model
        try:
            tipo_doc = tipo_model.objects.get(pk=tipo_id)
        except tipo_model.DoesNotExist:
            self.add_error("tipo_doc", "El tipo de documento seleccionado no es válido.")
            return cleaned_data

        from apps.bnhalumnos.models import (
            clasificar_tipo_documento,
            normalizar_cuil_opcional,
            normalizar_documento_bnh,
            validar_cuil_con_documento,
        )

        nro_doc = None
        cuil = None
        nro_doc_valido = True
        cuil_valido = True

        try:
            nro_doc = normalizar_documento_bnh(
                tipo_doc,
                cleaned_data.get("nro_doc"),
                "Número de documento",
            )
        except ValidationError as exc:
            nro_doc_valido = False
            self.add_error("nro_doc", exc)

        try:
            cuil = normalizar_cuil_opcional(cleaned_data.get("cuil"), "CUIL")
        except ValidationError as exc:
            cuil_valido = False
            self.add_error("cuil", exc)

        if nro_doc_valido and cuil_valido:
            try:
                validar_cuil_con_documento(cuil, tipo_doc, nro_doc, "CUIL")
            except ValidationError as exc:
                cuil_valido = False
                self.add_error("cuil", exc)

        busqueda_sin_identidad = False
        if nro_doc_valido and cuil_valido and not nro_doc and not cuil:
            clase_documento = clasificar_tipo_documento(tipo_doc)
            if clase_documento in {"no_posee", "en_tramite"}:
                # Sin número documental, CEF exige los datos actuales que BNH
                # mantiene como obligatorios para recuperar la persona de forma exacta.
                busqueda_sin_identidad = True
                apellidos = str(cleaned_data.get("apellidos") or "").strip()
                nombres = str(cleaned_data.get("nombres") or "").strip()
                fecha_nacimiento = cleaned_data.get("fecha_nacimiento")
                sexo_id = cleaned_data.get("sexo")

                if not apellidos:
                    self.add_error("apellidos", "Ingresá los apellidos para buscar al alumno.")
                if not nombres:
                    self.add_error("nombres", "Ingresá los nombres para buscar al alumno.")
                if not fecha_nacimiento:
                    self.add_error(
                        "fecha_nacimiento",
                        "Ingresá la fecha de nacimiento para buscar al alumno.",
                    )
                if not sexo_id:
                    self.add_error("sexo", "Seleccioná el sexo para buscar al alumno.")

                cleaned_data["apellidos"] = apellidos
                cleaned_data["nombres"] = nombres
            else:
                raise forms.ValidationError(
                    "Para buscar un alumno necesitás un número de documento o un CUIL informado."
                )

        cleaned_data["tipo_doc_obj"] = tipo_doc
        cleaned_data["nro_doc"] = nro_doc or ""
        cleaned_data["cuil"] = cuil or ""
        cleaned_data["busqueda_sin_identidad"] = busqueda_sin_identidad
        return cleaned_data


class CefBajaMotivoForm(forms.Form):
    motivo_baja = forms.CharField(
        label="Motivo de baja",
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean_motivo_baja(self):
        return (self.cleaned_data.get("motivo_baja") or "").strip()


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
            "fecha_inscripcion": "Fecha de incorporación al grupo",
            "observaciones": "Observaciones",
        }

    def __init__(self, *args, grupo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.grupo = grupo
        if self.grupo is None and getattr(self.instance, "pk", None):
            self.grupo = self.instance.grupo
        self.fields["fecha_inscripcion"].required = True
        if not self.is_bound and not getattr(self.instance, "pk", None):
            self.fields["fecha_inscripcion"].initial = None
            self.initial["fecha_inscripcion"] = None
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean_fecha_inscripcion(self):
        fecha_inscripcion = self.cleaned_data.get("fecha_inscripcion")
        if self.grupo is None:
            raise forms.ValidationError(
                "No se pudo validar el ciclo del grupo seleccionado."
            )
        return validar_fecha_inscripcion_grupo(self.grupo, fecha_inscripcion)


class CefInscripcionRectificacionForm(CefInscripcionForm):
    class Meta(CefInscripcionForm.Meta):
        fields = ["fecha_inscripcion", "fecha_baja", "motivo_baja", "observaciones"]
        widgets = {
            **CefInscripcionForm.Meta.widgets,
            "fecha_baja": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }
        labels = {
            **CefInscripcionForm.Meta.labels,
            "fecha_baja": "Fecha de baja",
            "motivo_baja": "Motivo de baja",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_baja"].required = True

    def clean_fecha_baja(self):
        return validar_fecha_interactiva_ciclo(
            self.grupo.ciclo, self.cleaned_data.get("fecha_baja"),
        )


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

    def __init__(self, *args, grupo=None, ciclo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.grupo = grupo or getattr(self.instance, "grupo", None)
        self.ciclo = self.grupo.ciclo if self.grupo is not None else ciclo
        self.fields["fecha_desde"].required = True
        if not self.is_bound and not getattr(self.instance, "pk", None):
            fecha_inicial = (
                fecha_operativa_predeterminada(self.ciclo)
                if self.ciclo is not None
                else None
            )
            self.fields["fecha_desde"].initial = fecha_inicial
            self.initial["fecha_desde"] = fecha_inicial
        for field in self.fields.values():
            _aplicar_clases_bootstrap(field)

    def clean_fecha_desde(self):
        grupo = self.grupo or getattr(self.instance, "grupo", None)
        ciclo = grupo.ciclo if grupo is not None else self.ciclo
        if ciclo is None:
            raise forms.ValidationError(
                "No se pudo validar el ciclo del grupo seleccionado."
            )
        return validar_fecha_interactiva_ciclo(
            ciclo,
            self.cleaned_data.get("fecha_desde"),
            mensaje_requerida="Debe indicar la fecha de asignación del profesor.",
            mensaje_anio="La fecha de asignación debe pertenecer al año del ciclo.",
        )



class CefDocenteGrupoRectificacionForm(CefDocenteGrupoForm):
    class Meta(CefDocenteGrupoForm.Meta):
        fields = ["rol", "fecha_desde", "fecha_hasta", "motivo_baja", "observaciones"]
        widgets = {
            **CefDocenteGrupoForm.Meta.widgets,
            "fecha_hasta": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }
        labels = {
            **CefDocenteGrupoForm.Meta.labels,
            "fecha_hasta": "Fecha de finalización",
            "motivo_baja": "Motivo de baja",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_hasta"].required = True

    def clean_fecha_hasta(self):
        return validar_fecha_interactiva_ciclo(
            self.ciclo, self.cleaned_data.get("fecha_hasta"),
        )
