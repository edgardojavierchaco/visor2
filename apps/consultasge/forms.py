# apps/consultasge/forms.py

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from .models import Consulta, Respuesta
from apps.usuarios.models import UsuarioCueanexo
from .models_padron import CapaUnicaOfertas


class ConsultaForm(forms.ModelForm):

    mensaje = forms.CharField(widget=CKEditorUploadingWidget())

    cueanexo = forms.ChoiceField(
        label="Establecimiento",
        required=True
    )

    class Meta:
        model = Consulta
        fields = ["cueanexo", "categoria", "asunto", "mensaje"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if not user:
            self.fields["cueanexo"].choices = []
            return

        # 🔥 cueanexos del usuario
        cueanexos = list(
            UsuarioCueanexo.objects.filter(usuario=user)
            .values_list("cueanexo", flat=True)
        )

        # 🔥 normalizar
        cueanexos = [str(c).strip() for c in cueanexos if c]

        # 🔥 traer escuelas en UNA consulta
        escuelas = CapaUnicaOfertas.objects.filter(
            cueanexo__in=cueanexos
        ).values("cueanexo", "nom_est")

        # 🔥 armar mapa
        mapa = {
            str(e["cueanexo"]).strip(): e["nom_est"]
            for e in escuelas
        }

        # 🔥 armar choices
        choices = []

        for cue in cueanexos:
            nombre = mapa.get(cue, "⚠ Sin nombre")
            choices.append((cue, f"{cue} - {nombre}"))

        self.fields["cueanexo"].choices = choices

        # 👉 UX: si hay uno solo
        if len(choices) == 1:
            self.fields["cueanexo"].widget = forms.HiddenInput()
            self.fields["cueanexo_display"] = forms.CharField(
                label="Establecimiento",
                initial=choices[0][1],
                disabled=True
            )


# ========================
# RESPUESTA
# ========================

class RespuestaForm(forms.ModelForm):

    mensaje = forms.CharField(widget=CKEditorUploadingWidget())

    class Meta:
        model = Respuesta
        fields = ["mensaje"]