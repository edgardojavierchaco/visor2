import hashlib
import json
import re
import unicodedata

from django.contrib.gis.db.models.functions import AsGeoJSON, Transform
from django.db.models import Q

from apps.mapas.models import RegionalesGeometria
from apps.supervisa2.models import Region


class RegionalGeoService:
    """
    Construye la capa GeoJSON de regiones educativas para Leaflet.

    REGLA DE SEGURIDAD:
    Nunca se asume que Region.id == RegionalesGeometria.objectid.
    La vinculación se hace exclusivamente por el nombre/código textual
    normalizado de la regional, evitando traer polígonos no asignados.
    """

    PALETA = (
        "#0d6efd", "#198754", "#fd7e14", "#6f42c1",
        "#dc3545", "#20c997", "#0dcaf0", "#ffc107",
        "#6610f2", "#e83e8c", "#795548", "#607d8b",
    )

    @classmethod
    def vacio(cls):
        return {"type": "FeatureCollection", "features": []}

    @classmethod
    def _color(cls, clave):
        clave = str(clave or "regional").encode("utf-8")
        digest = hashlib.sha256(clave).digest()
        return cls.PALETA[digest[0] % len(cls.PALETA)]

    @staticmethod
    def _normalizar_texto(valor):
        texto = str(valor or "").strip().upper()
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    @classmethod
    def _nombres_region(cls, region):
        """
        Devuelve únicamente identificadores textuales confiables de Region.
        No utiliza el PK como objectid de la capa GIS.
        """
        candidatos = []

        for atributo in ("nombre", "descripcion", "region", "codigo"):
            valor = getattr(region, atributo, None)
            if valor not in (None, ""):
                candidatos.append(str(valor).strip())

        representacion = str(region or "").strip()
        if representacion:
            candidatos.append(representacion)

        resultado = []
        vistos = set()
        for valor in candidatos:
            normalizado = cls._normalizar_texto(valor)
            if normalizado and normalizado not in vistos:
                vistos.add(normalizado)
                resultado.append(valor)

        return resultado

    @classmethod
    def geojson_por_ids(cls, region_ids):
        """
        Devuelve SOLO las geometrías de las regiones solicitadas.

        La búsqueda inicial es textual y luego se hace una segunda validación
        en Python para garantizar que ningún feature ajeno quede incluido.
        """
        region_ids = list(dict.fromkeys(int(x) for x in (region_ids or [])))
        if not region_ids:
            return cls.vacio()

        regiones = list(
            Region.objects.filter(pk__in=region_ids).order_by("pk")
        )
        if not regiones:
            return cls.vacio()

        # Conjunto exacto de nombres normalizados autorizados.
        nombres_autorizados = set()
        textos_busqueda = []

        for region in regiones:
            for texto in cls._nombres_region(region):
                normalizado = cls._normalizar_texto(texto)
                if normalizado:
                    nombres_autorizados.add(normalizado)
                    textos_busqueda.append(texto)

        if not nombres_autorizados:
            return cls.vacio()

        filtro = Q()
        for texto in textos_busqueda:
            filtro |= Q(region_pad__iexact=texto)
            filtro |= Q(TITULO__iexact=texto)

        queryset = (
            RegionalesGeometria.objects
            .filter(filtro)
            .annotate(
                geom_geojson=AsGeoJSON(
                    Transform("geom", 4326),
                    precision=6,
                )
            )
            .values(
                "id", "objectid", "region_pad", "TITULO", "geom_geojson"
            )
            .order_by("region_pad", "TITULO", "id")
        )

        features = []
        vistos = set()

        for item in queryset:
            region_pad_norm = cls._normalizar_texto(item.get("region_pad"))
            titulo_norm = cls._normalizar_texto(item.get("TITULO"))

            # Segunda barrera: al menos uno de los textos del feature debe
            # coincidir EXACTAMENTE con una regional autorizada.
            if (
                region_pad_norm not in nombres_autorizados
                and titulo_norm not in nombres_autorizados
            ):
                continue

            geom_text = item.get("geom_geojson")
            if not geom_text:
                continue

            try:
                geometry = json.loads(geom_text)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue

            clave = item.get("id")
            if clave in vistos:
                continue
            vistos.add(clave)

            titulo = (
                item.get("TITULO")
                or item.get("region_pad")
                or "Regional"
            )
            color = cls._color(item.get("region_pad") or titulo)

            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": item.get("id"),
                    "objectid": item.get("objectid"),
                    "region_pad": item.get("region_pad") or "",
                    "titulo": titulo,
                    "fillColor": color,
                    "strokeColor": color,
                },
            })

        return {"type": "FeatureCollection", "features": features}
