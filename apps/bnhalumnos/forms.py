"""ModelForms y normalizadores para la carga integral de alumnos BNH.

Las views reciben JSON desde el template, lo convierten en diccionarios y
delegan en estos formularios la limpieza, validacion y persistencia final de
Alumno, Tutor y relaciones hijas.
"""

import re
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Alumno,
    Tutor,
    ObraSocial,
    Discapacidad,
    PlanesSociales,
    Parental,
    CatalogoSinoTipo,
)
from .models import validar_cuil


TRUE_VALUES = {True, 1, "1", "true", "t", "yes", "y", "si", "s", "on"}
FALSE_VALUES = {False, 0, "0", "false", "f", "no", "n", "off", "", None}


def normalizar_booleano(valor):
    """Convierte valores de HTML/JSON a booleanos Python consistentes."""

    if isinstance(valor, str):
        valor = valor.strip().lower()
    if valor in TRUE_VALUES:
        return True
    if valor in FALSE_VALUES:
        return False
    raise ValidationError("Valor booleano invalido.")


def limpiar_digitos(valor):
    """Quita separadores y deja solo digitos para CUIL, DNI y telefonos."""

    return re.sub(r"\D", "", str(valor or ""))


def vacio_a_none(valor):
    """Convierte cadenas vacias en None para campos opcionales."""

    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


def limpiar_texto(valor, upper=False, none=False):
    """Recorta texto y aplica mayusculas o None segun la regla del campo."""

    if valor is None:
        return None if none else ""
    texto = str(valor).strip()
    if upper:
        texto = texto.upper()
    if none and not texto:
        return None
    return texto


def validar_texto_persona(valor, nombre_campo="El campo"):
    """Valida nombres/apellidos sin digitos ni caracteres fuera del patron."""

    texto = limpiar_texto(valor, upper=True)
    if not texto:
        return texto
    if re.search(r"\d", texto) or not re.fullmatch(r"[A-ZÁÉÍÓÚÜÑ\s'-]+", texto):
        raise ValidationError(f"{nombre_campo} no puede contener dígitos ni caracteres especiales.")
    return texto


def validar_solo_digitos(valor, mensaje, none=False):
    """Valida campos numericos recibidos como texto sin perder ceros iniciales."""

    texto = limpiar_texto(valor, none=none)
    if texto in (None, ""):
        return texto
    if not texto.isdigit():
        raise ValidationError(mensaje)
    return texto


def convertir_decimal(valor, zero_on_empty=False):
    """Acepta coma o punto decimal y define el valor para campos vacios."""

    valor = vacio_a_none(valor)
    if valor is None:
        return Decimal("0") if zero_on_empty else None
    return Decimal(str(valor).replace(",", "."))


def payload_tiene_datos(data, campos):
    """Detecta si una fila temporal del frontend trae algun dato util."""

    for campo in campos:
        valor = data.get(campo)
        if isinstance(valor, str):
            valor = valor.strip()
        if valor not in (None, "", [], {}):
            return True
    return False


def form_errors_to_json(form):
    """Convierte errores nativos de Django en listas simples serializables."""

    return {
        campo: [error.get("message", "") for error in errores]
        for campo, errores in form.errors.get_json_data().items()
    }


def validar_y_guardar(form):
    """Ejecuta ``is_valid`` y ``save`` para un ModelForm o lanza errores JSON."""

    # Helper central usado por views.py:
    # 1) form.is_valid() ejecuta validaciones y clean_*.
    # 2) form.save() viene de forms.ModelForm, crea/actualiza el model y Django lo persiste en la BD.
    if not form.is_valid():
        raise ValidationError(form_errors_to_json(form))
    return form.save()


def _pais_es_argentina(pais):
    """Reconoce Argentina por id historico o por texto del catalogo."""

    if not pais:
        return False
    pais_id = getattr(pais, "pk", None)
    return pais_id == 14 or "ARGENT" in str(pais).upper()


