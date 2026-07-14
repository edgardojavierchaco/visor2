from django import forms
from .models import (
    Personas,
    RegistroActividades,
    Localidades,
    CodAreasTelefonos,
    Grado_anio,
    Secciones,
    HorarioActividad,
    NomencladorCeic
)
from apps.bnhpersonas.domain.access import get_user_cueanexos

from datetime import date
from dateutil.relativedelta import relativedelta


# =====================================================
# PERSONA FORM
# =====================================================
class PersonaForm(forms.ModelForm):

    class Meta:
        model = Personas

        fields = [
            "cuil",
            "dni",
            "apellido",
            "nombre",
            "f_nacimiento",
            "sexo",
            "provincia",
            "localidad",
            "codigo_area",
            "telefono",
            "whatsapp",
        ]
        widgets = {

            "cuil": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),
            
            "dni": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),

            "apellido": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),

            "nombre": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),
            
            "f_nacimiento": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class":"form-control",
                    "type":"date"
                }
            ),

            "sexo": forms.Select(
                attrs={
                    "class":"form-select"
                }
            ),

            "provincia": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "localidad": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),
            
            "codigo_area": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),
            
            "telefono": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),
            
            "whatsapp": forms.CheckboxInput(
                attrs={
                    "class":"form-check-input",
                    "role":"switch"
                }
            ),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields["f_nacimiento"].input_formats = ["%Y-%m-%d"]

        self.fields["localidad"].queryset = Localidades.objects.none()

        self.fields["codigo_area"].queryset = CodAreasTelefonos.objects.all()

        if "provincia" in self.data:
            try:
                provincia_id = self.data.get("provincia")
                self.fields["localidad"].queryset = Localidades.objects.filter(
                    c_provincia_id=provincia_id
                )
            except:
                pass

        if self.instance.pk and self.instance.provincia_id:
            self.fields["localidad"].queryset = Localidades.objects.filter(
                c_provincia_id=self.instance.provincia_id
            )

    def clean_cuil(self):
        cuil = self.cleaned_data.get("cuil")
        return ''.join(filter(str.isdigit, cuil)) if cuil else cuil

    def clean_dni(self):
        dni = self.cleaned_data.get("dni")
        return ''.join(filter(str.isdigit, dni)) if dni else dni

    def clean_apellido(self):
        return " ".join(self.cleaned_data.get("apellido", "").upper().split())

    def clean_nombre(self):
        return " ".join(self.cleaned_data.get("nombre", "").upper().split())
    
    def clean(self):

        cleaned_data = super().clean()


        cuil = cleaned_data.get("cuil")
        dni = cleaned_data.get("dni")


        if cuil and dni:


            # dejar solamente números
            cuil = ''.join(
                filter(
                    str.isdigit,
                    cuil
                )
            )


            dni = ''.join(
                filter(
                    str.isdigit,
                    dni
                )
            )



            # CUIL debe tener 11 dígitos
            if len(cuil) != 11:

                self.add_error(
                    "cuil",
                    "El CUIL debe tener 11 dígitos."
                )

                return cleaned_data



            # extraer DNI del CUIL
            dni_cuil = cuil[2:10]



            if dni_cuil != dni:


                self.add_error(
                    "dni",
                    "El DNI no coincide con el DNI incluido en el CUIL."
                )


                self.add_error(
                    "cuil",
                    "El CUIL no corresponde al DNI ingresado."
                )



        return cleaned_data


# =====================================================
# ACTIVIDAD FORM
# =====================================================

