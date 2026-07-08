from django import forms
from django.db.models import Q

from apps.sirtee.models.empresas import Empresa
from apps.sirtee.forms.base import SirteeBaseForm



class EmpresaForm(SirteeBaseForm):


    class Meta:


        model = Empresa


        fields = [

            "razon_social",

            "nombre_fantasia",

            "cuit",

            "tipo",

            "registro_empresa",

            "condicion_fiscal",

            "telefono",

            "email",

            "domicilio",

            "localidad",

            "responsable",

            "activa",

            "observaciones",

        ]



        widgets = {


            "razon_social": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Razón social",
                }
            ),



            "nombre_fantasia": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Nombre comercial",
                }
            ),



            "cuit": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Ej: 30-12345678-9",
                }
            ),



            "tipo": forms.Select(
                attrs={
                    "class":
                    "form-select select2",

                    "data-placeholder":
                    "Seleccione tipo de empresa"
                }
            ),



            "registro_empresa": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Registro o matrícula"
                }
            ),



            "condicion_fiscal": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Condición fiscal"
                }
            ),



            "telefono": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Teléfono"
                }
            ),



            "email": forms.EmailInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "correo@empresa.com"
                }
            ),



            "domicilio": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Domicilio"
                }
            ),



            "localidad": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Localidad"
                }
            ),



            "responsable": forms.TextInput(
                attrs={
                    "class":
                    "form-control",

                    "placeholder":
                    "Responsable de contacto"
                }
            ),



            "activa": forms.CheckboxInput(
                attrs={
                    "class":
                    "form-check-input"
                }
            ),



            "observaciones": forms.Textarea(
                attrs={
                    "class":
                    "form-control",

                    "rows":
                    4,

                    "placeholder":
                    "Observaciones generales"
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



        # etiquetas requeridas

        for nombre, campo in self.fields.items():

            if campo.required:

                campo.label = (
                    f"{campo.label} *"
                )



    # ==================================================
    # CLEAN RAZON SOCIAL
    # ==================================================


    def clean_razon_social(self):

        valor = (
            self.cleaned_data
            .get("razon_social")
        )


        if valor:

            valor = valor.strip()


        if not valor:

            raise forms.ValidationError(
                "Debe ingresar la razón social."
            )


        if len(valor) < 3:

            raise forms.ValidationError(
                "La razón social es demasiado corta."
            )


        qs = Empresa.objects.filter(
            razon_social__iexact=valor
        )


        if self.instance.pk:

            qs = qs.exclude(
                pk=self.instance.pk
            )


        if qs.exists():

            raise forms.ValidationError(
                "Ya existe una empresa con esa razón social."
            )


        return valor



    # ==================================================
    # CLEAN CUIT
    # ==================================================


    def clean_cuit(self):

        cuit = (
            self.cleaned_data
            .get("cuit")
        )


        if not cuit:

            return None



        cuit = (
            cuit
            .replace("-","")
            .replace(" ","")
        )



        if not cuit.isdigit():

            raise forms.ValidationError(
                "El CUIT solamente debe contener números."
            )



        if len(cuit) != 11:

            raise forms.ValidationError(
                "El CUIT debe contener 11 dígitos."
            )



        qs = Empresa.objects.filter(
            cuit__icontains=cuit
        )



        if self.instance.pk:

            qs = qs.exclude(
                pk=self.instance.pk
            )



        if qs.exists():

            raise forms.ValidationError(
                "Ya existe una empresa con ese CUIT."
            )



        return (
            f"{cuit[:2]}-"
            f"{cuit[2:10]}-"
            f"{cuit[10]}"
        )



    # ==================================================
    # CLEAN EMAIL
    # ==================================================


    def clean_email(self):

        email = (
            self.cleaned_data
            .get("email")
        )


        if email:

            email = email.lower().strip()


        return email



    # ==================================================
    # VALIDACION GENERAL
    # ==================================================


    def clean(self):

        cleaned = super().clean()



        telefono = cleaned.get(
            "telefono"
        )


        email = cleaned.get(
            "email"
        )


        if not telefono and not email:

            self.add_error(
                "telefono",
                "Debe ingresar al menos un medio de contacto."
            )



        return cleaned