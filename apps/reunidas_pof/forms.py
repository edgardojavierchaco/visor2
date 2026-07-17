from decimal import Decimal
import re

from django import forms
from django.utils import timezone

from .models import CargoPof, LoteCargaPof, ProyectosEspecialesPof, ReunidaPof, SnapshotPadronLocalizacionPof
from .services.niveles_service import normalizar_nivel
from .services.padron_materializadas_service import (
    obtener_catalogos_padron_ingreso_manual_pof,
    normalizar_nivel_oferta_padron,
)


TIPOS_CABECERA = (
    ("REUNIDA", "Reunida"),
    ("PROYECTO_ESPECIAL", "Proyecto Especial"),
)

DUPLICADO_REUNIDA_POF = "Ya existe una Reunida POF para ese año y nivel."
MODO_PADRON_PADRON = "PADRON"
MODO_PADRON_MANUAL_CONTROLADO = "MANUAL_CONTROLADO"
MODOS_PADRON_VALIDOS = {MODO_PADRON_PADRON, MODO_PADRON_MANUAL_CONTROLADO}
ESTADOS_MANUALES_PADRON = ("Activo", "Baja")
TEXTO_SEGURO_RE = re.compile(r"^[^\x00-\x1f\x7f<>]*$")
MENSAJE_CATALOGO_INVALIDO = "El valor seleccionado no pertenece a las opciones disponibles."
SIN_INFORMACION = "Sin información"
MENSAJE_INGRESO_MANUAL_SIN_CUEANEXO = (
    "El ingreso manual no debe cargar CUE, Anexo ni CUEANEXO. Use Buscar en padrón."
)
MENSAJE_INGRESO_MANUAL_SIN_OFERTA = (
    "El ingreso manual por CUOF no admite oferta educativa ni estados de oferta o establecimiento."
)
CAMPOS_IDENTIDAD_PADRON_MANUAL = (
    "cue",
    "anexo",
    "cueanexo",
    "padron_cueanexo",
    "cue_anexo",
)

CAMPOS_CATALOGOS_MANUAL = (
    "region",
    "localidad",
    "departamento",
    "acronimo",
    "ambito",
    "categoria",
    "jornada",
)
CAMPOS_OFERTA_PADRON_MANUAL_PROHIBIDOS = (
    "oferta",
    "oferta_real",
    "estado_oferta_padron",
    "est_oferta",
    "estado_establecimiento_padron",
    "estado_est",
)
MENSAJES_CAMPOS_CATALOGO_MANUAL = {
    "region": "Debe seleccionar una región válida.",
    "localidad": "Debe seleccionar una localidad válida.",
    "departamento": "Debe seleccionar un departamento válido.",
    "acronimo": "Debe seleccionar un acrónimo válido.",
    "ambito": "Debe seleccionar un ámbito válido.",
    "categoria": "Debe seleccionar una categoría válida.",
    "jornada": "Debe seleccionar una jornada válida.",
}


def _serializar_errores_form(form):
    errores = {}
    for campo, lista_errores in form.errors.as_data().items():
        errores[campo] = []
        for error in lista_errores:
            errores[campo].extend(error.messages)
    return errores


def _texto(valor):
    return str(valor or "").strip()


def _texto_seguro(valor, max_length, obligatorio=False, mensaje_obligatorio="Este campo es obligatorio."):
    texto = _texto(valor)
    errores = []
    if not texto:
        if obligatorio:
            errores.append(mensaje_obligatorio)
        return texto, errores
    if len(texto) > max_length:
        errores.append(f"El texto no puede superar {max_length} caracteres.")
    if not TEXTO_SEGURO_RE.fullmatch(texto):
        errores.append("El texto contiene caracteres no permitidos.")
    return texto, errores


def _normalizar_estado_manual(valor):
    texto = _texto(valor) or ESTADOS_MANUALES_PADRON[0]
    for estado in ESTADOS_MANUALES_PADRON:
        if texto.lower() == estado.lower():
            return estado, []
    return texto, ["El estado seleccionado no es válido."]