def _provincia_id_de_localidad(localidad):
    """Obtiene el id de provincia asociado a una localidad de bnhpersonas."""

    return getattr(localidad, "c_provincia_id", None)


def _validar_localidad_en_provincia(form, localidad, provincia, campo, mensaje):
    """Agrega error si la localidad elegida no pertenece a la provincia."""

    if not localidad or not provincia:
        return
    if str(_provincia_id_de_localidad(localidad) or "") != str(getattr(provincia, "pk", provincia) or ""):
        form.add_error(campo, mensaje)


def _validar_contacto(form, cleaned_data, requerido=False):
    """Valida telefono, codigo de area y banderas celular/WhatsApp.

    Para alumno el contacto es opcional; para tutor es obligatorio. En ambos
    casos, si no hay telefono completo se desactivan ``es_celular`` y
    ``whatsapp`` para evitar datos inconsistentes.
    """

    telefono = limpiar_texto(cleaned_data.get("telefono"), none=True)
    codigo_area = cleaned_data.get("codigo_area")

    if not telefono:
        if requerido:
            form.add_error("telefono", "Debe ingresar el numero de telefono.")
        if codigo_area:
            form.add_error("telefono", "Debe ingresar el numero de telefono si selecciona codigo de area.")
        if requerido and not codigo_area:
            form.add_error("codigo_area", "Debe seleccionar el codigo de area.")
        cleaned_data["telefono"] = None
        cleaned_data["whatsapp"] = False
        cleaned_data["es_celular"] = False
        return

    if not telefono.isdigit():
        form.add_error("telefono", "El campo solo puede contener numeros.")
    elif not re.fullmatch(r"\d{6,8}", telefono):
        form.add_error("telefono", "El numero local debe tener entre 6 y 8 digitos.")

    if not codigo_area:
        form.add_error("codigo_area", "Debe seleccionar el codigo de area si ingresa telefono.")

    cleaned_data["telefono"] = telefono


def _validar_cuil(valor, nombre):
    """Normaliza y valida CUIL antes de que llegue al modelo."""

    cuil = limpiar_digitos(valor)
    if not cuil:
        raise ValidationError(f"{nombre} es obligatorio.")
    if len(cuil) != 11:
        raise ValidationError(f"{nombre} debe tener 11 digitos.")
    validar_cuil(cuil)
    return cuil


def _limpiar_estado(valor):
    """Normaliza estados de relaciones hijas y usa ACTIVO por defecto."""

    return limpiar_texto(valor, upper=True) or "ACTIVO"


def _validar_rango_fechas(form, cleaned_data, campo_inicio, campo_fin):
    """Valida que una fecha final no sea anterior a su fecha inicial."""

    inicio = cleaned_data.get(campo_inicio)
    fin = cleaned_data.get(campo_fin)
    if inicio and fin and fin < inicio:
        form.add_error(campo_fin, "La fecha de fin no puede ser anterior a la fecha de inicio.")


class FlexibleBooleanField(forms.Field):
    """Campo tolerante a los distintos valores booleanos que envia HTML/JSON."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return normalizar_booleano(value)

    def validate(self, value):
        return None


class CommaDecimalField(forms.DecimalField):
    """DecimalField que acepta coma decimal y defaults para campos vacios."""

    def __init__(self, *args, zero_on_empty=False, **kwargs):
        self.zero_on_empty = zero_on_empty
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            value = Decimal("0") if self.zero_on_empty else None
        elif isinstance(value, str):
            value = value.replace(",", ".")
        return super().to_python(value)


class NullableCharField(forms.CharField):
    """CharField opcional que devuelve None en vez de cadena vacia."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return value or None


