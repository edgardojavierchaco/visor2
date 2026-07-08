from django import forms
from apps.sirtee.models.documentos import Documento


class DocumentoForm(forms.ModelForm):

    class Meta:
        model = Documento
        fields = [
            "tipo",
            "titulo",
            "archivo",
            "relevamiento",
            "hallazgo",
            "intervencion",
        ]

    def clean(self):
        cleaned = super().clean()

        r = cleaned.get("relevamiento")
        h = cleaned.get("hallazgo")
        i = cleaned.get("intervencion")

        # regla: debe estar vinculado a al menos uno
        if not r and not h and not i:
            raise forms.ValidationError(
                "El documento debe estar vinculado a relevamiento, hallazgo o intervención"
            )

        # regla: no puede estar en los tres a la vez (evita ambigüedad)
        count = sum([1 if x else 0 for x in [r, h, i]])
        if count > 1:
            raise forms.ValidationError(
                "El documento solo puede vincularse a una entidad a la vez"
            )

        return cleaned