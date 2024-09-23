from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from apps.usuarios.models import UsuariosVisualizador, NivelAcceso
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
import re
import hashlib

User = get_user_model()

# Validador personalizado para el campo username
def validate_username(value):
    if not re.match(r'^\d{7,9}$', value):
        raise ValidationError('El nombre de usuario debe contener sólo números, entre 7 y 9 dígitos.')

# Validador personalizado para los campos apellido y nombres
def validate_alphanumeric_uppercase(value):
    if not re.match(r'^[A-Z0-9\' ]+$', value):
        raise ValidationError('Este campo solo debe contener caracteres alfanuméricos, apóstrofes y estar en mayúsculas.')

class UsuariosForm(ModelForm):
    class Meta:
        model = UsuariosVisualizador
        fields = ['id', 'username', 'password', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo', 'is_staff']

    def clean_username(self):
        username = self.cleaned_data['username']
        if not username.isdigit() or not (7 <= len(username) <= 9):
            raise forms.ValidationError('El nombre de usuario debe contener sólo números y tener entre 7 y 9 dígitos.')
        return username

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Encriptar la contraseña usando SHA-256
        if 'password' in self.cleaned_data:
            raw_password = self.cleaned_data['password']
            hashed_password = hashlib.sha256(raw_password.encode()).hexdigest()
            instance.password = hashed_password
        
        if commit:
            instance.save()
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].validators.append(validate_username)
        self.fields['apellido'].validators.append(validate_alphanumeric_uppercase)
        self.fields['nombres'].validators.append(validate_alphanumeric_uppercase)
        self.fields['username'].error_messages = {
            'unique': 'Ese usuario ya existe.'
        }

    
class UsuariosForm_login(ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese Contraseña', 'autocomplete': 'off'}))
    username = forms.CharField(validators=[validate_username], widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese usuario', 'autocomplete': 'off'}))
    apellido = forms.CharField(validators=[validate_alphanumeric_uppercase], widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido en mayúsculas', 'autocomplete': 'off'}))
    nombres = forms.CharField(validators=[validate_alphanumeric_uppercase], widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombres en mayúsculas', 'autocomplete': 'off'}))
    
    class Meta:
        model = UsuariosVisualizador
        fields = ['username', 'password', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo', 'is_staff', 'is_superuser']
        widgets = {            
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese correo', 'autocomplete': 'off'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'telefono sin 0 ni 15', 'autocomplete': 'off'}),
            'nivelacceso': forms.Select(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CustomPasswordResetForm(PasswordResetForm):
    
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'username', 'class': 'form-control'}))

    def get_users(self, username):
        active_users = UsuariosVisualizador._default_manager.filter(username__iexact=username, activo=True)
        return (u for u in active_users if u.has_usable_password())

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
    )

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise ValidationError("Las dos contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        """
        Guarda la nueva contraseña establecida.
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["new_password1"])
        if commit:
            user.save()
        return user

class ResetpassWordForm(forms.Form):
    username=forms.CharField(
        widget=forms.TextInput(
            attrs={
                'placeholder':'Ingrese un usuario',
                'class': 'form-control',
                'autocomplete':'off'
            }
        )
    )