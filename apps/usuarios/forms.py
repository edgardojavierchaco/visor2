from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from apps.usuarios.models import UsuariosVisualizador, NivelAcceso
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
import re
import hashlib
from django.contrib.auth.hashers import make_password

User = get_user_model()

# Validador personalizado para el campo username
def validate_username(value):
    """
    Valida que el nombre de usuario contenga solo números, entre 7 y 9 dígitos.

    Parámetros:
        value: El valor del nombre de usuario a validar.

    Lanza:
        ValidationError: Si el valor no cumple con las condiciones.
    """
    
    if not re.match(r'^\d{7,9}$', value):
        raise ValidationError('El nombre de usuario debe contener sólo números, entre 7 y 9 dígitos.')

# Validador personalizado para los campos apellido y nombres
def validate_alphanumeric_uppercase(value):
    """
    Valida que el valor contenga solo caracteres alfanuméricos y esté en mayúsculas.

    Parámetros:
        value: El valor a validar.

    Lanza:
        ValidationError: Si el valor no cumple con las condiciones.
    """
    
    if not re.match(r'^[A-Z0-9\' ]+$', value):
        raise ValidationError('Este campo solo debe contener caracteres alfanuméricos, apóstrofes y estar en mayúsculas.')

class UsuariosForm(ModelForm):
    """
    Formulario para crear o actualizar instancias del modelo UsuariosVisualizador.

    Este formulario incluye validaciones para los campos y encripta la contraseña antes de guardarla.

    Métodos:
        clean_username: Valida que el nombre de usuario cumpla con los requisitos.
        save: Guarda la instancia con la contraseña encriptada.
    """
    
    class Meta:
        model = UsuariosVisualizador
        fields = ['id', 'username', 'password', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso', 'activo', 'is_staff']

    def clean_username(self):
        """
        Valida el nombre de usuario para asegurarse de que contenga solo números.

        Retorna:
            El nombre de usuario limpio.

        Lanza:
            forms.ValidationError: Si el nombre de usuario no es válido.
        """
        
        username = self.cleaned_data['username']
        if not username.isdigit() or not (7 <= len(username) <= 9):
            raise forms.ValidationError('El nombre de usuario debe contener sólo números y tener entre 7 y 9 dígitos.')
        return username

    def save(self, commit=True):
        """
        Guarda la instancia del formulario con la contraseña encriptada.

        Parámetros:
            commit: Si se debe guardar la instancia en la base de datos.

        Retorna:
            La instancia guardada del modelo UsuariosVisualizador.
        """
        
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
        """
        Inicializa el formulario y añade validadores personalizados a los campos.

        Parámetros:
            args: Argumentos adicionales.
            kwargs: Palabras clave adicionales.
        """
        
        super().__init__(*args, **kwargs)
        self.fields['username'].validators.append(validate_username)
        self.fields['apellido'].validators.append(validate_alphanumeric_uppercase)
        self.fields['nombres'].validators.append(validate_alphanumeric_uppercase)
        self.fields['username'].error_messages = {
            'unique': 'Ese usuario ya existe.'
        }

    
class UsuariosForm_login(ModelForm):
    """
    Formulario para el inicio de sesión de UsuariosVisualizador.

    Este formulario incluye validaciones y widgets personalizados para facilitar la entrada de datos.

    Métodos:
        None.
    """
    
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
    """
    Formulario personalizado para restablecer la contraseña de UsuariosVisualizador.

    Este formulario extiende el formulario de restablecimiento de contraseña predeterminado
    y personaliza el método para obtener usuarios.

    Métodos:
        get_users: Obtiene usuarios activos que pueden ser autenticados.
    """
    
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'username', 'class': 'form-control'}))

    def get_users(self, username):
        """
        Obtiene una lista de usuarios activos que coinciden con el nombre de usuario proporcionado.

        Parámetros:
            username: El nombre de usuario a buscar.

        Retorna:
            Un generador de usuarios activos que tienen una contraseña utilizable.
        """
        
        active_users = UsuariosVisualizador._default_manager.filter(username__iexact=username, activo=True)
        return (u for u in active_users if u.has_usable_password())

class CustomSetPasswordForm(SetPasswordForm):
    """
    Formulario personalizado para establecer una nueva contraseña.

    Este formulario extiende el formulario de establecimiento de contraseña
    y personaliza la validación de las contraseñas.

    Métodos:
        clean_new_password2: Valida que las dos contraseñas coincidan.
        save: Guarda la nueva contraseña establecida.
    """
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
    )

    def clean_new_password2(self):
        """
        Valida que las dos contraseñas proporcionadas coincidan.

        Retorna:
            La segunda contraseña limpia.

        Lanza:
            ValidationError: Si las contraseñas no coinciden.
        """
        
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise ValidationError("Las dos contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        """
        Guarda la nueva contraseña establecida.

        Parámetros:
            commit: Si se debe guardar la instancia de usuario en la base de datos.

        Retorna:
            El objeto de usuario guardado con la nueva contraseña.
        """
        
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["new_password1"])
        if commit:
            user.save()
        return user

class ResetpassWordForm(forms.Form):
    """
    Formulario para restablecer la contraseña a través del nombre de usuario.

    Este formulario permite ingresar un nombre de usuario para iniciar el proceso de restablecimiento.

    Métodos:
        None.
    """
    
    username=forms.CharField(
        widget=forms.TextInput(
            attrs={
                'placeholder':'Ingrese un usuario',
                'class': 'form-control',
                'autocomplete':'off'
            }
        )
    )


class UserForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['autofocus'] = True

    class Meta:
        model = UsuariosVisualizador
        fields = 'username', 'password', 'apellido', 'nombres', 'correo', 'telefono', 'nivelacceso'
        widgets = {
            'username': forms.TextInput(
                attrs={
                    'placeholder': 'Ingrese un usuario',
                    'class': 'form-control',
                }
            ),
            'password': forms.PasswordInput(
                attrs={
                    'placeholder': 'Ingrese una constraseña',
                    'class': 'form-control',
                }
            ),
            'apellido': forms.TextInput(
                attrs={
                    'placeholder': 'Ingrese apellido (todo en mayúsculas)',
                    'class': 'form-control',
                }
            ),
            'nombres': forms.TextInput(
                attrs={
                    'placeholder': 'Ingrese nombre (todo en mayúsculas)',
                    'class': 'form-control',
                }
            ),
            'correo': forms.EmailInput(
                attrs={
                    'placeholder': 'Ingrese correo electrónico',
                    'class': 'form-control',
                }
            ),
            'telefono': forms.TextInput(
                attrs={
                    'placeholder': 'Ingrese número teléfono, sin el 0 ni el 15',
                    'class': 'form-control',
                }
            ),
            'nivelacceso': forms.Select(
                attrs={
                    'placeholder': 'Seleccione nivel de acceso',
                    'class': 'form-control',
                }
            ),
            
            
        }
        exclude = ['groups','user_permissions', 'last_login', 'date_joined', 'activo', 'is_superuser', 'is_active', 'is_staff']

    def save(self, commit=True):
        data = {}
        form = super()
        try:
            if form.is_valid():
                usuario = form.save()
                usuario.set_password(self.cleaned_data['password'])
                if commit:
                    usuario.save()  # Guardar la instancia con la contraseña encriptada
                return usuario
            else:
                data['error'] = form.errors
        except Exception as e:
            data['error'] = str(e)
        return data 