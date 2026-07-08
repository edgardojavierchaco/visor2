from django import forms

from apps.sirtee.models.seguimiento import Seguimiento

from apps.sirtee.forms.base import SirteeBaseForm



class SeguimientoForm(SirteeBaseForm):


    class Meta:


        model = Seguimiento


        fields = [

            "relevamiento",

            "hallazgo",

            "intervencion",

            "estado",

            "comentario",

        ]



        widgets = {


            "relevamiento": forms.Select(

                attrs={

                    "class":
                    "form-select select2",

                    "data-placeholder":
                    "Seleccione relevamiento"

                }

            ),



            "hallazgo": forms.Select(

                attrs={

                    "class":
                    "form-select select2",

                    "data-placeholder":
                    "Seleccione hallazgo"

                }

            ),



            "intervencion": forms.Select(

                attrs={

                    "class":
                    "form-select select2",

                    "data-placeholder":
                    "Seleccione intervención"

                }

            ),



            "estado": forms.Select(

                attrs={

                    "class":
                    "form-select",

                    "data-placeholder":
                    "Seleccione estado"

                }

            ),



            "comentario": forms.Textarea(

                attrs={

                    "class":
                    "form-control",

                    "rows":
                    5,

                    "placeholder":
                    "Ingrese detalle del seguimiento..."

                }

            ),

        }




    # =====================================================
    # INIT
    # =====================================================


    def __init__(

        self,
        *args,
        usuario=None,
        relevamiento=None,
        hallazgo=None,
        intervencion=None,
        **kwargs

    ):


        super().__init__(

            *args,

            **kwargs

        )


        self.usuario = usuario




        # -----------------------------------------------
        # FILTRO RELEVAMIENTO
        # -----------------------------------------------

        if relevamiento:


            self.fields[
                "relevamiento"
            ].initial = relevamiento


            self.fields[
                "relevamiento"
            ].disabled = True




        # -----------------------------------------------
        # FILTRO HALLAZGO
        # -----------------------------------------------

        if hallazgo:


            self.fields[
                "hallazgo"
            ].initial = hallazgo


            self.fields[
                "hallazgo"
            ].disabled = True




        # -----------------------------------------------
        # FILTRO INTERVENCIÓN
        # -----------------------------------------------

        if intervencion:


            self.fields[
                "intervencion"
            ].initial = intervencion


            self.fields[
                "intervencion"
            ].disabled = True





        # -----------------------------------------------
        # USUARIO AUTOMÁTICO
        # -----------------------------------------------

        if "usuario" in self.fields:


            self.fields[
                "usuario"
            ].initial = usuario



        # -----------------------------------------------
        # LABELS
        # -----------------------------------------------

        for nombre, campo in self.fields.items():

            if campo.required:

                campo.label = (
                    f"{campo.label} *"
                )





    # =====================================================
    # CLEAN GENERAL
    # =====================================================


    def clean(self):


        cleaned = super().clean()



        relevamiento = (
            cleaned.get(
                "relevamiento"
            )
        )


        hallazgo = (
            cleaned.get(
                "hallazgo"
            )
        )


        intervencion = (
            cleaned.get(
                "intervencion"
            )
        )



        comentario = (
            cleaned.get(
                "comentario"
            )
        )



        # -----------------------------------------------
        # DEBE TENER CONTEXTO
        # -----------------------------------------------


        if not hallazgo and not intervencion:


            self.add_error(

                None,

                "El seguimiento debe estar asociado "
                "a un hallazgo o una intervención."

            )




        # -----------------------------------------------
        # COMENTARIO OBLIGATORIO
        # -----------------------------------------------


        if comentario:


            comentario = comentario.strip()


            cleaned["comentario"] = comentario



            if len(comentario) < 10:


                self.add_error(

                    "comentario",

                    "El comentario debe tener "
                    "al menos 10 caracteres."

                )


        else:


            self.add_error(

                "comentario",

                "Debe ingresar un comentario."

            )




        # -----------------------------------------------
        # VALIDAR RELACIÓN
        # -----------------------------------------------


        if hallazgo and relevamiento:


            if hallazgo.relevamiento_id != relevamiento.id:


                self.add_error(

                    "hallazgo",

                    "El hallazgo seleccionado "
                    "no pertenece al relevamiento indicado."

                )



        if intervencion and hallazgo:


            if intervencion.hallazgo_id != hallazgo.id:


                self.add_error(

                    "intervencion",

                    "La intervención no pertenece "
                    "al hallazgo seleccionado."

                )



        return cleaned