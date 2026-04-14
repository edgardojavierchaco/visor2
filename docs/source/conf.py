import os
import sys
import django

# Añadir la ruta del proyecto al sys.path
sys.path.insert(0, os.path.abspath('../../'))  

# Establecer el módulo de configuración de Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base' 
 
# Configurar Django
django.setup()

# -- Información Proyecto -----------------------------------------------------
project = 'visoreducativochaco'
copyright = '2024, Edgardo Javier Gómez'
author = 'Edgardo Javier Gómez'
release = '1.0'

# -- configuración General ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = []

language = 'es'

# -- Opción para HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'  
html_static_path = ['_static']
