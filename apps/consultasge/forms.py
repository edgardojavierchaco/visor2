from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from .models import Consulta, Respuesta


class ConsultaForm(forms.ModelForm):

    mensaje = forms.CharField(
        widget=CKEditorUploadingWidget()
    )

    class Meta:
        model = Consulta
        fields = ["categoria", "asunto", "mensaje"]


class RespuestaForm(forms.ModelForm):

    mensaje = forms.CharField(
        widget=CKEditorUploadingWidget()
    )

    class Meta:
        model = Respuesta
        fields = ["mensaje"]