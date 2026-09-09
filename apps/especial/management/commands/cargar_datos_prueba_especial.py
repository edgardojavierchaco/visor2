# -*- coding: utf-8 -*-
"""Reinicia y carga un escenario controlado para probar Especial."""

import unicodedata
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bnhalumnos.models import (
    Alumno,
    CatalogoSinoTipo,
)
from apps.bnhpersonas.models import (
    DocumentoTipo,
    EstadosCiviles,
    Localidades,
    Nacionalidad,
    Pais,
    Personas,
    Provincias,
    Sexo,
)

from ...models import (
    AlumnoSeccion,
    CatalogoTipoRangoEtario,
    CatalogoTipoEstructuraEspecial,
    DocenteSeccion,
    EspecialAlumnoBanco,
    EspecialDatosCUEAnexo,
    EspecialDocenteBanco,
    EspecialPadronOferta,
    EspecialCiclo,
    EspecialTrasladoDocente,
    ModalidadDictadoTipo,
    PADRON_DB_ALIAS,
    SeccionEspecial,
    SeccionTipo,
    TurnoTipo,
    normalizar_cueanexo,
)
from apps.cef.models import (
    CefBeneficioSinoTipo,
    CefEspacioComedorTipo,
    CefFuenteFinanciamientoTipo,
    CefPrestacionTipo,
)


def _texto_oferta(valor):
    valor = unicodedata.normalize("NFKD", str(valor or ""))
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    return " ".join(valor.upper().split())


def _cuil(prefijo, dni):
    base = f"{prefijo}{dni:08d}"
    coeficientes = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    resto = sum(int(digito) * coef for digito, coef in zip(base, coeficientes)) % 11
    digito = 11 - resto
    if digito == 11:
        digito = 0
    if digito == 10:
        return None
    return f"{base}{digito}"