def _es_placeholder_manual(valor):
    texto = _texto(valor).lower()
    return (
        not texto
        or texto.startswith("seleccioná")
        or texto.startswith("selecciona")
        or texto.startswith("seleccione")
    )


def _campos_identidad_padron_manual_informados(padron):
    """
    Detecta identificadores oficiales prohibidos en el ingreso manual controlado.

    - Revisa los aliases de CUE, Anexo y CUEANEXO aceptados por otros flujos.
    - Considera informado cualquier valor no vacío, aunque no tenga formato válido.
    - Permite rechazar el payload antes de normalizar identidad oficial.
    """
    if not isinstance(padron, dict):
        return []
    return [
        campo
        for campo in CAMPOS_IDENTIDAD_PADRON_MANUAL
        if _texto(padron.get(campo))
    ]


def _campos_oferta_padron_manual_informados(padron):
    """
    Detecta datos oficiales de oferta prohibidos en el ingreso manual por CUOF.

    - Revisa oferta educativa y estados de oferta/establecimiento.
    - Considera informado cualquier valor no vacío enviado en el payload.
    - Permite rechazar manipulaciones antes de construir el padrón manual limpio.
    """
    if not isinstance(padron, dict):
        return []
    return [
        campo
        for campo in CAMPOS_OFERTA_PADRON_MANUAL_PROHIBIDOS
        if _texto(padron.get(campo))
    ]


def _validar_proyecto_especial_id(valor):
    proyecto_id = _texto(valor)
    if not proyecto_id or not proyecto_id.isdigit():
        return None, ["Debe seleccionar un Proyecto Especial POF válido."]
    if not ProyectosEspecialesPof.objects.filter(pk=proyecto_id).exists():
        return None, ["Debe seleccionar un Proyecto Especial POF válido."]
    return int(proyecto_id), []


