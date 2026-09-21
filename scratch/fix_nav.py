import re
with open('d:/NachoRepositorios/Trabajo_Ministerio/visor2/templates/especial/componentes/nav_operativo_especial.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace url tags
text = text.replace("url 'cef:", "url 'especial:")

text = text.replace('cef_context', 'especial_context')
text = text.replace('cef_inicio_url', 'especial_inicio_url')
text = text.replace('cef_localizaciones_url', 'especial_localizaciones_url')
text = text.replace('cef_alumnos_url', 'especial_alumnos_url')
text = text.replace('cef_profesores_url', 'especial_docentes_url') # renamed to docentes
text = text.replace('cef_cueanexo_url', 'especial_cueanexo_url')
text = text.replace('cef_grupos_url', 'especial_secciones_url') # renamed to secciones
text = text.replace('cef_ciclos_url', 'especial_ciclos_url')
text = text.replace('es_admin_cef', 'es_admin_especial')
text = text.replace('cefDirectorNav', 'especialDirectorNav')

text = text.replace("{% url 'especial:profesores'", "{% url 'especial:docentes'")
text = text.replace("{% url 'especial:carga_grupo'", "{% url 'especial:carga_seccion'")

# Text replacements
text = text.replace('>CEF</a>', '>Especial</a>')
text = text.replace('Navegación interna CEF', 'Navegación interna Especial')
text = text.replace('>Profesores</a>', '>Docentes</a>')
text = text.replace('>Grupos / Cursos</a>', '>Secciones</a>')

# Remove inventario
text = re.sub(r'\{% url \'especial:carga_inventario\'.*?\n', '', text)
text = re.sub(r'<li class="nav-item">\s*<a class="nav-link.*?inventario.*?</li>', '', text, flags=re.DOTALL)

with open('d:/NachoRepositorios/Trabajo_Ministerio/visor2/templates/especial/componentes/nav_operativo_especial.html', 'w', encoding='utf-8') as f:
    f.write(text)
