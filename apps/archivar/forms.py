from django import forms
from .models import ArchRegister

class ArchRegisterForm(forms.ModelForm):
    class Meta:
        model = ArchRegister
        fields = ['cueanexo', 'asunto', 'nivel', 't_norma','nro_normativa', 'año', 'descripcion', 'archivo']
        widgets= {
            'descripcion': forms.Textarea(attrs={
                'rows':2,
                'cols':30,
                'style':'resize:both;',
            }),
        }


"""
    Formulario para la creación y edición de registros de archivos.

    Esta clase hereda de `forms.ModelForm` y se utiliza para gestionar
    el registro de documentos asociados a un anexo específico. El formulario
    permite a los usuarios ingresar información relevante sobre el archivo,
    incluyendo datos obligatorios y opcionales, utilizando los campos del
    modelo `ArchRegister`.

    Attributes:
        cueanexo (CharField): Código único del anexo al que se asocia el registro.
        asunto (CharField): Asunto relacionado con el registro del archivo.
        nivel (CharField): Nivel de relevancia o clasificación del archivo.
        t_norma (CharField): Tipo de normativa que se aplica.
        nro_normativa (CharField): Número de la normativa correspondiente.
        año (IntegerField): Año asociado con la normativa.
        descripcion (TextField): Descripción del archivo o su contenido.
        archivo (FileField): Archivo a ser subido y asociado al registro.

    Meta:
        model (ArchRegister): Modelo que se utiliza para crear y validar el formulario.
        fields (list): Lista de campos que se incluirán en el formulario.
        widgets (dict): Personalización de widgets para campos específicos, 
                        incluyendo el campo 'descripcion' como un área de texto
                        redimensionable.

    Usage:
        - Instancia el formulario en vistas para manejar el registro de archivos.
        - Valida y guarda la información utilizando los métodos integrados de Django.
    """