class Command(BaseCommand):
    help = "Borra datos de prueba de Especial/BNH Alumnos y crea un escenario controlado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Ejecuta el borrado y la carga. Sin esta opción sólo muestra el preflight.",
        )

    def handle(self, *args, **options):
        escenario = self._preflight()
        self._mostrar_preflight(escenario)
        if not options["confirmar"]:
            self.stdout.write(self.style.WARNING("Preflight solamente: no se modificó ningún dato."))
            self.stdout.write("Para ejecutar: python manage.py cargar_datos_prueba_especial --confirmar")
            return

        with transaction.atomic():
            self._limpiar()
            self._asegurar_datos_cueanexo(escenario)
            alumnos = self._crear_alumnos(escenario)
            secciones = self._crear_secciones(escenario)
            self._crear_bancos_e_inscripciones(alumnos, secciones, escenario)
            docentes = self._crear_docentes(escenario)
            self._crear_asignaciones_docentes(docentes, secciones, escenario)
        self.stdout.write(self.style.SUCCESS("Escenario de prueba creado correctamente."))

    def _preflight(self):
        ciclo = (
            EspecialCiclo.objects.filter(actual=True, activo=True).first()
            or EspecialCiclo.objects.filter(activo=True).order_by("-anio").first()
        )
        if not ciclo:
            raise CommandError("No existe un ciclo Especial activo.")
        if Alumno.objects.count() < 10:
            raise CommandError("Se necesitan al menos 10 alumnos existentes en bnhalumnos.")

        filas = list(
            EspecialPadronOferta.objects.using(PADRON_DB_ALIAS).filter(
                acronimo__iexact="EEE",
                est_oferta__iexact="Activo",
                estado_est__iexact="Activo",
            )
        )
        por_cue = {}
        for fila in filas:
            cue = normalizar_cueanexo(fila.cueanexo or fila.padron_cueanexo)
            if cue:
                por_cue.setdefault(cue, []).append(fila)

        seleccion = None
        for cue, ofertas in por_cue.items():
            integracion = next(
                (fila for fila in ofertas if "INTEGRACION" in _texto_oferta(fila.oferta)),
                None,
            )
            comun = next(
                (
                    fila
                    for fila in ofertas
                    if "INTEGRACION" not in _texto_oferta(fila.oferta)
                ),
                None,
            )
            if integracion and comun:
                seleccion = (cue, integracion, comun)
                break
        if not seleccion:
            raise CommandError(
                "No se encontró un CUE-Anexo Especial con oferta de Integración y otra oferta Especial activas."
            )

        cue, integracion, comun = seleccion
        comunes = list(
            EspecialPadronOferta.objects.using(PADRON_DB_ALIAS).filter(
                est_oferta__iexact="Activo",
                estado_est__iexact="Activo",
            ).exclude(acronimo__iexact="EEE")
        )
        matricula = next(
            (
                normalizar_cueanexo(fila.cueanexo or fila.padron_cueanexo)
                for fila in comunes
                if normalizar_cueanexo(fila.cueanexo or fila.padron_cueanexo)
                and normalizar_cueanexo(fila.cueanexo or fila.padron_cueanexo) != cue
            ),
            None,
        )
        if not matricula:
            raise CommandError("No se encontró un CUE-Anexo común para matrícula compartida.")

        catalogos = {
            "tipo_doc": DocumentoTipo.objects.filter(pk=1).first() or DocumentoTipo.objects.first(),
            "sexo": Sexo.objects.first(),
            "nacionalidad": Nacionalidad.objects.filter(pk=-2).first() or Nacionalidad.objects.first(),
            "pais": Pais.objects.filter(pk=14).first(),
            "provincia": Provincias.objects.filter(pk=int(cue[:2])).first(),
            "localidad": Localidades.objects.filter(c_provincia_id=int(cue[:2])).first(),
            "estado_civil": EstadosCiviles.objects.first(),
            "sino": CatalogoSinoTipo.objects.filter(pk=-2).first() or CatalogoSinoTipo.objects.first(),
            "tipo_seccion": SeccionTipo.objects.first(),
            "estructura": CatalogoTipoEstructuraEspecial.objects.first(),
            "rango": CatalogoTipoRangoEtario.objects.first(),
            "turno": TurnoTipo.objects.first(),
            "modalidad": ModalidadDictadoTipo.objects.first(),
            "beneficio": (
                CefBeneficioSinoTipo.objects.filter(activo=True, codigo=2).first()
                or CefBeneficioSinoTipo.objects.filter(activo=True, codigo=-2).first()
                or CefBeneficioSinoTipo.objects.filter(activo=True).first()
            ),
            "fuente_no_corresponde": CefFuenteFinanciamientoTipo.objects.filter(activo=True, codigo=-1).first(),
            "prestacion_no_corresponde": CefPrestacionTipo.objects.filter(activo=True, codigo=-1).first(),
            "espacio": CefEspacioComedorTipo.objects.filter(activo=True).first(),
        }
        faltantes = [nombre for nombre, valor in catalogos.items() if valor is None]
        if faltantes:
            raise CommandError("Faltan catálogos obligatorios: " + ", ".join(faltantes))

        return {
            "ciclo": ciclo,
            "cue": cue,
            "integracion": integracion,
            "comun": comun,
            "matricula": matricula,
            "catalogos": catalogos,
        }

    def _mostrar_preflight(self, escenario):
        self.stdout.write(f"Ciclo: {escenario['ciclo'].anio} (id={escenario['ciclo'].pk})")
        self.stdout.write(f"CUE-Anexo Especial: {escenario['cue']}")
        self.stdout.write(f"Oferta Integración: {escenario['integracion'].oferta} (id={escenario['integracion'].id})")
        self.stdout.write(f"Oferta Especial adicional: {escenario['comun'].oferta} (id={escenario['comun'].id})")
        self.stdout.write(f"Matrícula compartida: {escenario['matricula']}")
        self.stdout.write("Se crearán 3 secciones, se reutilizarán 10 alumnos existentes y se crearán 3 docentes.")
        self.stdout.write("Se eliminarán únicamente bancos, inscripciones, asignaciones, traslados y secciones de Especial.")

    def _limpiar(self):
        DocenteSeccion.objects.all().delete()
        AlumnoSeccion.objects.all().delete()
        EspecialDocenteBanco.objects.all().delete()
        EspecialTrasladoDocente.objects.all().delete()
        EspecialAlumnoBanco.objects.all().delete()
        SeccionEspecial.objects.all().delete()

    def _crear_alumnos(self, escenario):
        return list(Alumno.objects.order_by("pk")[:10])

    def _asegurar_datos_cueanexo(self, escenario):
        catalogos = escenario["catalogos"]
        if EspecialDatosCUEAnexo.objects.filter(
            cueanexo=escenario["cue"], ciclo=escenario["ciclo"]
        ).exists():
            return
        beneficio = catalogos["beneficio"]
        fuente = catalogos["fuente_no_corresponde"]
        prestacion = catalogos["prestacion_no_corresponde"]
        if beneficio.codigo not in {-2, 2}:
            fuente = CefFuenteFinanciamientoTipo.objects.filter(activo=True).first()
            prestacion = CefPrestacionTipo.objects.filter(activo=True).first()
        EspecialDatosCUEAnexo.objects.create(
            cueanexo=escenario["cue"],
            ciclo=escenario["ciclo"],
            beneficio_alimentario_gratuito=beneficio,
            fuente_financiamiento=fuente,
            prestacion_tipo=prestacion,
            espacio_comedor=catalogos["espacio"],
            observaciones="Datos generados para pruebas de Educación Especial.",
        )

    def _crear_secciones(self, escenario):
        c = escenario["catalogos"]
        ciclo = escenario["ciclo"]
        cue = escenario["cue"]
        return [
            SeccionEspecial.objects.create(
                cueanexo=cue, ciclo=ciclo, nombre_seccion="INTEGRACION 1",
                oferta=escenario["integracion"].oferta, capacidad_total=10,
                cd_tipo_seccion=c["tipo_seccion"], tipo_estructura_especial=c["estructura"],
                turno=c["turno"], rango_etario=c["rango"], modalidad=c["modalidad"],
                estado=SeccionEspecial.Estado.ACTIVO,
            ),
            SeccionEspecial.objects.create(
                cueanexo=cue, ciclo=ciclo, nombre_seccion="INTEGRACION 2",
                oferta=escenario["integracion"].oferta, capacidad_total=10,
                cd_tipo_seccion=c["tipo_seccion"], tipo_estructura_especial=c["estructura"],
                turno=c["turno"], rango_etario=c["rango"], modalidad=c["modalidad"],
                estado=SeccionEspecial.Estado.ACTIVO,
            ),
            SeccionEspecial.objects.create(
                cueanexo=cue, ciclo=ciclo, nombre_seccion="SECCION ESPECIAL 1",
                oferta=escenario["comun"].oferta, capacidad_total=10,
                cd_tipo_seccion=c["tipo_seccion"], tipo_estructura_especial=c["estructura"],
                turno=c["turno"], rango_etario=c["rango"], modalidad=c["modalidad"],
                estado=SeccionEspecial.Estado.ACTIVO,
            ),
        ]

    def _crear_bancos_e_inscripciones(self, alumnos, secciones, escenario):
        for indice, alumno in enumerate(alumnos):
            seccion = secciones[0 if indice < 3 else 1 if indice < 6 else 2]
            banco = EspecialAlumnoBanco.objects.create(
                cueanexo=seccion.cueanexo,
                ciclo=seccion.ciclo,
                alumno=alumno,
                estado=EspecialAlumnoBanco.Estado.ACTIVO,
                matricula_compartida=(escenario["matricula"] if indice < 6 else None),
            )
            AlumnoSeccion.objects.create(
                alumno=alumno,
                seccion=seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
                fecha_inscripcion=date.today(),
            )

    def _crear_docentes(self, escenario):
        provincia = escenario["catalogos"]["provincia"]
        localidad = escenario["catalogos"]["localidad"]
        docentes = []
        for indice in range(1, 4):
            dni = 39000000 + indice
            cuil = _cuil(20, dni)
            while not cuil:
                dni += 1
                cuil = _cuil(20, dni)
            persona, _ = Personas.objects.get_or_create(
                cuil=cuil,
                defaults={
                    "dni": str(dni), "apellido": f"DOCENTE PRUEBA {indice}",
                    "nombre": f"ESPECIAL {indice}", "f_nacimiento": date(1980, indice, indice),
                    "sexo": escenario["catalogos"]["sexo"],
                    "provincia": provincia, "localidad": localidad,
                    "estado": "ACTIVO", "archivada": False,
                },
            )
            banco = EspecialDocenteBanco.objects.create(
                cueanexo=escenario["cue"], ciclo=escenario["ciclo"],
                docente_cuil=persona.cuil, estado=EspecialDocenteBanco.Estado.ACTIVO,
            )
            docentes.append(banco)
        return docentes

    def _crear_asignaciones_docentes(self, docentes, secciones, escenario):
        for indice, banco in enumerate(docentes):
            DocenteSeccion.objects.create(
                seccion=secciones[indice], docente_cuil=banco.docente_cuil,
                rol=DocenteSeccion.Rol.TITULAR, estado=DocenteSeccion.Estado.ACTIVO,
                fecha_desde=date.today(),
            )
