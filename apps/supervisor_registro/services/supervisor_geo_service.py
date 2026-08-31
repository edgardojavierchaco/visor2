# supervisor_registro/services/supervisor_geo_service.py

from collections import defaultdict

from apps.consultasge.models_padron import CapaUnicaOfertas

from ..models import (
    ABMSupervisores,
    SupervisorRegional,
    SupervisorRegionalOferta,
)


class SupervisorGeoService:
    """
    Servicio para obtener la cobertura geográfica
    de los supervisores a partir de las escuelas
    que tienen asignadas.

    IMPORTANTE:

    El supervisor NO tiene coordenadas propias.

    La geolocalización se obtiene de las escuelas
    asignadas mediante CUEANEXO.

    Fuente geográfica:
        v_capa_unica_ofertas_ant

    Coordenadas:
        lat
        long

    Geometría:
        geom (EPSG:4326)
    """

    @staticmethod
    def _coordenadas(row):
        """
        Obtiene latitud y longitud.

        Prioridad:

        1. lat / long
        2. geom

        Esto permite trabajar aunque alguna escuela
        no tenga cargados lat/long pero sí tenga geom.
        """

        lat = row.get("lat")
        lon = row.get("long")

        if lat is None or lon is None:
            return None, None

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return None, None

        # Validación básica de coordenadas
        if not -90 <= lat <= 90:
            return None, None

        if not -180 <= lon <= 180:
            return None, None

        return lat, lon

    # =====================================================
    # ESCUELAS DE UN SUPERVISOR
    # =====================================================

    @classmethod
    def escuelas_supervisor(
        cls,
        supervisor_id,
        regiones=None,
    ):
        """
        Devuelve todas las escuelas asignadas
        a un supervisor.

        Una escuela aparece una sola vez aunque
        tenga varias ofertas asignadas.
        """

        regionales = (
            SupervisorRegional.objects
            .filter(
                supervisor_id=supervisor_id,
                activo=True,
            )
            .select_related("region")
        )

        # -------------------------------------------------
        # Restricción territorial
        # -------------------------------------------------

        if regiones is not None:

            regionales = regionales.filter(
                region_id__in=regiones
            )

        asignaciones = (
            SupervisorRegionalOferta.objects
            .filter(
                supervisor_regional__in=regionales,
                activo=True,
            )
            .select_related(
                "supervisor_regional",
                "supervisor_regional__region",
            )
        )

        # -------------------------------------------------
        # CUEANEXO asignados
        # -------------------------------------------------

        cues = list(
            asignaciones
            .values_list(
                "cueanexo",
                flat=True,
            )
            .distinct()
        )

        if not cues:

            return {
                "supervisor_id": supervisor_id,
                "cantidad_escuelas": 0,
                "escuelas": [],
            }

        # -------------------------------------------------
        # Información de las asignaciones
        # -------------------------------------------------

        asignaciones_por_cue = defaultdict(list)

        for asignacion in asignaciones:

            regional = (
                asignacion
                .supervisor_regional
                .region
            )

            data = {

                "region": (
                    regional.nombre
                    if regional
                    else ""
                ),

                "oferta": (
                    asignacion.oferta
                    or ""
                ),

                "acronimo": (
                    asignacion.acronimo
                    or ""
                ),

            }

            if data not in asignaciones_por_cue[
                asignacion.cueanexo
            ]:

                asignaciones_por_cue[
                    asignacion.cueanexo
            ].append(data)

        # -------------------------------------------------
        # Escuelas
        # -------------------------------------------------

        queryset = (
            CapaUnicaOfertas.objects
            .filter(
                cueanexo__in=cues
            )
            .values(
                "cueanexo",
                "nom_est",
                "region_loc",
                "localidad",
                "departamento",
                "oferta",
                "acronimo",
                "lat",
                "long",
                "geom",
            )
        )

        escuelas = {}

        for row in queryset:

            cue = row["cueanexo"]

            latitud, longitud = (
                cls._coordenadas(row)
            )

            # -------------------------------------------------
            # Si la escuela no tiene coordenadas,
            # igualmente la conservamos para poder
            # informar el problema en el dashboard.
            # -------------------------------------------------

            if cue not in escuelas:

                escuelas[cue] = {

                    "cueanexo": cue,

                    "escuela": (
                        row["nom_est"]
                        or ""
                    ),

                    "region_loc": (
                        row["region_loc"]
                        or ""
                    ),

                    "localidad": (
                        row["localidad"]
                        or ""
                    ),

                    "departamento": (
                        row["departamento"]
                        or ""
                    ),

                    "latitud": latitud,

                    "longitud": longitud,

                    "geolocalizada": (
                        latitud is not None
                        and longitud is not None
                    ),

                    "ofertas": [],

                    "regiones": [],

                }

            # -------------------------------------------------
            # Agregar asignaciones
            # -------------------------------------------------

            for asignacion in (
                asignaciones_por_cue.get(
                    cue,
                    [],
                )
            ):

                if asignacion not in (
                    escuelas[cue]["ofertas"]
                ):

                    escuelas[cue]["ofertas"].append(
                        asignacion
                    )

                region = asignacion["region"]

                if (
                    region
                    and region not in
                    escuelas[cue]["regiones"]
                ):

                    escuelas[cue]["regiones"].append(
                        region
                    )

        resultado = list(
            escuelas.values()
        )

        return {

            "supervisor_id":
                supervisor_id,

            "cantidad_escuelas":
                len(resultado),

            "cantidad_geolocalizadas":
                sum(
                    1
                    for escuela in resultado
                    if escuela["geolocalizada"]
                ),

            "cantidad_sin_geolocalizar":
                sum(
                    1
                    for escuela in resultado
                    if not escuela["geolocalizada"]
                ),

            "escuelas":
                resultado,

        }

    # =====================================================
    # MAPA GENERAL
    # =====================================================

    @classmethod
    def mapa_general(
        cls,
        supervisores,
        regiones=None,
    ):
        """
        Construye el mapa general de escuelas
        asignadas a los supervisores visibles.

        Una escuela aparece una sola vez.

        Si está asignada a varios supervisores,
        todos aparecen dentro del popup.
        """

        supervisor_ids = [
            supervisor.id
            for supervisor in supervisores
        ]

        if not supervisor_ids:

            return []

        regionales = (
            SupervisorRegional.objects
            .filter(
                supervisor_id__in=supervisor_ids,
                activo=True,
            )
            .select_related(
                "supervisor",
                "supervisor__usuario",
                "region",
            )
        )

        if regiones is not None:

            regionales = regionales.filter(
                region_id__in=regiones
            )

        asignaciones = (
            SupervisorRegionalOferta.objects
            .filter(
                supervisor_regional__in=regionales,
                activo=True,
            )
            .select_related(
                "supervisor_regional",
                "supervisor_regional__region",
                "supervisor_regional__supervisor",
                "supervisor_regional__supervisor__usuario",
            )
        )

        cues = list(
            asignaciones
            .values_list(
                "cueanexo",
                flat=True,
            )
            .distinct()
        )

        if not cues:

            return []

        # -------------------------------------------------
        # Supervisores por escuela
        # -------------------------------------------------

        escuelas_supervisores = defaultdict(list)

        for asignacion in asignaciones:

            supervisor = (
                asignacion
                .supervisor_regional
                .supervisor
            )

            usuario = supervisor.usuario

            region = (
                asignacion
                .supervisor_regional
                .region
            )

            supervisor_data = {

                "supervisor_id":
                    supervisor.id,

                "cuil":
                    usuario.username,

                "nombre":
                    (
                        f"{usuario.apellido}, "
                        f"{usuario.nombres}"
                    ),

                "region":
                    (
                        region.nombre
                        if region
                        else ""
                    ),

                "oferta":
                    asignacion.oferta
                    or "",

            }

            lista = (
                escuelas_supervisores[
                    asignacion.cueanexo
                ]
            )

            if supervisor_data not in lista:

                lista.append(
                    supervisor_data
                )

        # -------------------------------------------------
        # Datos geográficos
        # -------------------------------------------------

        queryset = (
            CapaUnicaOfertas.objects
            .filter(
                cueanexo__in=cues
            )
            .values(
                "cueanexo",
                "nom_est",
                "region_loc",
                "localidad",
                "departamento",
                "lat",
                "long",
                "geom",
            )
        )

        resultado = {}

        for row in queryset:

            cue = row["cueanexo"]

            latitud, longitud = (
                cls._coordenadas(row)
            )

            if cue not in resultado:

                resultado[cue] = {

                    "cueanexo":
                        cue,

                    "escuela":
                        row["nom_est"]
                        or "",

                    "region_loc":
                        row["region_loc"]
                        or "",

                    "localidad":
                        row["localidad"]
                        or "",

                    "departamento":
                        row["departamento"]
                        or "",

                    "latitud":
                        latitud,

                    "longitud":
                        longitud,

                    "geolocalizada":
                        (
                            latitud is not None
                            and longitud is not None
                        ),

                    "supervisores":
                        escuelas_supervisores[
                            cue
                        ],

                }

        return list(
            resultado.values()
        )