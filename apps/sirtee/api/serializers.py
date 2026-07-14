from rest_framework import serializers

from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.intervenciones import Intervencion


# --------------------------------------
# RELEVAMIENTO
# --------------------------------------

class RelevamientoSerializer(serializers.ModelSerializer):

    escuela_nombre = serializers.CharField(source="escuela.nom_est", read_only=True)
    escuela_localidad = serializers.CharField(source="escuela.localidad", read_only=True)

    class Meta:
        model = Relevamiento
        fields = "__all__"


# --------------------------------------
# HALLAZGO
# --------------------------------------

class HallazgoSerializer(serializers.ModelSerializer):

    escuela = serializers.CharField(source="relevamiento.escuela.nom_est", read_only=True)

    class Meta:
        model = Hallazgo
        fields = "__all__"


# --------------------------------------
# INTERVENCIÓN
# --------------------------------------

class IntervencionSerializer(serializers.ModelSerializer):

    escuela = serializers.CharField(source="hallazgo.relevamiento.escuela.nom_est", read_only=True)

    class Meta:
        model = Intervencion
        fields = "__all__"