class ReunidaPofForm(forms.ModelForm):
    anio = forms.IntegerField(
        label="Año",
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "pof-form-control",
            "inputmode": "numeric",
            "pattern": "[0-9]{4}",
            "placeholder": "Ej: 2026",
            "autocomplete": "off",
            "data-pof-anio-input": "true",
        }),
        error_messages={
            "required": "El año es obligatorio.",
            "invalid": "El año debe tener 4 dígitos numéricos.",
        },
    )
    nivel = forms.ChoiceField(
        label="Nivel",
        choices=[("", "Seleccioná un nivel")] + list(ReunidaPof.Nivel.choices),
    )

    class Meta:
        model = ReunidaPof
        fields = ["anio", "nivel"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        anio_maximo = timezone.localdate().year + 1
        self.fields["anio"].widget.attrs.update({"max": str(anio_maximo)})
        self.fields["nivel"].widget.attrs.update({"class": "pof-form-select"})

    def clean_anio(self):
        anio = self.cleaned_data.get("anio")
        if anio is None:
            return anio

        anio_texto = str(anio)
        if not anio_texto.isdigit() or len(anio_texto) != 4:
            raise forms.ValidationError("El año debe tener 4 dígitos numéricos.")

        anio_maximo = timezone.localdate().year + 1

        if anio > anio_maximo:
            raise forms.ValidationError("El año no puede superar el año próximo.")

        return anio

    def clean(self):
        cleaned_data = super().clean()
        anio = cleaned_data.get("anio")
        nivel = cleaned_data.get("nivel")

        if anio and nivel and ReunidaPof.objects.filter(anio=anio, nivel=nivel).exists():
            raise forms.ValidationError(DUPLICADO_REUNIDA_POF)

        return cleaned_data


class ProyectoEspecialPofForm(forms.ModelForm):
    anio = forms.IntegerField(
        label="Año",
        required=True,
        widget=forms.NumberInput(attrs={
            "class": "pof-form-control",
            "inputmode": "numeric",
            "pattern": "[0-9]{4}",
            "placeholder": "Ej: 2026",
            "autocomplete": "off",
        }),
        error_messages={
            "required": "El año es obligatorio.",
            "invalid": "El año debe tener 4 dígitos numéricos.",
        },
    )

    class Meta:
        model = ProyectosEspecialesPof
        fields = ["anio", "nombre", "resolucion", "observacion", "proyecto_base_anterior"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "pof-form-control"}),
            "resolucion": forms.TextInput(attrs={"class": "pof-form-control"}),
            "observacion": forms.Textarea(attrs={"class": "pof-form-control", "rows": 3}),
            "proyecto_base_anterior": forms.Select(attrs={"class": "pof-form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["nombre"].required = True
        self.fields["resolucion"].required = False
        self.fields["observacion"].required = False
        self.fields["proyecto_base_anterior"].required = False
        self.fields["proyecto_base_anterior"].queryset = ProyectosEspecialesPof.objects.exclude(
            pk=self.instance.pk
        ).order_by("-anio", "nombre")

    def clean_anio(self):
        anio = self.cleaned_data.get("anio")
        if anio is None:
            return anio

        anio_texto = str(anio)
        if not anio_texto.isdigit() or len(anio_texto) != 4:
            raise forms.ValidationError("El año debe tener 4 dígitos numéricos.")

        return anio


def _cueanexo_desde_padron(padron):
    return _texto(
        padron.get("padron_cueanexo")
        or padron.get("cueanexo")
        or padron.get("cue_anexo")
    )


def _cuof_desde_padron(padron):
    return _texto(padron.get("cuof_loc") or padron.get("cuof"))


def _normalizar_origen_datos(valor, cabecera_tipo, cueanexo):
    if cueanexo:
        return SnapshotPadronLocalizacionPof.OrigenDatos.PADRON
    if cabecera_tipo == "PROYECTO_ESPECIAL":
        return SnapshotPadronLocalizacionPof.OrigenDatos.MANUAL

    origen = _texto(valor).upper()
    opciones = {opcion for opcion, _ in SnapshotPadronLocalizacionPof.OrigenDatos.choices}
    if origen in opciones:
        return origen
    return SnapshotPadronLocalizacionPof.OrigenDatos.PADRON


class CargoPofInputForm(forms.Form):
    """
    Valida la entrada editable y las confirmaciones funcionales de cada cargo POF.

    - Exige CEIC, cantidad y unidad como entrada mínima confiable.
    - Conserva la observación opcional ingresada por el usuario.
    - Conserva la confirmación explícita cuando el CEIC fue elegido desde "Otros".
    - Cargo, puntos y snapshot se resuelven después desde la fuente oficial CEIC.
    """
    ceic = forms.IntegerField(min_value=1)
    ceic_fuera_sugerencia = forms.BooleanField(required=False)
    observacion = forms.CharField(required=False)
    cantidad = forms.IntegerField(min_value=0)
    unidad_cantidad = forms.ChoiceField(
        choices=CargoPof.UnidadCantidad.choices
    )


class GuardarCargaPofForm(forms.Form):
    cabecera_tipo = forms.ChoiceField(choices=TIPOS_CABECERA)
    anio = forms.IntegerField(required=False)
    nivel = forms.CharField(required=False)
    proyecto_especial_id = forms.IntegerField(required=False, min_value=1)
    tipo_operacion = forms.ChoiceField(choices=LoteCargaPof.TipoOperacion.choices, required=False)
    observacion = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        cabecera_tipo = cleaned_data.get("cabecera_tipo")

        tipo_operacion = cleaned_data.get("tipo_operacion")
        if not tipo_operacion:
            cleaned_data["tipo_operacion"] = LoteCargaPof.TipoOperacion.ALTA

        if cabecera_tipo == "REUNIDA":
            anio = cleaned_data.get("anio")
            if not anio:
                self.add_error("anio", "El año es obligatorio para Reunidas POF.")
            else:
                anio_texto = str(anio)
                if not anio_texto.isdigit() or len(anio_texto) != 4:
                    self.add_error("anio", "El año debe tener 4 dígitos numéricos.")

            nivel = _texto(cleaned_data.get("nivel"))
            nivel_normalizado = ""
            if not nivel:
                self.add_error("nivel", "El nivel es obligatorio para Reunidas POF.")
            else:
                nivel_normalizado = normalizar_nivel(nivel)
                if not nivel_normalizado:
                    self.add_error("nivel", "El nivel ingresado no es válido.")
                else:
                    cleaned_data["nivel"] = nivel_normalizado

            if anio and nivel_normalizado and not self.errors:
                if not ReunidaPof.objects.filter(anio=anio, nivel=nivel_normalizado).exists():
                    self.add_error(
                        "reunida",
                        "No existe una Reunida POF para ese año y nivel. Primero debe crearla.",
                    )

        if cabecera_tipo == "PROYECTO_ESPECIAL" and not cleaned_data.get("proyecto_especial_id"):
            self.add_error(
                "proyecto_especial_id",
                "El proyecto especial es obligatorio para Proyectos Especiales POF.",
            )

        cleaned_data["observacion"] = _texto(cleaned_data.get("observacion"))
        return cleaned_data


def validar_payload_guardar_carga(datos):
    """
    Valida la estructura mínima del request de alta de cargos.

    - Asegura cabecera, padrón y lista mínima de cargos editables.
    - No conserva campos derivados del CEIC enviados por frontend.
    - La resolución oficial de cargo, puntos y snapshot ocurre luego en guardado.
    """
    if not isinstance(datos, dict):
        return {
            "ok": False,
            "errores": {"payload": ["El cuerpo de la solicitud debe ser un objeto JSON."]},
        }

    form = GuardarCargaPofForm(datos)
    errores = {}

    if not form.is_valid():
        errores.update(_serializar_errores_form(form))

    cabecera_tipo = datos.get("cabecera_tipo")
    padron = datos.get("padron")
    if not isinstance(padron, dict):
        errores["padron"] = ["El bloque padron es obligatorio y debe ser un objeto."]
        padron = {}

    cueanexo = _cueanexo_desde_padron(padron)
    cuof = _cuof_desde_padron(padron)

    if cabecera_tipo == "REUNIDA":
        if not cueanexo:
            errores["cueanexo"] = ["El CUEANEXO es obligatorio para Reunidas POF."]
        elif not re.fullmatch(r"\d{9}", cueanexo):
            errores["cueanexo"] = ["El CUEANEXO debe tener 9 dígitos."]

    if not cuof:
        errores["cuof"] = ["El CUOF es obligatorio."]

    cargos = datos.get("cargos")
    cargos_limpios = []
    if not isinstance(cargos, list) or not cargos:
        errores["cargos"] = ["La lista de cargos es obligatoria y no puede estar vacía."]
    else:
        errores_cargos = {}
        for indice, cargo in enumerate(cargos):
            if not isinstance(cargo, dict):
                errores_cargos[indice] = {"cargo": ["Cada cargo debe ser un objeto."]}
                continue

            cargo_form = CargoPofInputForm(cargo)
            if not cargo_form.is_valid():
                errores_cargos[indice] = _serializar_errores_form(cargo_form)
                continue

            cargo_limpio = cargo_form.cleaned_data
            cargo_limpio["observacion"] = _texto(cargo_limpio.get("observacion"))
            cargos_limpios.append(cargo_limpio)

        if errores_cargos:
            errores["cargos"] = errores_cargos

    if errores:
        return {"ok": False, "errores": errores}

    cabecera_limpia = form.cleaned_data
    padron_limpio = dict(padron)
    padron_limpio["cueanexo"] = cueanexo
    padron_limpio["padron_cueanexo"] = cueanexo
    padron_limpio["cuof_loc"] = cuof
    padron_limpio.setdefault("estado_loc", "")
    padron_limpio.setdefault("est_oferta", "")
    padron_limpio.setdefault("estado_est", "")
    padron_limpio["nivel_oferta"] = normalizar_nivel_oferta_padron(padron_limpio)
    padron_limpio["origen_datos"] = _normalizar_origen_datos(
        padron_limpio.get("origen_datos"),
        cabecera_limpia["cabecera_tipo"],
        cueanexo,
    )

    return {
        "ok": True,
        "datos": {
            "cabecera_tipo": cabecera_limpia["cabecera_tipo"],
            "anio": cabecera_limpia.get("anio"),
            "nivel": cabecera_limpia.get("nivel") or "",
            "proyecto_especial_id": cabecera_limpia.get("proyecto_especial_id"),
            "tipo_operacion": cabecera_limpia["tipo_operacion"],
            "observacion": cabecera_limpia.get("observacion", ""),
            "padron": padron_limpio,
            "cargos": cargos_limpios,
        },
    }


def _validar_catalogos_manual_pof(padron):
    """
    Valida los catálogos opcionales del ingreso manual controlado.

    - Normaliza vacíos y placeholders como "Sin información".
    - Si hay un valor real, exige que pertenezca al catálogo materializado vigente.
    - Devuelve valores limpios solo para los campos válidos.
    """
    try:
        catalogos = obtener_catalogos_padron_ingreso_manual_pof()
    except Exception:
        return {}, {"catalogos": ["No se pudieron cargar las opciones disponibles."]}

    valores = {}
    errores = {}

    for campo in CAMPOS_CATALOGOS_MANUAL:
        valor = _texto(padron.get(campo))
        opciones = set(catalogos.get(campo, []))
        if _es_placeholder_manual(valor) or valor.lower() == SIN_INFORMACION.lower():
            valores[campo] = SIN_INFORMACION
            continue
        if valor not in opciones:
            errores[campo] = [MENSAJES_CAMPOS_CATALOGO_MANUAL[campo]]
        valores[campo] = valor

    return valores, errores


def _armar_padron_manual_controlado(valores):
    """
    Construye el padrón mínimo permitido para Proyecto Especial manual.

    - Conserva solo referencia CUOF y catálogos institucionales manuales.
    - Mantiene vacía la identidad oficial porque no hay CUEANEXO validado.
    - Mantiene vacíos oferta y estados oficiales para no simular padrón.
    """
    cueanexo = valores.get("cueanexo", "")
    cue = valores.get("cue", "")
    anexo = valores.get("anexo", "")
    cuof = valores["cuof"]
    cui = valores["cui"]
    nombre = valores["nombre"]
    numero = valores["numero"]
    estado_localizacion = valores["estado_localizacion_padron"]

    return {
        "cueanexo": cueanexo,
        "padron_cueanexo": cueanexo,
        "cue_anexo": cueanexo,
        "cue": cue,
        "anexo": anexo,
        "cuof": cuof,
        "cuof_loc": cuof,
        "cui": cui,
        "cui_loc": cui,
        "nombre_establecimiento": nombre,
        "nom_est": nombre,
        "numero_establecimiento": numero,
        "nro_est": numero,
        "region": valores["region"],
        "region_loc": valores["region"],
        "localidad": valores["localidad"],
        "departamento": valores["departamento"],
        "oferta": "",
        "oferta_real": "",
        "acronimo": valores["acronimo"],
        "ambito": valores["ambito"],
        "categoria": valores["categoria"],
        "jornada": valores["jornada"],
        "estado_loc": estado_localizacion,
        "est_oferta": "",
        "estado_est": "",
        "estado_localizacion_padron": estado_localizacion,
        "estado_oferta_padron": "",
        "estado_establecimiento_padron": "",
        "origen_datos": SnapshotPadronLocalizacionPof.OrigenDatos.MANUAL,
        "estado_padron": SnapshotPadronLocalizacionPof.EstadoPadron.NO_ENCONTRADO,
    }


def _validar_cue_anexo_manual(padron):
    cue = _texto(padron.get("cue"))
    anexo = _texto(padron.get("anexo"))
    cueanexo = _texto(
        padron.get("padron_cueanexo")
        or padron.get("cueanexo")
        or padron.get("cue_anexo")
    )
    errores = {}

    if cue and not re.fullmatch(r"\d{7}", cue):
        errores["cue"] = ["El CUE debe tener 7 dígitos."]
    if anexo and not re.fullmatch(r"\d{2}", anexo):
        errores["anexo"] = ["El Anexo debe tener 2 dígitos."]
    if cueanexo and not re.fullmatch(r"\d{9}", cueanexo):
        errores["cueanexo"] = ["El CUEANEXO debe tener 9 dígitos."]

    if (cue and not anexo) or (anexo and not cue):
        errores["cueanexo"] = ["Para informar CUE o Anexo debe completar ambos campos."]

    if errores:
        return "", "", "", errores

    if cue and anexo:
        construido = f"{cue}{anexo}"
        if cueanexo and cueanexo != construido:
            return "", "", "", {
                "cueanexo": ["El CUEANEXO debe coincidir con CUE + Anexo."]
            }
        cueanexo = construido
    elif cueanexo:
        cue = cueanexo[:7]
        anexo = cueanexo[7:]

    return cue, anexo, cueanexo, {}


def _validar_estado_manual(valor):
    """
    Valida el estado de localización opcional del ingreso manual controlado.

    - Normaliza vacíos y placeholders como "Sin información".
    - Conserva la normalización existente de estados manuales permitidos.
    """
    texto = _texto(valor)
    if _es_placeholder_manual(texto) or texto.lower() == SIN_INFORMACION.lower():
        return SIN_INFORMACION, []
    return _normalizar_estado_manual(valor)


def _validar_payload_manual_proyecto_especial(datos, proyecto_id):
    """
    Valida el ingreso manual controlado de Proyecto Especial.

    - Exige únicamente CUOF y normaliza los demás datos manuales opcionales.
    - Rechaza cualquier intento de informar CUE, Anexo o CUEANEXO manualmente.
    - Fuerza identidad oficial vacía antes de delegar al validador común.
    """
    errores = {}
    padron = datos.get("padron")
    if not isinstance(padron, dict):
        errores["padron"] = ["El bloque padron es obligatorio y debe ser un objeto."]
        padron = {}

    if _campos_identidad_padron_manual_informados(padron):
        errores["padron"] = [MENSAJE_INGRESO_MANUAL_SIN_CUEANEXO]
    if _campos_oferta_padron_manual_informados(padron):
        errores["oferta"] = [MENSAJE_INGRESO_MANUAL_SIN_OFERTA]

    cuof, errores_cuof = _texto_seguro(
        padron.get("cuof") or padron.get("cuof_loc"),
        100,
        obligatorio=True,
        mensaje_obligatorio="El CUOF es obligatorio.",
    )
    if errores_cuof:
        errores["cuof"] = errores_cuof

    cui, errores_cui = _texto_seguro(
        padron.get("cui") or padron.get("cui_loc"),
        100,
    )
    if errores_cui:
        errores["cui"] = errores_cui
    cui = cui or SIN_INFORMACION

    nombre, errores_nombre = _texto_seguro(
        padron.get("nombre_establecimiento") or padron.get("nom_est"),
        255,
    )
    if errores_nombre:
        errores["nombre_establecimiento"] = errores_nombre
    nombre = nombre or SIN_INFORMACION

    numero, errores_numero = _texto_seguro(
        padron.get("numero_establecimiento") or padron.get("nro_est"),
        100,
    )
    if errores_numero:
        errores["numero_establecimiento"] = errores_numero
    numero = numero or SIN_INFORMACION

    valores_catalogo, errores_catalogo = _validar_catalogos_manual_pof(padron)
    errores.update(errores_catalogo)

    estado_localizacion, errores_estado_localizacion = _validar_estado_manual(
        padron.get("estado_localizacion_padron") or padron.get("estado_loc")
    )
    if errores_estado_localizacion:
        errores["estado_localizacion_padron"] = errores_estado_localizacion

    if errores:
        return {"ok": False, "errores": errores}

    valores_manual = {
        **valores_catalogo,
        "cuof": cuof,
        "cue": "",
        "anexo": "",
        "cueanexo": "",
        "cui": cui,
        "nombre": nombre,
        "numero": numero,
        "estado_localizacion_padron": estado_localizacion,
    }
    payload = {
        **datos,
        "cabecera_tipo": "PROYECTO_ESPECIAL",
        "anio": None,
        "nivel": "",
        "proyecto_especial_id": proyecto_id,
        "modo_padron": MODO_PADRON_MANUAL_CONTROLADO,
        "padron": _armar_padron_manual_controlado(valores_manual),
    }

    validacion = validar_payload_guardar_carga(payload)
    if not validacion["ok"]:
        return validacion

    validacion["datos"]["modo_padron"] = MODO_PADRON_MANUAL_CONTROLADO
    return validacion


def _validar_payload_padron_proyecto_especial(datos, proyecto_id):
    payload = {
        **datos,
        "cabecera_tipo": "PROYECTO_ESPECIAL",
        "anio": None,
        "nivel": "",
        "proyecto_especial_id": proyecto_id,
        "modo_padron": MODO_PADRON_PADRON,
    }
    validacion = validar_payload_guardar_carga(payload)
    if not validacion["ok"]:
        return validacion

    padron = validacion["datos"]["padron"]
    cueanexo = _cueanexo_desde_padron(padron)
    if not cueanexo or not re.fullmatch(r"\d{9}", cueanexo):
        return {
            "ok": False,
            "errores": {"cueanexo": ["El CUEANEXO oficial es obligatorio para buscar en padrón."]},
        }

    padron["origen_datos"] = SnapshotPadronLocalizacionPof.OrigenDatos.PADRON
    padron["estado_padron"] = SnapshotPadronLocalizacionPof.EstadoPadron.VIGENTE
    validacion["datos"]["modo_padron"] = MODO_PADRON_PADRON
    return validacion


def validar_payload_guardar_carga_proyecto_especial(datos):
    """
    Valida el alta específica de Proyecto Especial sin mezclar la cabecera Reunida.

    - `PADRON` exige una oferta oficial seleccionada.
    - `MANUAL_CONTROLADO` arma un padrón mínimo desde campos/catálogos validados.
    - La persistencia profunda de cargos queda delegada al servicio común.
    """
    if not isinstance(datos, dict):
        return {
            "ok": False,
            "errores": {"payload": ["El cuerpo de la solicitud debe ser un objeto JSON."]},
        }

    modo_padron = _texto(datos.get("modo_padron") or MODO_PADRON_PADRON).upper()
    errores = {}
    if modo_padron not in MODOS_PADRON_VALIDOS:
        errores["modo_padron"] = ["El modo de padrón seleccionado no es válido."]

    if _texto(datos.get("cabecera_tipo")).upper() == "REUNIDA" and modo_padron == MODO_PADRON_MANUAL_CONTROLADO:
        errores["modo_padron"] = ["El modo manual solo es válido para Proyecto Especial."]

    proyecto_id, errores_proyecto = _validar_proyecto_especial_id(datos.get("proyecto_especial_id"))
    if errores_proyecto:
        errores["proyecto_especial_id"] = errores_proyecto

    if errores:
        return {"ok": False, "errores": errores}

    if modo_padron == MODO_PADRON_MANUAL_CONTROLADO:
        return _validar_payload_manual_proyecto_especial(datos, proyecto_id)

    return _validar_payload_padron_proyecto_especial(datos, proyecto_id)