class AlumnoForm(forms.ModelForm):
    """Valida y guarda datos principales del alumno.

    ``required`` en el formulario controla lo que debe llegar desde el payload;
    ``null``/``blank`` del modelo siguen definiendo como se guarda en la base.
    """

    # ModelForm conecta formulario + modelo:
    # views.py le pasa los datos del frontend y Meta.model indica que se guardan como Alumno.
    cuil = forms.CharField(required=True)
    email = forms.EmailField(required=False, max_length=150)
    telefono = NullableCharField(max_length=8)
    es_celular = FlexibleBooleanField()
    whatsapp = FlexibleBooleanField()
    talla = CommaDecimalField(max_digits=5, decimal_places=2, zero_on_empty=True)
    peso = CommaDecimalField(max_digits=5, decimal_places=2, zero_on_empty=True)

    class Meta:
        # Aca esta la union con models.py. Al llamar form.save(), Django usa models.Alumno.
        model = Alumno
        fields = [
            "apellidos",
            "nombres",
            "tipo_doc",
            "nro_doc",
            "cuil",
            "fecha_nacimiento",
            "sexo",
            "pais_nacimiento",
            "prov_nacimiento",
            "lugar_nacimiento",
            "loc_nacimiento",
            "pais_residencia",
            "prov_residencia",
            "loc_residencia",
            "est_civil",
            "pertenece_pueblo_indigena",
            "comunidad_originaria",
            "lengua_originaria",
            "tiene_discapacidad",
            "tiene_ppi",
            "codigo_area",
            "telefono",
            "es_celular",
            "whatsapp",
            "email",
            "talla",
            "peso",
            "observaciones",
        ]

    def clean_apellidos(self):
        return validar_texto_persona(self.cleaned_data.get("apellidos"))

    def clean_nombres(self):
        return validar_texto_persona(self.cleaned_data.get("nombres"))

    def clean_nro_doc(self):
        return validar_solo_digitos(
            self.cleaned_data.get("nro_doc"),
            "El número de documento es inválido. Ingrese solo números.",
        )

    def clean_cuil(self):
        return _validar_cuil(self.cleaned_data.get("cuil"), "CUIL del alumno")

    def clean_telefono(self):
        return validar_solo_digitos(
            self.cleaned_data.get("telefono"),
            "El campo solo puede contener números.",
            none=True,
        )

    def clean_observaciones(self):
        return limpiar_texto(self.cleaned_data.get("observaciones"))

    def clean_lugar_nacimiento(self):
        valor = limpiar_texto(self.cleaned_data.get("lugar_nacimiento"), upper=True)
        if re.search(r"\d", valor):
            raise ValidationError(
                "Este campo no acepta números. Si el nombre del lugar tuviera un número, ingresarlo con caracteres, por ejemplo: Cuatro de Julio."
            )
        return valor

    def clean(self):
        """Aplica validaciones cruzadas de nacimiento, residencia y contacto."""

        cleaned_data = super().clean()
        pais_nacimiento = cleaned_data.get("pais_nacimiento")
        # Argentina requiere provincia/localidad del catalogo; pais extranjero
        # requiere texto libre y limpia las ForeignKey locales.
        if _pais_es_argentina(pais_nacimiento):
            cleaned_data["lugar_nacimiento"] = ""
            if not cleaned_data.get("prov_nacimiento"):
                self.add_error("prov_nacimiento", "La provincia de nacimiento es obligatoria para Argentina.")
            if not cleaned_data.get("loc_nacimiento"):
                self.add_error("loc_nacimiento", "La localidad de nacimiento es obligatoria para Argentina.")
            _validar_localidad_en_provincia(
                self,
                cleaned_data.get("loc_nacimiento"),
                cleaned_data.get("prov_nacimiento"),
                "loc_nacimiento",
                "La localidad de nacimiento no corresponde a la provincia seleccionada.",
            )
        else:
            cleaned_data["prov_nacimiento"] = None
            cleaned_data["loc_nacimiento"] = None
            if pais_nacimiento and not cleaned_data.get("lugar_nacimiento"):
                self.add_error(
                    "lugar_nacimiento",
                    "El lugar de nacimiento es obligatorio cuando el país de nacimiento no es Argentina.",
                )

        if not cleaned_data.get("pais_residencia"):
            self.add_error("pais_residencia", "Debe seleccionar el pais de residencia.")
        if not cleaned_data.get("prov_residencia"):
            self.add_error("prov_residencia", "Debe seleccionar la provincia de residencia.")
        if not cleaned_data.get("loc_residencia"):
            self.add_error("loc_residencia", "Debe seleccionar la localidad de residencia.")
        _validar_localidad_en_provincia(
            self,
            cleaned_data.get("loc_residencia"),
            cleaned_data.get("prov_residencia"),
            "loc_residencia",
            "La localidad de residencia no corresponde a la provincia seleccionada.",
        )

        # Comunidad originaria solo se conserva cuando la respuesta es SI.
        pertenece = cleaned_data.get("pertenece_pueblo_indigena")
        comunidad = cleaned_data.get("comunidad_originaria")
        if pertenece and pertenece.codigo == CatalogoSinoTipo.SI:
            if not comunidad:
                self.add_error(
                    "comunidad_originaria",
                    "Debe indicar la comunidad originaria cuando pertenece a pueblo indígena.",
                )
        else:
            cleaned_data["comunidad_originaria"] = None

        _validar_contacto(self, cleaned_data)
        if not cleaned_data.get("es_celular"):
            cleaned_data["whatsapp"] = False
        return cleaned_data


