from django import forms
from django.core.exceptions import ValidationError

from apps.supervisa2.models.supervisor import Supervisor2
from apps.supervisa2.models.catalogos import NivelModalidad, Region, SituacionRevista
from apps.supervisa2.services.regional_service import get_region_usuario


class Supervisor2DynamicForm(forms.ModelForm):

    # =========================================================
    # 🎯 PERMISOS POR ROL
    # =========================================================
    ROLE_PERMISSIONS = {
        "ADMIN": "__all__",
        "SUPERVISOR": "__all__",
        "REGIONAL": ["estado_validacion"],  # 👈 REGIONAL SOLO DECIDE
    }

    # =========================================================
    # 🔄 WORKFLOW REAL
    # =========================================================
    WORKFLOW = {
        "PENDIENTE": ["EN_REVISION"],
        "EN_REVISION": ["APROBADO", "RECHAZADO"],
        "RECHAZADO": ["EN_REVISION"],
        "APROBADO": [],
    }

    class Meta:
        model = Supervisor2
        fields = [
            "situacion_revista",
            "fecha_desde",
            "fecha_hasta",
            "telefono",
            "email",
            "activo",
            "niveles_modalidad",
            "regiones",
            "estado_validacion",
        ]

        widgets = {
            "situacion_revista": forms.Select(attrs={"class": "form-select select2-single"}),

            "fecha_desde": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"}
            ),
            "fecha_hasta": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"}
            ),

            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "niveles_modalidad": forms.SelectMultiple(
                attrs={"class": "form-select select2-multiple"}
            ),
            "regiones": forms.SelectMultiple(
                attrs={"class": "form-select select2-multiple"}
            ),

            "estado_validacion": forms.Select(
                attrs={"class": "form-select select2-single"}
            ),
        }

    # =========================================================
    # 🧠 ROL
    # =========================================================
    def get_user_role(self, user):

        if user.is_superuser:
            return "ADMIN"

        if hasattr(user, "perfil") and user.perfil and user.perfil.rol:
            return user.perfil.rol.nombre.upper()

        return "SUPERVISOR"

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user
        role = self.get_user_role(user)

        # =====================================================
        # QUERYSETS
        # =====================================================
        self.fields["situacion_revista"].queryset = SituacionRevista.objects.all()
        self.fields["niveles_modalidad"].queryset = NivelModalidad.objects.all()
        self.fields["regiones"].queryset = Region.objects.all()

        # =====================================================
        # FECHAS
        # =====================================================
        self.fields["fecha_desde"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_hasta"].input_formats = ["%Y-%m-%d"]

        # =====================================================
        # 🌍 REGIONAL: FILTRA REGIONES
        # =====================================================
        region_user = get_region_usuario(user)

        if role == "REGIONAL":
            if isinstance(region_user, str):
                qs = Region.objects.filter(nombre__icontains=region_user)
            else:
                qs = Region.objects.filter(nombre__in=region_user or [])

            self.fields["regiones"].queryset = qs

            if not self.instance.pk:
                self.initial["regiones"] = qs

            self.fields["regiones"].disabled = True

        # =====================================================
        # 🔒 BLOQUEO SI APROBADO (TOTAL)
        # =====================================================
        if self.instance and self.instance.pk:
            if self.instance.estado_validacion == "APROBADO":
                for f in self.fields.values():
                    f.disabled = True
                return

        # =====================================================
        # 🎯 PERMISOS POR ROL
        # =====================================================
        allowed = self.ROLE_PERMISSIONS.get(role, "__all__")

        if allowed != "__all__":
            for name in self.fields:
                if name not in allowed:
                    self.fields[name].disabled = True

        # =====================================================
        # 🔄 WORKFLOW EN SELECT
        # =====================================================
        if self.instance and self.instance.pk:
            actual = self.instance.estado_validacion
            posibles = self.WORKFLOW.get(actual, [])

            self.fields["estado_validacion"].choices = [
                (k, v)
                for k, v in self.fields["estado_validacion"].choices
                if k in posibles or k == actual
            ]

        self.fields["estado_validacion"].widget.attrs.update({
            "data-placeholder": "Seleccione acción"
        })

        # =====================================================
        # 🔒 REGLAS REGIONAL
        # =====================================================
        if role == "REGIONAL" and self.instance:

            if self.instance.estado_validacion != "EN_REVISION":
                self.fields["estado_validacion"].disabled = True

            if self.instance.estado_validacion == "APROBADO":
                self.fields["activo"].disabled = True

    # =========================================================
    # CLEAN
    # =========================================================
    def clean(self):
        cleaned = super().clean()

        fd = cleaned.get("fecha_desde")
        fh = cleaned.get("fecha_hasta")

        if fd and fh and fh < fd:
            raise ValidationError("Fecha hasta no puede ser menor a fecha desde.")

        # =====================================================
        # mantener valores disabled
        # =====================================================
        for name, field in self.fields.items():
            if field.disabled and self.instance:
                cleaned[name] = getattr(self.instance, name)

        # =====================================================
        # WORKFLOW VALIDATION
        # =====================================================
        if self.instance and self.instance.pk:

            actual = self.instance.estado_validacion
            nuevo = cleaned.get("estado_validacion")

            if nuevo and nuevo != actual:
                if nuevo not in self.WORKFLOW.get(actual, []):
                    raise ValidationError(f"No permitido: {actual} → {nuevo}")

        return cleaned