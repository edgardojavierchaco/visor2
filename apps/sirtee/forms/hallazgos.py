from django import forms

from apps.sirtee.models.hallazgos import Hallazgo
from apps.sirtee.models.relevamientos import Relevamiento
from apps.sirtee.catalogos.models import EstadoHallazgo

from apps.sirtee.forms.base import SirteeBaseForm

from apps.usuarios.models import UsuariosVisualizador


class HallazgoForm(SirteeBaseForm):
    """
    Formulario principal de Hallazgos SiRTEE.

    Incluye:

    - Bootstrap automático mediante SirteeBaseForm
    - Select2 automático
    - Validaciones técnicas
    - Restricción por usuario
    - Responsable automático
    """


    class Meta:

        model = Hallazgo


        fields = [

            "relevamiento",

            "sistema_constructivo",

            "area_afectada",

            "tipo_hallazgo",

            "criticidad",

            "riesgo",

            "estado",

            "titulo",

            "descripcion",

            "ubicacion",

            "observacion_tecnica",

            "recomendacion",

            "usuario_responsable",

        ]



        widgets = {


            "relevamiento": forms.Select(
                attrs={
                    "data-placeholder":
                    "Seleccione relevamiento"
                }
            ),



            "sistema_constructivo": forms.Select(
                attrs={
                    "data-placeholder":
                    "Seleccione sistema constructivo"
                }
            ),



            "area_afectada": forms.Select(
                attrs={
                    "data-placeholder":
                    "Seleccione área afectada"
                }
            ),



            "tipo_hallazgo": forms.Select(
                attrs={
                    "data-placeholder":
                    "Seleccione tipo de hallazgo"
                }
            ),



            "criticidad": forms.Select(
                attrs={
                    "data-placeholder":
                    "Seleccione criticidad"
                }
            ),



            "riesgo": forms.Select(
                attrs={
                    "data-placeholder":
                    "Seleccione riesgo"
                }
            ),



            "estado": forms.Select(
                attrs={
                    "data-placeholder":
                    "Seleccione estado"
                }
            ),



            "titulo": forms.TextInput(
                attrs={
                    "placeholder":
                    "Título del hallazgo"
                }
            ),



            "descripcion": forms.Textarea(
                attrs={

                    "rows": 5,

                    "placeholder":
                    "Describa técnicamente el problema detectado"

                }
            ),



            "ubicacion": forms.TextInput(
                attrs={

                    "placeholder":
                    "Ej: Aula 4, Galería Norte, Cubierta sector B"

                }
            ),



            "observacion_tecnica": forms.Textarea(
                attrs={

                    "rows": 4,

                    "placeholder":
                    "Detalle técnico complementario"

                }
            ),



            "recomendacion": forms.Textarea(
                attrs={

                    "rows": 4,

                    "placeholder":
                    "Indique acciones recomendadas"

                }
            ),



            "usuario_responsable": forms.Select(
                attrs={

                    "data-placeholder":
                    "Seleccione responsable"

                }
            ),

        }



    # ==========================================================
    # INIT
    # ==========================================================


    def __init__(
        self,
        *args,
        usuario=None,
        relevamiento=None,
        **kwargs
    ):


        super().__init__(
            *args,
            **kwargs
        )


        self.usuario = usuario



        # ======================================================
        # RELEVAMIENTOS DISPONIBLES
        # ======================================================


        if usuario:


            if hasattr(
                usuario,
                "relevamientos_disponibles"
            ):


                self.fields[
                    "relevamiento"
                ].queryset = (

                    usuario
                    .relevamientos_disponibles()

                )


            else:


                self.fields[
                    "relevamiento"
                ].queryset = (

                    Relevamiento.objects.all()

                )



        # ======================================================
        # RELEVAMIENTO PRESELECCIONADO
        # ======================================================


        if relevamiento:


            self.fields[
                "relevamiento"
            ].initial = relevamiento


            self.fields[
                "relevamiento"
            ].disabled = True



        # ======================================================
        # RESPONSABLE
        # ======================================================


        if usuario and "usuario_responsable" in self.fields:


            usuario_bd = UsuariosVisualizador.objects.get(
                pk=usuario.pk
            )


            self.fields[
                "usuario_responsable"
            ].queryset = (

                UsuariosVisualizador.objects.filter(
                    pk=usuario_bd.pk
                )

            )


            self.fields[
                "usuario_responsable"
            ].initial = usuario_bd


            self.fields[
                "usuario_responsable"
            ].disabled = True



        # ======================================================
        # ESTADO INICIAL
        # ======================================================


        if not self.instance.pk:


            self.fields[
                "estado"
            ].queryset = (

                EstadoHallazgo.objects.filter(
                    codigo="ABIERTO"
                )

            )



        # ======================================================
        # LABELS REQUERIDOS
        # ======================================================


        for nombre, campo in self.fields.items():


            if campo.required:


                campo.label = (
                    f"{campo.label} *"
                )



        # ======================================================
        # BOOTSTRAP + SELECT2
        # ======================================================


        self.configure_fields()



    # ==========================================================
    # VALIDACION TITULO
    # ==========================================================


    def clean_titulo(self):


        titulo = (
            self.cleaned_data.get(
                "titulo"
            )
        )


        if titulo:

            titulo = titulo.strip()



        if not titulo:


            raise forms.ValidationError(
                "Debe ingresar un título."
            )



        if len(titulo) < 10:


            raise forms.ValidationError(
                "El título debe ser más descriptivo."
            )



        return titulo



    # ==========================================================
    # VALIDACION DESCRIPCION
    # ==========================================================


    def clean_descripcion(self):


        descripcion = (
            self.cleaned_data.get(
                "descripcion"
            )
        )



        if descripcion:

            descripcion = descripcion.strip()



        if not descripcion:


            raise forms.ValidationError(
                "Debe ingresar una descripción técnica."
            )



        if len(descripcion) < 30:


            raise forms.ValidationError(
                "La descripción técnica debe tener al menos 30 caracteres."
            )



        return descripcion



    # ==========================================================
    # VALIDACIONES GENERALES
    # ==========================================================


    def clean(self):


        cleaned = super().clean()



        criticidad = cleaned.get(
            "criticidad"
        )


        recomendacion = cleaned.get(
            "recomendacion"
        )


        estado = cleaned.get(
            "estado"
        )



        if (

            criticidad

            and criticidad.codigo == "CRITICA"

            and not recomendacion

        ):


            self.add_error(

                "recomendacion",

                "Los hallazgos críticos requieren recomendación técnica."

            )



        if (

            not self.instance.pk

            and estado

            and estado.codigo == "RESUELTO"

        ):


            self.add_error(

                "estado",

                "Un hallazgo nuevo no puede crearse como resuelto."

            )



        return cleaned



    # ==========================================================
    # SAVE
    # ==========================================================


    def save(
        self,
        commit=True
    ):


        obj = super().save(
            commit=False
        )



        if self.usuario:


            obj.usuario_responsable = (

                UsuariosVisualizador.objects.get(
                    pk=self.usuario.pk
                )

            )



        if commit:


            obj.save()


            self.save_m2m()



        return obj