class TutorForm(forms.ModelForm):
    """Valida y guarda tutores reutilizables por CUIL o documento."""

    # TutorForm funciona igual que AlumnoForm, pero guarda/actualiza un models.Tutor.
    cuil_tutor = forms.CharField(required=True)
    mail = forms.EmailField(required=False)
    telefono = forms.CharField(required=True, max_length=8)
    es_celular = FlexibleBooleanField()
    whatsapp = FlexibleBooleanField()

    class Meta:
        # Aca esta la union con models.Tutor para que form.save() persista el tutor.
        model = Tutor
        fields = [
            "cuil_tutor",
            "apellidos",
            "nombres",
            "tipo_doc",
            "nro_doc",
            "fecha_nac",
            "nacionalidad",
            "pais_nac",
            "nivel_formacion",
            "ocupacion",
            "prov_resid",
            "loc_resid",
            "cod_postal",
            "calle",
            "nro",
            "piso",
            "dpto",
            "mail",
            "codigo_area",
            "telefono",
            "es_celular",
            "whatsapp",
        ]

    def clean_cuil_tutor(self):
        return _validar_cuil(self.cleaned_data.get("cuil_tutor"), "CUIL del tutor")

    def clean_apellidos(self):
        return validar_texto_persona(self.cleaned_data.get("apellidos"))

    def clean_nombres(self):
        return validar_texto_persona(self.cleaned_data.get("nombres"))

    def clean_nro_doc(self):
        return validar_solo_digitos(
            self.cleaned_data.get("nro_doc"),
            "El número de documento es inválido. Ingrese solo números.",
        )

    def clean_ocupacion(self):
        return limpiar_texto(self.cleaned_data.get("ocupacion"))

    def clean_cod_postal(self):
        return limpiar_texto(self.cleaned_data.get("cod_postal"))

    def clean_calle(self):
        return limpiar_texto(self.cleaned_data.get("calle"))

    def clean_nro(self):
        return limpiar_texto(self.cleaned_data.get("nro"))

    def clean_piso(self):
        return limpiar_texto(self.cleaned_data.get("piso"))

    def clean_dpto(self):
        return limpiar_texto(self.cleaned_data.get("dpto"))

    def clean_telefono(self):
        return validar_solo_digitos(
            self.cleaned_data.get("telefono"),
            "El campo solo puede contener números.",
            none=True,
        )

    def clean(self):
        """Valida residencia y contacto obligatorio del tutor."""

        cleaned_data = super().clean()
        if not cleaned_data.get("prov_resid"):
            self.add_error("prov_resid", "Debe seleccionar la provincia de residencia del tutor.")
        if not cleaned_data.get("loc_resid"):
            self.add_error("loc_resid", "Debe seleccionar la localidad de residencia del tutor.")
        _validar_localidad_en_provincia(
            self,
            cleaned_data.get("loc_resid"),
            cleaned_data.get("prov_resid"),
            "loc_resid",
            "La localidad de residencia del tutor no corresponde a la provincia seleccionada.",
        )

        _validar_contacto(self, cleaned_data, requerido=True)
        if not cleaned_data.get("es_celular"):
            cleaned_data["whatsapp"] = False
        return cleaned_data