class ActividadDirectorForm(forms.ModelForm):

    cueanexo = forms.ChoiceField(required=True)

    class Meta:

        model = RegistroActividades

        fields = [
            "cueanexo",
            "categoria",
            "modalidad",
            "niveles",
            "sit_revista",
            "cond_actividad",
            "designacion",
            "t_designacion",
            "ceic",
            "grado_anio",
            "turno",
            "secciones",
            "espacios",
            "f_desde",
            "f_hasta",
            "carga_horaria",
            "estado",
            "funciones",
            "f_desde_funciones",
            "f_hasta_funciones",
        ]


        widgets = {

            "categoria": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "modalidad": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "niveles": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "sit_revista": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "cond_actividad": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "designacion": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),
            
            "t_designacion": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "ceic": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "grado_anio": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "turno": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "secciones": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "espacios": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "estado": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),

            "funciones": forms.Select(
                attrs={
                    "class":"form-select select2"
                }
            ),


            # ==========================
            # FECHAS
            # ==========================

            "f_desde": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class":"form-control",
                    "type":"date"
                }
            ),

            "f_hasta": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class":"form-control",
                    "type":"date"
                }
            ),


            "f_desde_funciones": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class":"form-control",
                    "type":"date"
                }
            ),

            "f_hasta_funciones": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class":"form-control",
                    "type":"date"
                }
            ),


            "carga_horaria": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),

        }



    def __init__(self,*args,**kwargs):

        self.user = kwargs.pop("user",None)

        super().__init__(*args,**kwargs)



        # ==========================
        # CUEANEXO POR USUARIO
        # ==========================

        if self.user:

            ofertas = get_user_cueanexos(self.user)

            self.fields["cueanexo"].choices = [
                (x,x)
                for x in ofertas
            ]


        self.fields["cueanexo"].widget.attrs.update({

            "class":"form-select select2"

        })



        # ==========================
        # FORMATO FECHAS AL EDITAR
        # ==========================

        for campo in [

            "f_desde",
            "f_hasta",
            "f_desde_funciones",
            "f_hasta_funciones"

        ]:

            self.fields[campo].input_formats = [
                "%Y-%m-%d"
            ]


        # =========================
        # DEFAULT F_HASTA
        # TITULAR / INTERINO
        # =========================
        
        if not self.instance.pk:

            sit = None


            if self.data:

                sit = self.data.get(
                    "sit_revista"
                )


            else:

                sit = (
                    self.initial.get("sit_revista")
                )


            if sit in [
                "TITULAR",
                "INTERINO"
            ]:


                limite = (
                    date(
                        date.today().year,
                        12,
                        31
                    )
                    +
                    relativedelta(
                        years=28
                    )
                )


                self.initial["f_hasta"] = limite
                

        # ==========================
        # MANTENER CUEANEXO
        # ==========================

        if self.instance and self.instance.pk:

            self.initial["cueanexo"] = str(
                self.instance.cueanexo
            )


    
    def clean_cueanexo(self):

        cue = self.cleaned_data.get("cueanexo")


        if self.user:

            permitidos = set(
                get_user_cueanexos(self.user)
            )


            if str(cue) not in permitidos:

                raise forms.ValidationError(
                    "Sin permisos para esta institución."
                )


        return cue
    
        # =====================================================
    # VALIDACIONES DE FECHAS
    # =====================================================

    def clean(self):

        cleaned_data = super().clean()


        f_desde = cleaned_data.get(
            "f_desde"
        )

        f_hasta = cleaned_data.get(
            "f_hasta"
        )


        f_desde_funciones = cleaned_data.get(
            "f_desde_funciones"
        )

        f_hasta_funciones = cleaned_data.get(
            "f_hasta_funciones"
        )



        # ================================
        # VALIDAR RANGO DEL CARGO
        # ================================

        if f_desde and f_hasta:

            if f_hasta < f_desde:

                self.add_error(
                    "f_hasta",
                    "La fecha hasta no puede ser menor que la fecha desde."
                )



        # ================================
        # FUNCIONES DENTRO DEL PERÍODO
        # ================================

        if f_desde and f_desde_funciones:

            if f_desde_funciones < f_desde:

                self.add_error(
                    "f_desde_funciones",
                    "La fecha desde funciones debe estar dentro del período del cargo."
                )



        if f_hasta and f_hasta_funciones:

            if f_hasta_funciones > f_hasta:

                self.add_error(
                    "f_hasta_funciones",
                    "La fecha hasta funciones debe estar dentro del período del cargo."
                )


        return cleaned_data


# =====================================================
# HORARIO FORM
# =====================================================
class HorarioActividadForm(forms.ModelForm):

    class Meta:
        model = HorarioActividad
        fields = ["dia", "hora_desde", "hora_hasta"]

    def clean(self):
        data = super().clean()

        if data.get("hora_desde") and data.get("hora_hasta"):
            if data["hora_desde"] >= data["hora_hasta"]:
                raise forms.ValidationError("Horario inválido")

        return data