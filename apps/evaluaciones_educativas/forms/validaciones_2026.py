from django import forms
from django.core.validators import RegexValidator

from apps.evaluaciones_educativas.models.validaciones_2026 import (
    ValVeedor,
    ValAplicador,
)


# ---------------------------------------------------------------------------
# Validadores reutilizables
# ---------------------------------------------------------------------------
solo_numeros = RegexValidator(
    regex=r'^\d+$',
    message='Solo se permiten números.',
)

cuil_validator = RegexValidator(
    regex=r'^\d{2}-\d{7,8}-\d{1}$',
    message='El CUIL debe tener el formato XX-XXXXXXXX-X (ej: 20-12345678-9).',
)


# ---------------------------------------------------------------------------
# Form base de persona (campos comunes)
# ---------------------------------------------------------------------------
class ValPersonaBaseForm(forms.Form):
    """
    Form base con los campos comunes de ValPersona.
    No es un ModelForm porque se usa tanto para Veedor como para Aplicador.

    Los `id` de los inputs NO se fijan en `attrs`: Django los genera a partir
    del prefix de cada subclase (id_veedor-nombre, id_aplicador-nombre,
    id_editar-nombre). Fijarlos acá haría que los tres modales compartan el
    mismo id y rompería las búsquedas por getElementById del template.
    """
    nombre = forms.CharField(
        label='Nombre',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre',
        }),
    )
    apellido = forms.CharField(
        label='Apellido',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido',
        }),
    )
    cuil = forms.CharField(
        label='CUIL',
        max_length=20,
        validators=[cuil_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '20-12345678-9',
        }),
    )
    correo = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com',
        }),
    )
    codigo_area = forms.CharField(
        label='Código de área',
        max_length=5,
        validators=[solo_numeros],
        error_messages={
            'max_length': 'El código de área no puede tener más de 5 dígitos.',
            'required': 'El código de área es obligatorio.',
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 362',
            'maxlength': '5',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
        help_text='Máximo 5 dígitos. Solo números.',
    )
    numero_telefono = forms.CharField(
        label='Número de teléfono',
        max_length=10,
        validators=[solo_numeros],
        error_messages={
            'max_length': 'El número de teléfono no puede tener más de 10 dígitos.',
            'required': 'El número de teléfono es obligatorio.',
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 4123456',
            'maxlength': '10',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        }),
        help_text='Máximo 10 dígitos. Solo números.',
    )

    def errores_legibles(self):
        """
        Aplana form.errors en un solo string usando el label de cada campo,
        listo para mostrarse en el toast del template.
        """
        partes = []
        for campo, mensajes in self.errors.items():
            etiqueta = self.fields[campo].label if campo in self.fields else campo
            partes.append(f"{etiqueta}: {' '.join(mensajes)}")
        return ' | '.join(partes)


# ---------------------------------------------------------------------------
# Form: Crear / Editar Veedor
# ---------------------------------------------------------------------------
class ValVeedorForm(ValPersonaBaseForm):
    """Form para crear o editar un Veedor."""

    def __init__(self, *args, prefix='veedor', **kwargs):
        super().__init__(*args, prefix=prefix, **kwargs)


# ---------------------------------------------------------------------------
# Form: Crear / Editar Aplicador
# ---------------------------------------------------------------------------
class ValAplicadorForm(ValPersonaBaseForm):
    """Form para crear o editar un Aplicador."""

    seccion_id = forms.IntegerField(
        label='Sección',
        widget=forms.HiddenInput(),
        required=True,
        error_messages={'required': 'Debe seleccionar una sección.'},
    )

    def __init__(self, *args, prefix='aplicador', **kwargs):
        super().__init__(*args, prefix=prefix, **kwargs)


# ---------------------------------------------------------------------------
# Form: Editar persona (genérico, sin campo de relación)
# ---------------------------------------------------------------------------
class ValPersonaEditForm(ValPersonaBaseForm):
    """Form para editar los datos personales de un Veedor o Aplicador."""

    def __init__(self, *args, prefix='editar', **kwargs):
        super().__init__(*args, prefix=prefix, **kwargs)