class ObraSocialForm(forms.ModelForm):
    """Valida una obra social temporal antes de asociarla al alumno."""

    estado = forms.CharField(required=False)

    class Meta:
        model = ObraSocial
        fields = [
            "id_alumno",
            "tipo_obra",
            "nombre_obra",
            "fecha_inicio",
            "fecha_fin",
            "descripcion",
            "estado",
        ]

    def clean_descripcion(self):
        return limpiar_texto(self.cleaned_data.get("descripcion"))

    def clean_estado(self):
        return _limpiar_estado(self.cleaned_data.get("estado"))

    def clean(self):
        """Valida el rango de vigencia de la cobertura."""

        cleaned_data = super().clean()
        _validar_rango_fechas(self, cleaned_data, "fecha_inicio", "fecha_fin")
        return cleaned_data


class DiscapacidadForm(forms.ModelForm):
    """Valida un detalle de discapacidad enviado desde el modal."""

    porcentaje = CommaDecimalField(max_digits=5, decimal_places=2, required=False)

    class Meta:
        model = Discapacidad
        fields = [
            "id_alumno",
            "id_discapacidad",
            "fecha_inicio",
            "fecha_fin",
            "porcentaje",
            "observaciones",
            "certificado_cud",
        ]

    def clean_observaciones(self):
        return limpiar_texto(self.cleaned_data.get("observaciones"))

    def clean_certificado_cud(self):
        return limpiar_texto(self.cleaned_data.get("certificado_cud"))

    def clean_porcentaje(self):
        porcentaje = self.cleaned_data.get("porcentaje")
        if porcentaje is None:
            return porcentaje
        if porcentaje < Decimal("1") or porcentaje > Decimal("100"):
            raise ValidationError("El porcentaje de discapacidad debe estar entre 1 y 100.")
        return porcentaje

    def clean(self):
        """Valida fechas del detalle de discapacidad."""

        cleaned_data = super().clean()
        _validar_rango_fechas(self, cleaned_data, "fecha_inicio", "fecha_fin")
        return cleaned_data


class PlanesSocialesForm(forms.ModelForm):
    """Valida beneficios o planes sociales asociados al alumno."""

    monto = CommaDecimalField(max_digits=12, decimal_places=2, zero_on_empty=True)
    estado = forms.CharField(required=False)

    class Meta:
        model = PlanesSociales
        fields = [
            "id_alumno",
            "id_beneficio",
            "descripcion",
            "fecha_desde",
            "fecha_hasta",
            "monto",
            "estado",
            "observaciones",
        ]

    def clean_descripcion(self):
        return limpiar_texto(self.cleaned_data.get("descripcion"))

    def clean_estado(self):
        return _limpiar_estado(self.cleaned_data.get("estado"))

    def clean_observaciones(self):
        return limpiar_texto(self.cleaned_data.get("observaciones"))

    def clean(self):
        """Valida fechas del plan o beneficio social."""

        cleaned_data = super().clean()
        _validar_rango_fechas(self, cleaned_data, "fecha_desde", "fecha_hasta")
        return cleaned_data


class ParentalForm(forms.ModelForm):
    """Guarda la relacion entre Alumno, Tutor y parentesco."""

    class Meta:
        # Guarda la relacion entre alumno y tutor: id_alumno + id_tutor + parentesco.
        model = Parental
        fields = [
            "id_alumno",
            "id_tutor",
            "parentesco",
            "observaciones",
        ]

    def clean_observaciones(self):
        return limpiar_texto(self.cleaned_data.get("observaciones"))
