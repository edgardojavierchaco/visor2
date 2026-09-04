# apps/supervisor_registro/services/supervisor_geo_service.py

from collections import defaultdict

from django.db.models import CharField
from django.db.models.functions import Cast

from apps.consultasge.models_padron import CapaUnicaOfertas

from ..models import (
    ABMSupervisores,
    SupervisorRegionalOferta,
)


class SupervisorGeoService:
    """
    Servicio encargado de construir la información geográfica
    correspondiente a los supervisores y sus establecimientos.

    La fuente geográfica es:

        CapaUnicaOfertas
        -> vista PostgreSQL v_capa_unica_ofertas_ant

    Las asignaciones se obtienen desde:

        SupervisorRegionalOferta

    IMPORTANTE
    ----------
    En la vista PostgreSQL, cueanexo puede venir como INTEGER/BIGINT,
    aunque en el modelo Django esté declarado como CharField.

    Por ese motivo TODO CUE se normaliza a texto antes de realizar
    cruces entre ambas fuentes.
    """

    # ==============================================================
    # UTILIDADES
    # ==============================================================

    @staticmethod
    def _normalizar_cue(cue):
        """
        Normaliza cualquier CUE/anexo a string.

        Ejemplos:

            220000700
            "220000700"
            " 220000700 "

        todos terminan como:

            "220000700"
        """

        if cue is None:
            return None

        cue = str(cue).strip()

        if not cue:
            return None

        # Por seguridad, elimina ".0" si alguna fuente
        # hubiera transformado el valor en float.
        if cue.endswith(".0"):
            cue = cue[:-2]

        return cue

    # --------------------------------------------------------------

    @staticmethod
    def _coordenadas(row):
        """
        Obtiene latitud y longitud.

        Se priorizan los campos lat/long de la vista porque el campo
        geom del padrón puede tener un SRID diferente del declarado
        en el modelo Django.
        """

        lat = row.get("lat")
        lon = row.get("long")

        try:
            if lat is not None:
                lat = float(lat)

            if lon is not None:
                lon = float(lon)

        except (TypeError, ValueError):
            return None, None

        # Coordenadas imposibles
        if lat is not None and not (-90 <= lat <= 90):
            lat = None

        if lon is not None and not (-180 <= lon <= 180):
            lon = None

        return lat, lon

    # --------------------------------------------------------------

    @staticmethod
    def _nombre_usuario(usuario):

        if not usuario:
            return ""

        apellido = (
            getattr(
                usuario,
                "apellido",
                ""
            )
            or ""
        ).strip()

        nombres = (
            getattr(
                usuario,
                "nombres",
                ""
            )
            or ""
        ).strip()


        if apellido or nombres:

            return " ".join(
                valor
                for valor in [
                    apellido,
                    nombres
                ]
                if valor
            )


        apellido = (
            getattr(
                usuario,
                "last_name",
                ""
            )
            or ""
        ).strip()

        nombres = (
            getattr(
                usuario,
                "first_name",
                ""
            )
            or ""
        ).strip()


        if apellido or nombres:

            return " ".join(
                valor
                for valor in [
                    apellido,
                    nombres
                ]
                if valor
            )


        return str(
            getattr(
                usuario,
                "username",
                ""
            )
            or usuario
        )


    @classmethod
    def _datos_supervisor(
        cls,
        supervisor
    ):

        usuario = getattr(
            supervisor,
            "usuario",
            None
        )

        return {

            "id":
                supervisor.id,

            "cuil":
                getattr(
                    usuario,
                    "username",
                    None
                )
                if usuario
                else None,

            "nombre":
                cls._nombre_usuario(
                    usuario
                ),

            "telefono":
                supervisor.telefono
                or "",

            "email":
                supervisor.email
                or "",

            "activo":
                bool(
                    supervisor.activo
                ),

        }

    # --------------------------------------------------------------

    @staticmethod
    def _datos_oferta(asignacion):
        """
        Serializa una oferta asignada al supervisor.
        """

        return {
            "cueanexo": str(asignacion.cueanexo).strip(),
            "oferta": asignacion.oferta or "",
            "acronimo": asignacion.acronimo or "",
            "nom_est": asignacion.nom_est or "",
        }

    # --------------------------------------------------------------

    @staticmethod
    def _deduplicar_por(items, clave):
        """
        Deduplica una lista de diccionarios.
        """

        resultado = []
        vistos = set()

        for item in items:

            valor = item.get(clave)

            if valor in vistos:
                continue

            vistos.add(valor)
            resultado.append(item)

        return resultado

    # ==============================================================
    # QUERYSET GEOGRÁFICO
    # ==============================================================

    @classmethod
    def _queryset_escuelas(cls, cues):
        """
        Devuelve establecimientos del padrón geográfico.

        IMPORTANTE:
        Se hace CAST explícito de cueanexo a texto porque la columna
        física de PostgreSQL puede ser numérica mientras Django la
        tiene declarada como CharField.
        """

        cues = {
            cls._normalizar_cue(cue)
            for cue in cues
            if cls._normalizar_cue(cue)
        }

        if not cues:
            return CapaUnicaOfertas.objects.none()

        return (
            CapaUnicaOfertas.objects
            .annotate(
                cueanexo_normalizado=Cast(
                    "cueanexo",
                    output_field=CharField(),
                )
            )
            .filter(
                cueanexo_normalizado__in=cues
            )
        )

    # ==============================================================
    # MAPA DE UN SUPERVISOR
    # ==============================================================

    @classmethod
    def escuelas_supervisor(
        cls,
        supervisor,
        regiones=None,
    ):
        """
        Devuelve establecimientos asignados a un único supervisor.

        regiones:
            None -> sin filtro territorial adicional
            []   -> ningún acceso
            [1,2,...] -> regiones autorizadas
        """

        if supervisor is None:
            return []

        # ----------------------------------------------------------
        # ASIGNACIONES
        # ----------------------------------------------------------

        asignaciones = (
            SupervisorRegionalOferta.objects
            .filter(
                supervisor_regional__supervisor=supervisor,
                supervisor_regional__activo=True,
                activo=True,
            )
            .select_related(
                "supervisor_regional",
                "supervisor_regional__supervisor",
                "supervisor_regional__supervisor__usuario",
                "supervisor_regional__region",
            )
        )

        # ----------------------------------------------------------
        # FILTRO DE REGIONES
        # ----------------------------------------------------------

        if regiones is not None:

            if not regiones:
                return []

            asignaciones = asignaciones.filter(
                supervisor_regional__region_id__in=regiones
            )

        # ----------------------------------------------------------
        # MATERIALIZAMOS LAS ASIGNACIONES
        # ----------------------------------------------------------

        asignaciones = list(asignaciones)

        if not asignaciones:
            return []

        # ----------------------------------------------------------
        # AGRUPAMOS INFORMACIÓN POR CUE
        # ----------------------------------------------------------

        escuelas_supervisores = defaultdict(list)
        escuelas_regiones = defaultdict(list)
        escuelas_ofertas = defaultdict(list)

        cues = set()

        for asignacion in asignaciones:

            cue = cls._normalizar_cue(
                asignacion.cueanexo
            )

            if not cue:
                continue

            cues.add(cue)

            supervisor_obj = (
                asignacion
                .supervisor_regional
                .supervisor
            )

            region = (
                asignacion
                .supervisor_regional
                .region
            )

            escuelas_supervisores[cue].append(
                cls._datos_supervisor(supervisor_obj)
            )

            escuelas_regiones[cue].append(
                {
                    "id": region.id,
                    "nombre": str(region),
                }
            )

            escuelas_ofertas[cue].append(
                cls._datos_oferta(asignacion)
            )

        if not cues:
            return []

        # ----------------------------------------------------------
        # PADRÓN GEOGRÁFICO
        # ----------------------------------------------------------

        queryset = (
            cls._queryset_escuelas(cues)
            .values(
                "cueanexo",
                "nom_est",
                "region_loc",
                "localidad",
                "departamento",
                "lat",
                "long",
            )
            .order_by(
                "cueanexo",
                "nom_est",
            )
        )

        resultado = []

        cues_agregados = set()

        for row in queryset:

            cue = cls._normalizar_cue(
                row["cueanexo"]
            )

            if not cue:
                continue

            # La vista puede tener varias filas por CUE debido
            # a las distintas ofertas.
            # Para el mapa necesitamos un punto por establecimiento.
            if cue in cues_agregados:
                continue

            cues_agregados.add(cue)

            lat, lon = cls._coordenadas(row)

            supervisores = cls._deduplicar_por(
                escuelas_supervisores.get(cue, []),
                "id",
            )

            regiones_cue = cls._deduplicar_por(
                escuelas_regiones.get(cue, []),
                "id",
            )

            ofertas = cls._deduplicar_por(
                escuelas_ofertas.get(cue, []),
                "oferta",
            )

            resultado.append(
                {
                    "cueanexo": cue,

                    "escuela": (
                        row.get("nom_est")
                        or ""
                    ),

                    "region_loc": (
                        row.get("region_loc")
                        or ""
                    ),

                    "localidad": (
                        row.get("localidad")
                        or ""
                    ),

                    "departamento": (
                        row.get("departamento")
                        or ""
                    ),

                    "latitud": lat,
                    "longitud": lon,

                    "geolocalizada": (
                        lat is not None
                        and lon is not None
                    ),

                    "regiones": regiones_cue,

                    "supervisores": supervisores,

                    "ofertas": ofertas,
                }
            )

        return resultado

    # ==============================================================
    # MAPA GENERAL
    # ==============================================================

    @classmethod
    def mapa_general(
        cls,
        supervisores,
        regiones=None,
    ):
        """
        Genera el mapa general de supervisores.

        El resultado contiene UN registro por establecimiento
        (CUE/anexo), aunque existan varias ofertas o supervisores.

        Ejemplo:

        {
            "cueanexo": "220000700",
            "escuela": "...",
            "regiones": [...],
            "supervisores": [...],
            "ofertas": [...]
        }
        """

        # ----------------------------------------------------------
        # SUPERVISORES
        # ----------------------------------------------------------

        if supervisores is None:
            return []

        if hasattr(supervisores, "values_list"):

            supervisor_ids = list(
                supervisores.values_list(
                    "id",
                    flat=True,
                )
            )

        else:

            supervisor_ids = [
                supervisor.id
                for supervisor in supervisores
                if supervisor is not None
            ]

        supervisor_ids = list(
            dict.fromkeys(supervisor_ids)
        )

        if not supervisor_ids:
            return []

        # ----------------------------------------------------------
        # ASIGNACIONES
        # ----------------------------------------------------------

        asignaciones = (
            SupervisorRegionalOferta.objects
            .filter(
                supervisor_regional__supervisor_id__in=supervisor_ids,
                supervisor_regional__activo=True,
                supervisor_regional__supervisor__activo=True,
                activo=True,
            )
            .select_related(
                "supervisor_regional",
                "supervisor_regional__supervisor",
                "supervisor_regional__supervisor__usuario",
                "supervisor_regional__region",
            )
        )

        # ----------------------------------------------------------
        # RESTRICCIÓN REGIONAL
        # ----------------------------------------------------------

        if regiones is not None:

            if not regiones:
                return []

            asignaciones = asignaciones.filter(
                supervisor_regional__region_id__in=regiones
            )

        # Ejecutamos UNA SOLA VEZ el queryset.
        asignaciones = list(asignaciones)

        if not asignaciones:
            return []

        # ----------------------------------------------------------
        # AGRUPADORES
        # ----------------------------------------------------------

        escuelas_supervisores = defaultdict(list)
        escuelas_regiones = defaultdict(list)
        escuelas_ofertas = defaultdict(list)

        cues = set()

        # ----------------------------------------------------------
        # ASIGNACIONES -> CUE
        # ----------------------------------------------------------

        for asignacion in asignaciones:

            cue = cls._normalizar_cue(
                asignacion.cueanexo
            )

            if not cue:
                continue

            cues.add(cue)

            supervisor = (
                asignacion
                .supervisor_regional
                .supervisor
            )

            region = (
                asignacion
                .supervisor_regional
                .region
            )

            # Supervisor
            escuelas_supervisores[cue].append(
                cls._datos_supervisor(
                    supervisor
                )
            )

            # Región
            escuelas_regiones[cue].append(
                {
                    "id": region.id,
                    "nombre": str(region),
                }
            )

            # Oferta
            escuelas_ofertas[cue].append(
                cls._datos_oferta(
                    asignacion
                )
            )

        if not cues:
            return []

        # ----------------------------------------------------------
        # BUSCAMOS LOS ESTABLECIMIENTOS
        # ----------------------------------------------------------

        queryset = (
            cls._queryset_escuelas(cues)
            .values(
                "cueanexo",
                "nom_est",
                "region_loc",
                "localidad",
                "departamento",
                "lat",
                "long",
            )
            .order_by(
                "cueanexo",
                "nom_est",
            )
        )

        # ----------------------------------------------------------
        # RESULTADO
        # ----------------------------------------------------------

        resultado = []

        cues_agregados = set()

        for row in queryset:

            cue = cls._normalizar_cue(
                row["cueanexo"]
            )

            if not cue:
                continue

            # Una sola marca por CUE/anexo.
            if cue in cues_agregados:
                continue

            cues_agregados.add(cue)

            lat, lon = cls._coordenadas(
                row
            )

            # ----------------------------------------------
            # CRUCE
            # ----------------------------------------------

            supervisores_cue = (
                escuelas_supervisores.get(
                    cue,
                    [],
                )
            )

            regiones_cue = (
                escuelas_regiones.get(
                    cue,
                    [],
                )
            )

            ofertas_cue = (
                escuelas_ofertas.get(
                    cue,
                    [],
                )
            )

            # ----------------------------------------------
            # DEDUPLICACIÓN
            # ----------------------------------------------

            supervisores_cue = (
                cls._deduplicar_por(
                    supervisores_cue,
                    "id",
                )
            )

            regiones_cue = (
                cls._deduplicar_por(
                    regiones_cue,
                    "id",
                )
            )

            # Una escuela puede tener varias filas iguales
            # de oferta provenientes de distintos cruces.
            ofertas_vistas = set()
            ofertas_final = []

            for oferta in ofertas_cue:

                clave = (
                    oferta.get("cueanexo"),
                    oferta.get("oferta"),
                    oferta.get("acronimo"),
                )

                if clave in ofertas_vistas:
                    continue

                ofertas_vistas.add(clave)
                ofertas_final.append(oferta)

            # ----------------------------------------------
            # REGISTRO FINAL
            # ----------------------------------------------

            resultado.append(
                {
                    "cueanexo": cue,

                    "escuela": (
                        row.get("nom_est")
                        or ""
                    ),

                    "region_loc": (
                        row.get("region_loc")
                        or ""
                    ),

                    "localidad": (
                        row.get("localidad")
                        or ""
                    ),

                    "departamento": (
                        row.get("departamento")
                        or ""
                    ),

                    "latitud": lat,

                    "longitud": lon,

                    "geolocalizada": (
                        lat is not None
                        and lon is not None
                    ),

                    "regiones": regiones_cue,

                    "supervisores": supervisores_cue,

                    "ofertas": ofertas_final,
                }
            )

        # ----------------------------------------------------------
        # ORDEN
        # ----------------------------------------------------------

        resultado.sort(
            key=lambda item: (
                item.get("region_loc") or "",
                item.get("localidad") or "",
                item.get("escuela") or "",
                item.get("cueanexo") or "",
            )
        )

        return resultado

    # ==============================================================
    # ESTADÍSTICAS
    # ==============================================================

    @classmethod
    def estadisticas(cls, escuelas):
        """
        Calcula estadísticas para el dashboard/mapa.
        """

        if not escuelas:
            return {
                "total": 0,
                "geolocalizadas": 0,
                "sin_geolocalizar": 0,
                "supervisores": 0,
                "regiones": 0,
                "ofertas": 0,
            }

        supervisores = set()
        regiones = set()
        ofertas = set()

        geolocalizadas = 0

        for escuela in escuelas:

            if escuela.get("geolocalizada"):
                geolocalizadas += 1

            for supervisor in escuela.get(
                "supervisores",
                [],
            ):
                supervisor_id = supervisor.get("id")

                if supervisor_id is not None:
                    supervisores.add(
                        supervisor_id
                    )

            for region in escuela.get(
                "regiones",
                [],
            ):
                region_id = region.get("id")

                if region_id is not None:
                    regiones.add(
                        region_id
                    )

            for oferta in escuela.get(
                "ofertas",
                [],
            ):

                clave = (
                    oferta.get("cueanexo"),
                    oferta.get("oferta"),
                )

                ofertas.add(clave)

        total = len(escuelas)

        return {
            "total": total,
            "geolocalizadas": geolocalizadas,
            "sin_geolocalizar": (
                total - geolocalizadas
            ),
            "supervisores": len(supervisores),
            "regiones": len(regiones),
            "ofertas": len(ofertas),
        }