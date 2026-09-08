from django import template


register = template.Library()


CARGA_ROUTE_NAMES = {
    'carga',
    'materialbibliografico_list', 'materialbibliografico_create',
    'materialbibliografico_update', 'materialbibliografico_delete',
    'servref_list', 'servref_create', 'servref_update', 'servref_delete',
    'servrefvirtual_list', 'servrefvirtual_create', 'servrefvirtual_update',
    'servrefvirtual_delete',
    'servprestamo_list', 'servprestamo_create', 'servprestamo_update',
    'servprestamo_delete',
    'infopedago_list', 'infopedago_create', 'infopedago_update',
    'infopedago_delete',
    'asistusua_list', 'asistusua_create', 'asistusua_update',
    'asistusua_delete',
    'instituciones_list', 'instituciones_create', 'instituciones_update',
    'instituciones_delete',
    'proctec_list', 'proctec_create', 'proctec_update', 'proctec_delete',
    'aguapey_list', 'aguapey_create', 'aguapey_update', 'aguapey_delete',
    'fondos_list', 'fondos_create', 'fondos_update', 'fondos_delete',
    'bibliotecario_list', 'bibliotecario_create', 'bibliotecario_update',
    'bibliotecario_delete',
}


@register.filter
def biblioteca_nav_section(url_name):
    if url_name == 'dashboard':
        return 'inicio'
    if url_name in {'periodos', 'generar_info', 'generar_informe'}:
        return 'periodos'
    if url_name in CARGA_ROUTE_NAMES:
        return 'carga'
    if url_name in {
        'informe', 'informe_detalle',
        'modal_generar_pdf_uno', 'generar_pdf_uno',
    }:
        return 'informe'
    return ''
