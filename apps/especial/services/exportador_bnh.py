# -*- coding: utf-8 -*-
"""Generación del TXT de 33 campos para BNH Educación Especial."""

import logging
import re
from collections import defaultdict

from apps.bnhpersonas.models import Provincias
from django.db.models import F, Q

from ..models import (
    AlumnoSeccion,
    EspecialAlumnoBanco,
    EspecialDatosCUEAnexo,
    EspecialCiclo,
    EspecialPadronOferta,
    PADRON_DB_ALIAS,
    SeccionEspecial,
)
from ..validators.bnh_validators import (
    compactar_texto,
    normalizar_texto,
    validar_combinaciones_especiales,
    validar_cueanexo,
    validar_documento,
)

logger = logging.getLogger(__name__)

ESTADO_ACTIVO = AlumnoSeccion.Estado.ACTIVO
OFERTA_INTEGRACION = 134
CAMPOS_BNH = (
    "id_persona_jurisdiccional",
    "fecha",
    "apellidos",
    "nombres",
    "cd_tipo_documento",
    "nro_documento",
    "cuil",
    "fecha_nacimiento",
    "cd_sexo",
    "cd_pais_nacimiento",
    "cd_provincia_nacimiento",
    "lugar_nacimiento",
    "cd_nacionalidad",
    "cd_pais_residencia",
    "cd_provincia_residencia",
    "cd_localidad_residencia",
    "cd_pueblo_indigena",
    "cd_discapacidad",
    "cd_ppi",
    "beneficio_alimentario_gratuito",
    "fuente_financiamiento",
    "prestacion_tipo",
    "espacio_comedor",
    "cueanexo",
    "cd_oferta_padron",
    "cd_duracion_oferta",
    "cd_grado",
    "cd_orientacion",
    "modalidad_dictado",
    "id_seccion",
    "nombre_seccion",
    "cd_tipo_seccion",
    "cd_turno",
)


