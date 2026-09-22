import re

from django import forms
from django.core.exceptions import ValidationError

from .domain.access import scoped_offers, user_has_cueanexo_access
from .domain.catalogs import (
    activity_catalogs,
    available_curricular_levels,
    available_levels,
    condiciones_actividad,
    curricular_catalogs,
    titulacion_options,
    titulacion_source,
    valid_titulacion,
)
from .models import (
    EspacioCurricularNombre,
    Grado_anio,
    HorarioActividad,
    Localidades,
    ModalidadNivel,
    ModalidadTipo,
    NivelServicioTipo,
    NomencladorCeic,
    Personas,
    RegistroActividades,
    RevisionCatalogos,
    Secciones,
    TipoPersonal,
    CondicionActividadNombre,
    validar_cuil,
    validar_dni,
)


class StyledForm(forms.ModelForm):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            if isinstance(field, forms.BooleanField):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select select2"
            else:
                field.widget.attrs["class"] = "form-control"
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(
                    format="%Y-%m-%d",
                    attrs={"type": "date", "class": "form-control"},
                )
                field.input_formats = ["%Y-%m-%d"]
        if self.instance.pk and "version" in self.fields:
            self.initial["version"] = self.instance.version


class PersonaForm(StyledForm):
    cuil = forms.CharField(max_length=20, label="CUIL", help_text="Puede ingresarlo con guiones.")
    dni = forms.CharField(max_length=12, label="DNI")

    class Meta:
        model = Personas
        fields = [
            "cuil", "dni", "apellido", "nombre", "f_nacimiento", "sexo",
            "provincia", "localidad", "codigo_area", "telefono", "whatsapp",
        ]
        labels = {"f_nacimiento": "Fecha de nacimiento", "codigo_area": "Código de área"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raw = self.data.get(self.add_prefix("provincia")) if self.is_bound else self.instance.provincia_id
        try:
            provincia = int(raw)
        except (TypeError, ValueError):
            provincia = None
        self.fields["localidad"].queryset = Localidades.objects.filter(c_provincia_id=provincia)

    def clean_cuil(self):
        value = re.sub(r"[.\s-]", "", self.cleaned_data["cuil"])
        validar_cuil(value)
        if not re.fullmatch(r"[0-9]{11}", value):
            raise forms.ValidationError("Ingrese 11 dígitos.")

        # En Alta de personal no se permite duplicar una persona existente.
        # En edición se excluye la propia instancia.
        duplicate = Personas.objects.filter(cuil=value)
        if self.instance and self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise forms.ValidationError(
                "Este CUIL ya se encuentra registrado en BNH Personal Educativo. "
                "Utilice la ficha existente o la opción “Vincular existente”."
            )

        return value

    def clean_dni(self):
        value = re.sub(r"[.\s]", "", self.cleaned_data["dni"])
        validar_dni(value)
        return value

    def clean_apellido(self):
        return " ".join(self.cleaned_data["apellido"].upper().split())

    def clean_nombre(self):
        return " ".join(self.cleaned_data["nombre"].upper().split())


class ActividadDirectorForm(StyledForm):
    """
    Mantiene dos circuitos completamente independientes:

      1) CARGO / CEIC:
         modalidad -> Modalidades (modalidades_tipo)
         niveles   -> NivelServicio (nivel_servicio)
         ceic      -> ModalidadNivelCeic/NomencladorCeic

      2) UBICACIÓN CURRICULAR:
         modalidad_curricular -> ModalidadTipo (modalidad1_tipo)
         nivel_curricular     -> NivelServicioTipo (nivel_servicio_tipo)
         titulacion           -> tabla dinámica según modalidad/nivel
         espacio_curricular   -> espacio_curricular_nombre
         grado_anio/secciones -> modalidad_curricular + nivel_curricular
    """

    cueanexo = forms.ChoiceField(label="Institución / CUEANEXO")
    operation_id = forms.UUIDField(widget=forms.HiddenInput, required=False)
    catalog_version = forms.IntegerField(widget=forms.HiddenInput, required=False)
    confirmar_posible_duplicado = forms.BooleanField(
        required=False,
        label=(
            "Confirmo que revisé el cargo existente y que esta designación debe registrarse "
            "como un cargo distinto."
        ),
        widget=forms.HiddenInput(),
    )

    titulacion = forms.TypedChoiceField(
        label="Titulación",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Seleccione titulación")],
    )
    titulacion_fuente = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = RegistroActividades
        fields = [
            "cueanexo",
            "tipo_personal",
            # Circuito Cargo / CEIC (legacy)
            "modalidad",
            "niveles",
            "sit_revista",
            "cond_actividad",
            "t_designacion",
            "ceic",
            # Circuito curricular nuevo
            "modalidad_curricular",
            "nivel_curricular",
            "titulacion",
            "titulacion_fuente",
            "espacio_curricular",
            "grado_anio",
            "turno",
            "secciones",
            # Fechas / funciones
            "f_desde",
            "f_hasta",
            "carga_horaria",
            "estado",
            "funciones",
            "f_desde_funciones",
            "f_hasta_funciones",
        ]
        labels = {
            "tipo_personal": "Tipo de personal",
            "modalidad": "Modalidad del cargo / CEIC",
            "niveles": "Nivel del cargo / CEIC",
            "sit_revista": "Situación de revista",
            "cond_actividad": "Condición de actividad",
            "t_designacion": "Tipo de designación",
            "ceic": "Cargo / CEIC",
            "modalidad_curricular": "Modalidad curricular",
            "nivel_curricular": "Nivel curricular",
            "espacio_curricular": "Espacio curricular",
            "grado_anio": "Grado / Año",
            "secciones": "Sección",
            "f_desde": "Inicio del cargo",
            "f_hasta": "Fin del cargo (si corresponde)",
            "f_desde_funciones": "Inicio de funciones",
            "f_hasta_funciones": "Fin de funciones (si corresponde)",
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["operation_id"].required = not bool(self.instance.pk)
        self.initial["operation_id"] = self.instance.uuid
        self.initial["catalog_version"] = RevisionCatalogos.current_version()

        # La confirmación de posible duplicado se muestra sólo cuando el backend
        # encuentra una coincidencia con la clave funcional. No se usa UNIQUE
        # porque dos designaciones legítimas pueden compartir esos valores.
        self.fields["confirmar_posible_duplicado"].help_text = (
            "Clave revisada: persona + CUEANEXO + tipo de personal + CEIC + "
            "situación de revista + tipo de designación + fecha desde."
        )

        # ----------------------------------------------------
        # CUEANEXOS autorizados
        # ----------------------------------------------------
        choices = {}
        ofertas = (
            scoped_offers(user)
            .order_by("cueanexo_str", "nom_est")
            .values_list("cueanexo_str", "nom_est")
        )
        for cue, name in ofertas:
            choices.setdefault(cue, f"{cue} — {name}")
        self.fields["cueanexo"].choices = [("", "Seleccione institución")] + list(choices.items())
        if self.instance.pk:
            self.fields["cueanexo"].disabled = True

        def raw_value(name, *, fk=True):
            if self.is_bound:
                raw = self.data.get(self.add_prefix(name))
            else:
                attr = name + "_id" if fk else name
                raw = getattr(self.instance, attr, None)
            try:
                return int(raw) if raw not in (None, "") else None
            except (TypeError, ValueError):
                return None

        tipo_personal = raw_value("tipo_personal")
        es_no_docente = tipo_personal == 2

        self.fields["tipo_personal"].queryset = (
            TipoPersonal.objects
            .order_by("c_tpersonal")
        )

        situacion_revista = raw_value("sit_revista")
        self.fields["cond_actividad"].queryset = condiciones_actividad(
            tipo_personal,
            situacion_revista,
        )
        self.fields["cond_actividad"].required = True
        self.fields["cond_actividad"].label_from_instance = (
            lambda obj: str(obj)
        )

        # ====================================================
        # CIRCUITO CARGO / CEIC: SE MANTIENE COMO ESTABA
        # ====================================================
        modalidad = raw_value("modalidad")
        nivel = raw_value("niveles")

        self.fields["niveles"].queryset = available_levels(modalidad)
        try:
            ceic, _, _ = activity_catalogs(
                modalidad,
                nivel,
                tipo_personal=tipo_personal,
            )
        except ValidationError:
            ceic = NomencladorCeic.objects.none()
        self.fields["ceic"].queryset = ceic

        # ====================================================
        # CIRCUITO CURRICULAR NUEVO
        # ====================================================
        self.fields["modalidad_curricular"].queryset = (
            ModalidadTipo.objects.filter(c_modalidad1__gt=0).order_by("orden", "descripcion")
        )

        modalidad_curricular = raw_value("modalidad_curricular")
        nivel_curricular = raw_value("nivel_curricular")
        titulacion = raw_value("titulacion", fk=False)

        self.fields["nivel_curricular"].queryset = available_curricular_levels(modalidad_curricular)

        catalogs = curricular_catalogs(
            modalidad_curricular,
            nivel_curricular,
            titulacion,
            tipo_personal=tipo_personal,
        )

        title_options = titulacion_options(modalidad_curricular, nivel_curricular)
        self.fields["titulacion"].choices = [("", "Seleccione titulación")] + [
            (item["id_titulacion"], item["descripcion"])
            for item in title_options
        ]

        self.fields["espacio_curricular"].queryset = catalogs["espacios"]
        self.fields["grado_anio"].queryset = catalogs["grados"]
        self.fields["secciones"].queryset = catalogs["secciones"]

        expected_source = titulacion_source(modalidad_curricular, nivel_curricular)
        self.initial["titulacion_fuente"] = expected_source or getattr(
            self.instance, "titulacion_fuente", ""
        )

        # Titulación sólo es obligatoria cuando la combinación tiene catálogo.
        self.fields["titulacion"].required = bool(expected_source) and not es_no_docente
        self.fields["espacio_curricular"].required = False
        self.fields["grado_anio"].required = False
        self.fields["secciones"].required = False

        if es_no_docente:
            for name in (
                "modalidad_curricular",
                "nivel_curricular",
                "titulacion",
                "espacio_curricular",
                "grado_anio",
                "secciones",
            ):
                self.fields[name].required = False
        else:
            self.fields["modalidad_curricular"].required = True
            self.fields["nivel_curricular"].required = True

        self.fields["f_hasta"].help_text = "Deje vacío si no existe una fecha de cese conocida."
        self.fields["modalidad_curricular"].help_text = (
            "Circuito curricular independiente del Cargo / CEIC. Fuente: modalidad1_tipo."
        )
        self.fields["nivel_curricular"].help_text = "Fuente: nivel_servicio_tipo."
        self.fields["espacio_curricular"].help_text = (
            "Se filtra por la titulación seleccionada. Puede quedar vacío si esa titulación no tiene espacios cargados."
        )
        self.fields["grado_anio"].help_text = "Se filtra por modalidad y nivel curricular."
        self.fields["secciones"].help_text = "Se filtra por modalidad y nivel curricular."

    def expose_duplicate_warning(self, message=None):
        """Hace visible la confirmación sólo después de una detección real."""
        field = self.fields["confirmar_posible_duplicado"]
        field.widget = forms.CheckboxInput(attrs={"class": "form-check-input"})
        if message:
            field.help_text = message + " " + field.help_text

    def clean_cueanexo(self):
        value = self.cleaned_data["cueanexo"]
        if not user_has_cueanexo_access(self.user, value):
            raise forms.ValidationError("Institución no autorizada.")
        return value

    def clean(self):
        data = super().clean()

        submitted_catalog_version = data.get("catalog_version")
        if submitted_catalog_version is not None:
            current_catalog_version = RevisionCatalogos.current_version()
            if submitted_catalog_version != current_catalog_version:
                raise forms.ValidationError(
                    "Los catálogos BNH fueron actualizados mientras el formulario estaba abierto. "
                    "Recargue la página y vuelva a seleccionar las opciones antes de guardar."
                )

        tipo_personal = data.get("tipo_personal")
        tipo_personal_codigo = (
            tipo_personal.c_tpersonal
            if tipo_personal
            else None
        )
        es_no_docente = tipo_personal_codigo == 2

        # ====================================================
        # CIRCUITO CARGO / CEIC (lógica anterior)
        # ====================================================
        modalidad = data.get("modalidad")
        nivel = data.get("niveles")
        ceic = data.get("ceic")
        situacion_revista = data.get("sit_revista")
        condicion = data.get("cond_actividad")

        if not tipo_personal:
            self.add_error("tipo_personal", "Seleccione el tipo de personal.")

        if tipo_personal and situacion_revista:
            valid_conditions = condiciones_actividad(
                tipo_personal.c_tpersonal,
                situacion_revista.pk,
            )
            if not condicion:
                self.add_error(
                    "cond_actividad",
                    "Seleccione la condición de actividad.",
                )
            elif not valid_conditions.filter(pk=condicion.pk).exists():
                self.add_error(
                    "cond_actividad",
                    "La condición de actividad no corresponde al tipo de personal y situación de revista seleccionados.",
                )

        if modalidad and nivel and not ModalidadNivel.objects.filter(
            modalidad=modalidad, nivel=nivel
        ).exists():
            self.add_error("niveles", "El nivel no está habilitado para esta modalidad del cargo.")

        if es_no_docente:
            if ceic and not (1023 <= ceic.c_niv <= 1025):
                self.add_error(
                    "ceic",
                    "Para personal no docente el cargo debe corresponder a un CEIC con c_niv entre 1023 y 1025.",
                )

            # El circuito curricular no corresponde a No Docente.
            data["modalidad_curricular"] = None
            data["nivel_curricular"] = None
            data["titulacion"] = None
            data["titulacion_fuente"] = ""
            data["espacio_curricular"] = None
            data["grado_anio"] = None
            data["secciones"] = None
            return data

        # ====================================================
        # CIRCUITO CURRICULAR
        # ====================================================
        modalidad_curricular = data.get("modalidad_curricular")
        nivel_curricular = data.get("nivel_curricular")
        titulacion = data.get("titulacion")
        espacio = data.get("espacio_curricular")
        grado = data.get("grado_anio")
        seccion = data.get("secciones")

        if not modalidad_curricular:
            self.add_error("modalidad_curricular", "Seleccione la modalidad curricular.")
            return data

        if not nivel_curricular:
            self.add_error("nivel_curricular", "Seleccione el nivel curricular.")
            return data

        if not available_curricular_levels(modalidad_curricular.pk).filter(pk=nivel_curricular.pk).exists():
            self.add_error(
                "nivel_curricular",
                "El nivel curricular no pertenece a la modalidad curricular seleccionada.",
            )
            return data

        source = titulacion_source(modalidad_curricular.pk, nivel_curricular.pk)
        data["titulacion_fuente"] = source

        if source:
            if not titulacion:
                self.add_error("titulacion", "Seleccione una titulación.")
            elif not valid_titulacion(
                modalidad_curricular.pk,
                nivel_curricular.pk,
                titulacion,
                source,
            ):
                self.add_error(
                    "titulacion",
                    "La titulación no corresponde a la modalidad y nivel curricular seleccionados.",
                )
        elif titulacion:
            self.add_error("titulacion", "El nivel seleccionado no tiene catálogo de titulaciones configurado.")

        catalogs = curricular_catalogs(
            modalidad_curricular.pk,
            nivel_curricular.pk,
            titulacion,
            tipo_personal=tipo_personal_codigo,
        )

        if espacio and not catalogs["espacios"].filter(pk=espacio.pk).exists():
            self.add_error("espacio_curricular", "El espacio curricular no corresponde a la titulación seleccionada.")

        if grado and not catalogs["grados"].filter(pk=grado.pk).exists():
            self.add_error("grado_anio", "El grado/año no corresponde a la modalidad y nivel curricular.")

        if seccion and not catalogs["secciones"].filter(pk=seccion.pk).exists():
            self.add_error("secciones", "La sección no corresponde a la modalidad y nivel curricular.")

        return data


class HorarioActividadForm(StyledForm):
    class Meta:
        model = HorarioActividad
        fields = ["dia", "hora_desde", "hora_hasta"]
        widgets = {
            key: forms.TimeInput(format="%H:%M", attrs={"type": "time"})
            for key in ("hora_desde", "hora_hasta")
        }

    def clean(self):
        data = super().clean()
        if data.get("hora_desde") and data.get("hora_hasta") and data["hora_desde"] >= data["hora_hasta"]:
            self.add_error("hora_hasta", "La hora de fin debe ser posterior al inicio.")
        return data


class ConfirmacionForm(forms.Form):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    motivo = forms.CharField(
        min_length=5,
        max_length=1000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )


class VincularPersonaForm(forms.Form):
    cuil = forms.CharField(max_length=20, label="CUIL")
    dni = forms.CharField(max_length=8, label="DNI")
    apellido = forms.CharField(max_length=150, label="Apellido")
    nombre = forms.CharField(max_length=150, label="Nombre")
    confirmo = forms.BooleanField(
        label="Confirmo que esta persona presta servicios en la institución seleccionada."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Estos datos se recuperan desde la persona ya registrada.
        # readonly permite enviarlos igualmente en el POST.
        for name in ("dni", "apellido", "nombre"):
            self.fields[name].widget.attrs["readonly"] = "readonly"
            self.fields[name].widget.attrs["autocomplete"] = "off"

        self.fields["cuil"].widget.attrs["autocomplete"] = "off"

    def clean_cuil(self):
        value = re.sub(r"[^0-9]", "", self.cleaned_data["cuil"])
        validar_cuil(value)
        if len(value) != 11:
            raise forms.ValidationError("Ingrese un CUIL válido de 11 dígitos.")
        return value

    def clean_dni(self):
        value = re.sub(r"[^0-9]", "", self.cleaned_data["dni"])
        validar_dni(value)
        return value

    def clean_apellido(self):
        return " ".join(self.cleaned_data["apellido"].upper().split())

    def clean_nombre(self):
        return " ".join(self.cleaned_data["nombre"].upper().split())
