import os

files_to_check = [
    'alumnos_especial.html',
    'asignar_docente_seccion_modal_especial.html',
    'carga_cueanexo_especial.html',
    'carga_seccion_especial.html',
    'ciclos_especial.html',
    'docente_seccion_form_especial.html',
    'docentes_especial.html',
    'docentes_lista_especial.html',
    'docentes_seccion_especial.html',
    'docentes_seccion_lista_especial.html',
    'editar_datos_cueanexo_especial.html',
    'form_seccion_especial.html',
    'gestionar_seccion_docente_activo_especial.html',
    'gestionar_seccion_especial.html',
    'gestionar_seccion_resumen_especial.html',
    'inicio_especial.html',
    'inscripcion_seccion_especial.html',
    'inscripcion_seccion_form_especial.html',
    'inscripciones_seccion_lista_especial.html',
    'localizaciones_especial.html',
    'modal_busqueda_alumno_especial.html',
    'modal_busqueda_docente_especial.html',
]

for filename in files_to_check:
    filepath = f"d:/NachoRepositorios/Trabajo_Ministerio/visor2/templates/especial/{filename}"
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Generic replacements
    text = text.replace('cef_context', 'especial_context')
    text = text.replace('cef_subtitle', 'especial_subtitle')
    text = text.replace('cef_content', 'especial_content')
    
    text = text.replace('cef/base_operativo_cef.html', 'especial/base_operativo_especial.html')
    text = text.replace('archivos/base/layout.html', 'especial/base_operativo_especial.html')
    
    text = text.replace('{% block content %}', '{% block especial_content %}')
    text = text.replace('{% endblock content %}', '{% endblock especial_content %}')

    # Cef prefix fixes
    text = text.replace("url 'cef:", "url 'especial:")
    text = text.replace('url "cef:', 'url "especial:')
    
    # URL name fixes
    text = text.replace('carga_grupo_editar', 'carga_seccion_editar')
    text = text.replace('carga_grupo', 'carga_seccion')
    text = text.replace('gestionar_grupo', 'gestionar_seccion')
    text = text.replace('inscripcion_grupo', 'inscripcion_seccion')
    
    # Text replacements
    text = text.replace('del grupo', 'de la sección')
    text = text.replace('del curso', 'de la sección')
    text = text.replace('este grupo', 'esta sección')
    text = text.replace('este curso', 'esta sección')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
