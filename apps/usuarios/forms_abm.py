# usuarios/forms_abm.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from .models import (
    UsuariosVisualizador,
    PerfilUsuario,
    Rol,
    NivelAcceso
)


class UsuarioForm(forms.ModelForm):

    # ==========================
    # 🔹 CAMPOS EXTRA
    # ==========================

    rol = forms.ModelChoiceField(
        queryset=Rol.objects.all().order_by('nombre'),
        required=False,
        label="Rol",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Seleccione un rol'
        })
    )

    nivelacceso = forms.ModelChoiceField(
        queryset=NivelAcceso.objects.all().order_by('tacceso'),
        label="Nivel de acceso",
        widget=forms.Select(attrs={
            'class': 'form-select select2',
            'data-placeholder': 'Seleccione un nivel'
        })
    )

    password1 = forms.CharField(
        required=False,
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese contraseña'
        })
    )

    password2 = forms.CharField(
        required=False,
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repita la contraseña'
        })
    )

    # ==========================
    # 🔹 META
    # ==========================

    class Meta:
        model = UsuariosVisualizador
        fields = [
            'username',
            'apellido',
            'nombres',
            'correo',
            'telefono',
            'nivelacceso',
            'activo',
            'is_staff',
        ]

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),

            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # ==========================
    # 🔹 INIT
    # ==========================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 Cargar rol actual en edición
        if self.instance.pk and hasattr(self.instance, 'perfil'):
            self.fields['rol'].initial = getattr(self.instance.perfil, 'rol', None)

        # 🔥 Mejora UX: empty label
        self.fields['rol'].empty_label = "Seleccione..."
        self.fields['nivelacceso'].empty_label = "Seleccione..."

    # ==========================
    # 🔹 VALIDACIONES
    # ==========================

    def clean(self):
        cleaned_data = super().clean()

        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        # 👉 CREACIÓN → obligatorio
        if not self.instance.pk:
            if not p1 or not p2:
                raise ValidationError("Debe ingresar y confirmar la contraseña")

        # 👉 VALIDACIÓN
        if p1 or p2:
            if p1 != p2:
                raise ValidationError("Las contraseñas no coinciden")

            validate_password(p1)

        return cleaned_data

    # ==========================
    # 🔹 SAVE
    # ==========================

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("password1")

        if password:
            user.set_password(password)  # 🔐 ENCRIPTADO REAL

        if commit:
            user.save()

            # 🔥 PERFIL + ROL
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
            perfil.rol = self.cleaned_data.get("rol")
            perfil.save()

        return user