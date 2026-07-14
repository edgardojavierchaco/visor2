from django import forms

from apps.sirtee.models.intervenciones import Intervencion

from apps.sirtee.forms.base import SirteeBaseForm



class IntervencionForm(SirteeBaseForm):


    class Meta:


        model = Intervencion


        fields = [

            "hallazgo",

            "titulo",

            "descripcion",

            "tipo",

            "estado",

            "prioridad",

            "empresa",

            "responsable",

            "equipo_ejecutor",

            "organismo_responsable",

            "fuente_financiamiento",

            "fecha_inicio",

            "fecha_fin",

            "fecha_estimada_fin",

            "costo_estimado",

            "costo_real",

            "porcentaje_avance",

            "observaciones",

        ]



        widgets = {


            "hallazgo": forms.Select(
                attrs={
                    "class":
                    "form-control select2",

                    "data-placeholder":
                    "Seleccione hallazgo",
                }
            ),



            "titulo": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Título de la intervención"
                }
            ),



            "descripcion": forms.Textarea(
                attrs={
                    "class":
                    "form-control",

                    "rows":5,

                    "placeholder":
                    "Descripción técnica de la intervención"
                }
            ),



            "tipo": forms.Select(
                attrs={
                    "class":
                    "form-control select2",

                    "data-placeholder":
                    "Tipo de intervención"
                }
            ),



            "estado": forms.Select(
                attrs={
                    "class":
                    "form-control select2",

                    "data-placeholder":
                    "Estado"
                }
            ),



            "prioridad": forms.Select(
                attrs={
                    "class":
                    "form-control select2",

                    "data-placeholder":
                    "Prioridad"
                }
            ),



            "empresa": forms.Select(
                attrs={
                    "class":
                    "form-control select2",

                    "data-placeholder":
                    "Empresa ejecutora"
                }
            ),



            "responsable": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Responsable técnico"
                }
            ),



            "equipo_ejecutor": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Equipo ejecutor"
                }
            ),



            "organismo_responsable": forms.Select(
                attrs={
                    "class":
                    "form-control select2",

                    "data-placeholder":
                    "Organismo responsable"
                }
            ),



            "fuente_financiamiento": forms.Select(
                attrs={
                    "class":
                    "form-control select2",

                    "data-placeholder":
                    "Fuente de financiamiento"
                }
            ),



            "fecha_inicio": forms.DateTimeInput(
                attrs={
                    "type":
                    "datetime-local",

                    "class":
                    "form-control"
                }
            ),



            "fecha_fin": forms.DateTimeInput(
                attrs={
                    "type":
                    "datetime-local",

                    "class":
                    "form-control"
                }
            ),



            "fecha_estimada_fin": forms.DateInput(
                attrs={
                    "type":
                    "date",

                    "class":
                    "form-control"
                }
            ),



            "costo_estimado": forms.NumberInput(
                attrs={
                    "class":
                    "form-control",

                    "step":
                    "0.01",

                    "min":
                    "0"
                }
            ),



            "costo_real": forms.NumberInput(
                attrs={
                    "class":
                    "form-control",

                    "step":
                    "0.01",

                    "min":
                    "0"
                }
            ),



            "porcentaje_avance": forms.NumberInput(
                attrs={
                    "class":
                    "form-control",

                    "min":
                    "0",

                    "max":
                    "100"
                }
            ),



            "observaciones": forms.Textarea(
                attrs={
                    "class":
                    "form-control",

                    "rows":
                    4
                }
            ),

        }



    # ==================================================
    # INIT
    # ==================================================

    def __init__(
        self,
        *args,
        usuario=None,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )


        self.usuario = usuario


        # Labels obligatorios

        for nombre, campo in self.fields.items():

            if campo.required:

                campo.label = (
                    f"{campo.label} *"
                )


        # Select placeholder

        selects = [

            "hallazgo",
            "tipo",
            "estado",
            "prioridad",
            "empresa",
            "organismo_responsable",
            "fuente_financiamiento",

        ]


        for campo in selects:

            if campo in self.fields:

                field = self.fields[campo]


                if hasattr(
                    field,
                    "empty_label"
                ):

                    field.empty_label = (
                        "Seleccione..."
                    )



    # ==================================================
    # TITULO
    # ==================================================

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



    # ==================================================
    # DESCRIPCION
    # ==================================================

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


        if len(descripcion) < 20:

            raise forms.ValidationError(
                "La descripción debe tener "
                "al menos 20 caracteres."
            )


        return descripcion



    # ==================================================
    # AVANCE
    # ==================================================

    def clean_porcentaje_avance(self):

        avance = (
            self.cleaned_data.get(
                "porcentaje_avance"
            )
        )


        if avance is None:

            return 0



        if avance < 0 or avance > 100:

            raise forms.ValidationError(
                "El avance debe estar entre 0 y 100."
            )


        return avance



    # ==================================================
    # VALIDACION GENERAL
    # ==================================================

    def clean(self):

        cleaned = super().clean()


        fecha_inicio = cleaned.get(
            "fecha_inicio"
        )

        fecha_fin = cleaned.get(
            "fecha_fin"
        )

        estado = cleaned.get(
            "estado"
        )

        avance = cleaned.get(
            "porcentaje_avance"
        )



        # Fechas

        if (
            fecha_inicio
            and fecha_fin
            and fecha_fin < fecha_inicio
        ):

            self.add_error(
                "fecha_fin",
                "La fecha final no puede ser anterior a la inicial."
            )



        # Estado finalizado

        if (

            estado

            and

            estado.codigo in [

                "FINALIZADA",
                "FINALIZADO"

            ]

            and avance != 100

        ):

            self.add_error(
                "porcentaje_avance",
                "Una intervención finalizada debe tener 100% de avance."
            )



        return cleaned



    # ==================================================
    # SAVE
    # ==================================================

    def save(
        self,
        commit=True
    ):

        obj = super().save(
            commit=False
        )


        if self.usuario:

            if hasattr(
                obj,
                "usuario_creacion"
            ):

                obj.usuario_creacion = (
                    self.usuario
                )



        if commit:

            obj.save()


            self.save_m2m()


        return obj