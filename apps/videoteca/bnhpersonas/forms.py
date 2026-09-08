import re
from django import forms
from django.core.exceptions import ValidationError
from .models import Personas, RegistroActividades, Localidades, HorarioActividad, ModalidadNivel, validar_cuil, validar_dni
from .domain.access import scoped_offers, user_has_cueanexo_access
from .domain.catalogs import activity_catalogs


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
    cueanexo = forms.ChoiceField(label="Institución / CUEANEXO")
    operation_id = forms.UUIDField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = RegistroActividades
        fields = ["cueanexo", "categoria", "modalidad", "niveles", "sit_revista", "cond_actividad", "designacion", "t_designacion", "ceic", "grado_anio", "turno", "secciones", "espacios", "f_desde", "f_hasta", "carga_horaria", "estado", "funciones", "f_desde_funciones", "f_hasta_funciones"]
        labels = {"categoria": "Tipo de personal", "niveles": "Nivel", "sit_revista": "Situación de revista", "cond_actividad": "Condición de actividad", "t_designacion": "Tipo de designación", "ceic": "Cargo / CEIC", "f_desde": "Inicio del cargo", "f_hasta": "Fin del cargo (si corresponde)", "f_desde_funciones": "Inicio de funciones", "f_hasta_funciones": "Fin de funciones (si corresponde)"}

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["operation_id"].required = not bool(self.instance.pk)
        self.initial["operation_id"] = self.instance.uuid
        choices = {}
        for cue, name in scoped_offers(user).order_by("cueanexo_str", "nom_est").values_list("cueanexo_str", "nom_est"):
            choices.setdefault(cue, f"{cue} — {name}")
        self.fields["cueanexo"].choices = [("", "Seleccione institución")] + list(choices.items())
        # Traslados son un nuevo cargo; nunca se mueven horarios de una escuela a otra.
        if self.instance.pk:
            self.fields["cueanexo"].disabled = True
        def value(name):
            raw = self.data.get(self.add_prefix(name)) if self.is_bound else getattr(self.instance, name + "_id", None)
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
        try:
            ceic, grados, secciones = activity_catalogs(value("modalidad"), value("niveles"))
        except ValidationError:
            from .models import NomencladorCeic, Grado_anio, Secciones
            ceic, grados, secciones = NomencladorCeic.objects.none(), Grado_anio.objects.none(), Secciones.objects.none()
        self.fields["ceic"].queryset = ceic
        self.fields["grado_anio"].queryset = grados
        self.fields["secciones"].queryset = secciones
        self.fields["f_hasta"].help_text = "Deje vacío si no existe una fecha de cese conocida."

    def clean_cueanexo(self):
        value = self.cleaned_data["cueanexo"]
        if not user_has_cueanexo_access(self.user, value):
            raise forms.ValidationError("Institución no autorizada.")
        return value

    def clean(self):
        data = super().clean()
        modalidad, nivel = data.get("modalidad"), data.get("niveles")
        if modalidad and nivel and not ModalidadNivel.objects.filter(modalidad=modalidad, nivel=nivel).exists():
            self.add_error("niveles", "El nivel no está habilitado para esta modalidad.")
        if data.get("categoria") == "NO DOCENTE":
            for name in ("grado_anio", "secciones", "espacios"):
                data[name] = None
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