class ExportadorBNH:
    """Construye registros BNH sin modificar ninguna tabla."""

    def __init__(self):
        self.rechazados = []

    def exportar(self, cueanexo=None, anio=None):
        """Devuelve el archivo completo, conservando la API existente.

        Para descargas HTTP debe utilizarse ``iterar``: este método se mantiene
        para usos internos y pruebas que necesitan un ``bytes`` completo.
        """
        return b"".join(self.iterar(cueanexo=cueanexo, anio=anio))

    def iterar(self, cueanexo=None, anio=None):
        """Genera el TXT por partes, sin acumularlo completo en memoria."""
        ciclo = self._resolver_ciclo(anio)
        if not ciclo:
            return

        queryset = self._inscripciones(ciclo, cueanexo)
        cues = set(queryset.values_list("seccion__cueanexo", flat=True))
        padron = self._padron_por_cue_y_oferta(cues)
        datos = {
            (item.cueanexo, item.ciclo_id): item
            for item in EspecialDatosCUEAnexo.objects.filter(
                ciclo=ciclo, cueanexo__in=cues
            ).select_related(
                "beneficio_alimentario_gratuito",
                "fuente_financiamiento",
                "prestacion_tipo",
                "espacio_comedor",
            )
        }
        provincias_ids = set(Provincias.objects.values_list("pk", flat=True))

        encabezado = "|".join(CAMPOS_BNH)
        yield (encabezado + "\n").encode("utf-8")

        grupo = []
        alumno_id = None
        for inscripcion in queryset.iterator(chunk_size=1000):
            if alumno_id is not None and inscripcion.alumno_id != alumno_id:
                yield from self._lineas_grupo(
                    alumno_id, grupo, ciclo, datos, padron, provincias_ids
                )
                grupo = []
            alumno_id = inscripcion.alumno_id
            grupo.append(inscripcion)

        if grupo:
            yield from self._lineas_grupo(
                alumno_id, grupo, ciclo, datos, padron, provincias_ids
            )

    def _lineas_grupo(self, alumno_id, items, ciclo, datos, padron, provincias_ids):
        try:
            validar_combinaciones_especiales(
                alumno_id,
                [{"oferta": item.seccion.oferta} for item in items],
            )
        except ValueError as exc:
            self._rechazar(alumno_id, str(exc))
            return

        for inscripcion in items:
            try:
                campos = self._registro(
                    inscripcion,
                    datos.get((inscripcion.seccion.cueanexo, ciclo.pk)),
                    padron,
                    provincias_ids,
                )
                yield ("|".join(campos) + "\n").encode("utf-8")
            except ValueError as exc:
                self._rechazar(alumno_id, str(exc), inscripcion)

    def _resolver_ciclo(self, anio):
        queryset = EspecialCiclo.objects.all()
        if anio:
            return queryset.filter(anio=anio).first()
        return queryset.filter(actual=True, activo=True).first() or queryset.filter(
            activo=True
        ).order_by("-anio").first()

    def _inscripciones(self, ciclo, cueanexo):
        queryset = (
            AlumnoSeccion.objects.filter(
                estado=ESTADO_ACTIVO,
                seccion__ciclo=ciclo,
                seccion__estado=SeccionEspecial.Estado.ACTIVO,
                alumno__bancos_especial__estado=EspecialAlumnoBanco.Estado.ACTIVO,
                alumno__bancos_especial__ciclo=ciclo,
                alumno__bancos_especial__cueanexo=F("seccion__cueanexo"),
            )
            .select_related(
                "alumno__tipo_doc",
                "alumno__sexo",
                "alumno__nacionalidad",
                "alumno__pais_nacimiento",
                "alumno__prov_nacimiento",
                "alumno__pais_residencia",
                "alumno__prov_residencia",
                "alumno__loc_residencia",
                "alumno__pertenece_pueblo_indigena",
                "alumno__tiene_discapacidad",
                "alumno__tiene_ppi",
                "seccion__ciclo",
                "seccion__cd_tipo_seccion",
                "seccion__turno",
                "seccion__modalidad",
            )
            .order_by("alumno_id", "pk")
            .distinct()
        )
        if cueanexo:
            queryset = queryset.filter(seccion__cueanexo=cueanexo)
        return queryset

    def _padron_por_cue_y_oferta(self, cues):
        queryset = EspecialPadronOferta.objects.using(PADRON_DB_ALIAS).filter(
            acronimo__iexact="EEE",
            est_oferta__iexact="Activo",
            estado_est__iexact="Activo",
        ).filter(Q(cueanexo__in=cues) | Q(padron_cueanexo__in=cues))
        resultado = defaultdict(list)
        por_cue = defaultdict(list)
        for fila in queryset:
            claves = {str(fila.cueanexo or "")}
            if fila.padron_cueanexo:
                claves.add(str(fila.padron_cueanexo))
            for cue in claves:
                resultado[cue, normalizar_texto(fila.oferta)].append(fila)
                por_cue[cue].append(fila)
        return resultado, por_cue

    def _registro(self, inscripcion, datos, padron, provincias_ids):
        alumno = inscripcion.alumno
        seccion = inscripcion.seccion
        cue = re.sub(r"\D", "", seccion.cueanexo or "")
        ofertas_padron, padron_por_cue = padron
        filas_padron = padron_por_cue.get(cue, [])
        cue = validar_cueanexo(cue, filas_padron, provincias_ids)
        oferta_txt = normalizar_texto(seccion.oferta)
        filas_oferta = ofertas_padron.get((cue, oferta_txt), [])
        if not filas_oferta:
            raise ValueError("La oferta de la sección no está activa en Padrón.")
        cd_oferta = OFERTA_INTEGRACION if "INTEGRACION" in oferta_txt else int(filas_oferta[0].id)
        if not datos:
            raise ValueError("Faltan datos CUE-Anexo obligatorios para el ciclo.")

        tipo_doc = getattr(alumno.tipo_doc, "pk", None)
        nro_doc = validar_documento(tipo_doc, alumno.nro_doc)
        apellido = normalizar_texto(alumno.apellidos, solo_letras=True)
        nombre = normalizar_texto(alumno.nombres, solo_letras=True)
        if not apellido or not nombre:
            raise ValueError("El apellido y el nombre son obligatorios.")
        fecha_nacimiento = _fecha(alumno.fecha_nacimiento)
        id_persona = compactar_texto(alumno.id_persona_jurisdiccional)
        if not id_persona:
            id_persona = compactar_texto(
                f"{apellido}{nombre}{tipo_doc}{nro_doc}{fecha_nacimiento}{_codigo(alumno.sexo)}"
            )

        pais_nacimiento = _codigo(alumno.pais_nacimiento, default=-2)
        pais_residencia = _codigo(alumno.pais_residencia, default=-2)
        es_argentina_nacimiento = pais_nacimiento == 14
        es_argentina_residencia = pais_residencia == 14
        nombre_curso = "No corresponde"
        tipo_seccion = -1
        turno = -1
        if "CURSOS" in oferta_txt and "TALLERES" in oferta_txt:
            nombre_curso = normalizar_texto(seccion.nombre_seccion, solo_letras=True)
            tipo_seccion = _codigo(seccion.cd_tipo_seccion)
            turno = _codigo(seccion.turno)

        campos = [
            id_persona,
            _fecha(inscripcion.fecha_inscripcion),
            apellido,
            nombre,
            str(tipo_doc or ""),
            nro_doc,
            _cuil(alumno.cuil),
            fecha_nacimiento,
            str(_codigo(alumno.sexo)),
            str(pais_nacimiento),
            str(_codigo(alumno.prov_nacimiento)) if es_argentina_nacimiento else "",
            normalizar_texto(alumno.lugar_nacimiento, solo_letras=True) if not es_argentina_nacimiento else "",
            str(_codigo(alumno.nacionalidad, default=-2)),
            str(pais_residencia),
            str(_codigo(alumno.prov_residencia)) if es_argentina_residencia else "",
            str(_codigo(alumno.loc_residencia)) if es_argentina_residencia else "",
            str(_codigo(alumno.pertenece_pueblo_indigena)),
            str(_codigo(alumno.tiene_discapacidad)),
            str(_codigo(alumno.tiene_ppi)),
            str(_codigo(datos.beneficio_alimentario_gratuito)),
            str(_codigo(datos.fuente_financiamiento)),
            str(_codigo(datos.prestacion_tipo)),
            str(_codigo(datos.espacio_comedor)),
            cue,
            str(cd_oferta),
            "0",
            "0",
            "-1",
            str(_codigo(seccion.modalidad)),
            f"EEE{seccion.pk}",
            nombre_curso,
            str(tipo_seccion),
            str(turno),
        ]
        if len(campos) != 33:
            raise ValueError("La línea generada no contiene exactamente 33 campos.")
        obligatorios = (0, 1, 2, 3, 4, 7, 8, 9, 10, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32)
        if any(campos[indice] == "" for indice in obligatorios):
            raise ValueError("El registro contiene un campo obligatorio vacío.")
        return campos

    def _rechazar(self, alumno_id, motivo, inscripcion=None):
        detalle = f"alumno_id={alumno_id} motivo={motivo}"
        if inscripcion:
            detalle += f" seccion_id={inscripcion.seccion_id}"
        self.rechazados.append(detalle)
        logger.warning("Registro BNH rechazado: %s", detalle)


def _codigo(objeto, default=""):
    if objeto is None:
        return default
    return getattr(objeto, "codigo", getattr(objeto, "pk", default))


def _fecha(valor):
    return valor.strftime("%d/%m/%Y") if valor else ""


def _cuil(valor):
    cuil = re.sub(r"\D", "", str(valor or ""))
    if cuil and len(cuil) != 11:
        raise ValueError("El CUIL debe tener 11 dígitos.")
    return cuil
