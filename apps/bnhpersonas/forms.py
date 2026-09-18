import re
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Personas, 
    RegistroActividades, 
    Localidades, 
    HorarioActividad, 
    ModalidadNivel, 
    Grado_anio,
    Secciones,
    validar_cuil, 
    validar_dni
)
    
from .domain.access import scoped_offers, user_has_cueanexo_access
from .domain.catalogs import activity_catalogs, available_levels


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
                field.widget = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"})
                field.input_formats = ["%Y-%m-%d"]
        if self.instance.pk and "version" in self.fields:
            self.initial["version"] = self.instance.version


class PersonaForm(StyledForm):
    cuil = forms.CharField(max_length=20, label="CUIL", help_text="Puede ingresarlo con guiones.")
    dni = forms.CharField(max_length=12, label="DNI")

    class Meta:
        model = Personas
        fields = ["cuil", "dni", "apellido", "nombre", "f_nacimiento", "sexo", "provincia", "localidad", "codigo_area", "telefono", "whatsapp"]
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

    cueanexo = forms.ChoiceField(
        label="Institución / CUEANEXO"
    )

    operation_id = forms.UUIDField(
        widget=forms.HiddenInput,
        required=False
    )

    class Meta:

        model = RegistroActividades

        fields = [
            "cueanexo",
            "categoria",
            "modalidad",
            "niveles",
            "sit_revista",
            "cond_actividad",
            "designacion",
            "t_designacion",
            "ceic",
            "grado_anio",
            "turno",
            "secciones",
            "espacios",
            "f_desde",
            "f_hasta",
            "carga_horaria",
            "estado",
            "funciones",
            "f_desde_funciones",
            "f_hasta_funciones",
        ]

        labels = {
            "categoria": "Tipo de personal",
            "niveles": "Nivel",
            "sit_revista": "Situación de revista",
            "cond_actividad": "Condición de actividad",
            "t_designacion": "Tipo de designación",
            "ceic": "Cargo / CEIC",
            "f_desde": "Inicio del cargo",
            "f_hasta": "Fin del cargo (si corresponde)",
            "f_desde_funciones": "Inicio de funciones",
            "f_hasta_funciones": "Fin de funciones (si corresponde)",
        }

    def __init__(
        self,
        *args,
        user=None,
        **kwargs
    ):

        self.user = user

        super().__init__(*args, **kwargs)

        # ====================================================
        # OPERATION ID
        # ====================================================

        self.fields["operation_id"].required = (
            not bool(self.instance.pk)
        )

        self.initial["operation_id"] = (
            self.instance.uuid
        )

        # ====================================================
        # CUEANEXOS HABILITADOS
        # ====================================================

        choices = {}

        ofertas = (
            scoped_offers(user)
            .order_by(
                "cueanexo_str",
                "nom_est",
            )
            .values_list(
                "cueanexo_str",
                "nom_est",
            )
        )

        for cue, name in ofertas:

            choices.setdefault(
                cue,
                f"{cue} — {name}"
            )

        self.fields["cueanexo"].choices = [
            (
                "",
                "Seleccione institución",
            )
        ] + list(
            choices.items()
        )

        # ----------------------------------------------------
        # Una actividad existente no cambia de institución.
        # Un traslado implica un nuevo cargo.
        # ----------------------------------------------------

        if self.instance.pk:
            self.fields["cueanexo"].disabled = True

        # ====================================================
        # OBTENER VALORES DEL FORMULARIO
        # ====================================================

        def value(name):

            if self.is_bound:
                raw = self.data.get(
                    self.add_prefix(name)
                )
            else:
                raw = getattr(
                    self.instance,
                    name + "_id",
                    None,
                )

            try:
                return int(raw)

            except (TypeError, ValueError):
                return None

        # ====================================================
        # CATEGORÍA
        # ====================================================

        if self.is_bound:

            categoria = str(
                self.data.get(
                    self.add_prefix("categoria")
                )
                or ""
            ).strip().upper()

        else:

            categoria = str(
                getattr(
                    self.instance,
                    "categoria",
                    "",
                )
                or ""
            ).strip().upper()

        modalidad = value("modalidad")
        nivel = value("niveles")
        grado = value("grado_anio")

        # ====================================================
        # NIVELES
        # ====================================================

        self.fields["niveles"].queryset = (
            available_levels(modalidad)
        )

        # ====================================================
        # CATÁLOGOS DE ACTIVIDAD
        # ====================================================

        try:

            ceic, grados, secciones = (
                activity_catalogs(
                    modalidad,
                    nivel,
                    grado,
                    categoria=categoria,
                )
            )

        except ValidationError:

            from .models import (
                NomencladorCeic,
                Grado_anio,
                Secciones,
            )

            ceic = NomencladorCeic.objects.none()
            grados = Grado_anio.objects.none()
            secciones = Secciones.objects.none()

        self.fields["ceic"].queryset = ceic
        self.fields["grado_anio"].queryset = grados
        self.fields["secciones"].queryset = secciones

        # ====================================================
        # PERSONAL NO DOCENTE
        # ====================================================

        if categoria == "NO DOCENTE":

            # No corresponden estos campos.
            self.fields["grado_anio"].required = False
            self.fields["secciones"].required = False
            self.fields["espacios"].required = False

            self.fields["grado_anio"].queryset = (
                Grado_anio.objects.none()
            )

            self.fields["secciones"].queryset = (
                Secciones.objects.none()
            )

            self.fields["grado_anio"].help_text = (
                "No corresponde para personal no docente."
            )

            self.fields["secciones"].help_text = (
                "No corresponde para personal no docente."
            )

        else:

            self.fields["secciones"].help_text = (
                "Seleccione primero un grado. "
                "Se muestran las secciones del mismo par "
                "modalidad/nivel; el catálogo no contiene "
                "asignaciones por curso de cada escuela."
            )

        self.fields["f_hasta"].help_text = (
            "Deje vacío si no existe una fecha "
            "de cese conocida."
        )

    # ========================================================
    # VALIDACIÓN CUEANEXO
    # ========================================================

    def clean_cueanexo(self):

        value = self.cleaned_data["cueanexo"]

        if not user_has_cueanexo_access(
            self.user,
            value,
        ):
            raise forms.ValidationError(
                "Institución no autorizada."
            )

        return value

    # ========================================================
    # VALIDACIÓN GENERAL
    # ========================================================

    def clean(self):

        data = super().clean()

        categoria = str(
            data.get("categoria") or ""
        ).strip().upper()
        modalidad = data.get("modalidad")
        nivel = data.get("niveles")
        ceic = data.get("ceic")

        # ----------------------------------------------------
        # VALIDACIÓN MODALIDAD / NIVEL
        # ----------------------------------------------------

        if (
            modalidad
            and nivel
            and not ModalidadNivel.objects
            .filter(
                modalidad=modalidad,
                nivel=nivel,
            )
            .exists()
        ):

            self.add_error(
                "niveles",
                "El nivel no está habilitado "
                "para esta modalidad."
            )

        # ----------------------------------------------------
        # PERSONAL NO DOCENTE
        # ----------------------------------------------------

        if categoria == "NO DOCENTE":

            # Estos campos no corresponden.
            data["grado_anio"] = None
            data["secciones"] = None
            data["espacios"] = None

            # Seguridad adicional:
            # aunque modifiquen el POST manualmente,
            # solamente aceptamos CEIC con c_niv 1023-1025.

            if ceic and not (
                1023 <= ceic.c_niv <= 1025
            ):

                self.add_error(
                    "ceic",
                    "Para personal no docente "
                    "el cargo debe corresponder "
                    "a un CEIC con c_niv entre "
                    "1023 y 1025."
                )

        return data
class HorarioActividadForm(StyledForm):
    class Meta:
        model = HorarioActividad
        fields = ["dia", "hora_desde", "hora_hasta"]
        widgets = {key: forms.TimeInput(format="%H:%M", attrs={"type": "time"}) for key in ("hora_desde", "hora_hasta")}

    def clean(self):
        data = super().clean()
        if data.get("hora_desde") and data.get("hora_hasta") and data["hora_desde"] >= data["hora_hasta"]:
            self.add_error("hora_hasta", "La hora de fin debe ser posterior al inicio.")
        return data


class ConfirmacionForm(forms.Form):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    motivo = forms.CharField(min_length=5, max_length=1000, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))


class VincularPersonaForm(forms.Form):
    cuil = forms.CharField(max_length=11, label="CUIL (sin guiones)")
    dni = forms.CharField(max_length=8, label="DNI")
    apellido = forms.CharField(max_length=150)
    confirmo = forms.BooleanField(label="Confirmo que esta persona presta servicios en la institución seleccionada.")
