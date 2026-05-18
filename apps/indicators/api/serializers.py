from rest_framework.serializers import (
    Serializer,
    CharField,
    ChoiceField,
    ValidationError,
)


####################################
# INPUT (FILTROS)
####################################
class IndicatorQuerySerializer(Serializer):

    cueanexo = CharField(required=True)

    nivel = ChoiceField(
        choices=[
            "PRIMARIA",
            "SECUNDARIA",
            "TECNICA"
        ],
        required=True
    )

    orientacion = CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    def validate(self, data):

        nivel = data.get("nivel")
        orientacion = data.get("orientacion")

        if nivel in ["SECUNDARIA", "TECNICA"] and not orientacion:
            raise ValidationError({
                "orientacion":
                "Obligatoria para secundaria y técnica"
            })

        return data