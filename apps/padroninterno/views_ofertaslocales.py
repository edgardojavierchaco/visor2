from django.shortcuts import render
from django.db import connections
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from functools import lru_cache
from .permisos import padron_interno_admin_o_gestor_required
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from django.http import HttpResponse, JsonResponse
from datetime import datetime
from io import BytesIO

from requests import request

from apps.padroninterno.partes import partes

PADRON_DB = 'Padron'
PAGE_SIZE = 10

CAMPO_SQL = {
    'cue': 'e.cue::text',
    'anexo': 'l.anexo',
    'codigo_jurisdiccional': 'ol.codigo_jurisdiccional',
    'localizacion': 'l.nombre',
    'tipo_oferta': "BTRIM(COALESCE(ot.descripcion, ''))",
    'nombre_titulo': 'ot.descripcion',
    'estado': "BTRIM(COALESCE(est_of.descripcion, ''))",
    'subvencion': "BTRIM(COALESCE(st.descripcion, ''))",
    'jornada': "BTRIM(COALESCE(jt.descripcion, ''))",
    'matricula_total': 'ol.matricula_total::text',
    'mod_compl_planes': 'eav_o_mod.valor', # Corregido: devuelto a su cajón EAV original
    'cabecera_anexo': "BTRIM(COALESCE(eav_o_cab.valor, ''))",
    'ambito': "BTRIM(COALESCE(eav_o_amb.descripcion, ''))",
    'tipo_ed': "BTRIM(COALESCE(eav_o_tipo_ed.descripcion, ''))",
    'nivel': "BTRIM(COALESCE(eav_o_niv.descripcion, ''))",
    'fecha_creacion': 'eav_o_fecha.valor',
    'sector': "BTRIM(COALESCE(eav_o_sec.descripcion, ''))",
    'acronimo': "BTRIM(COALESCE(eav_o_acr.valor, ''))",
    'categoria': "BTRIM(COALESCE(eav_o_cat.descripcion, ''))",
    'fecha_inst_legal': 'eav_o_fecha_inst.valor',
    'nro_inst_legal': 'eav_o_nro_inst.valor',
    'anio_creacion': 'eav_o_anio.valor',
    'descrip_inst_legal': "BTRIM(COALESCE(eav_o_descrip.valor, ''))",
    'cui': 'eav_o_cui.valor',
    'tel_supervisor': 'eav_o_tel.valor',
    'email_supervisor': 'eav_o_mail.valor',
    'supervisor_tecnico': "BTRIM(COALESCE(eav_o_sup.valor, ''))",
    'udt': "BTRIM(COALESCE(eav_o_udt.valor, ''))",
    'cuof': 'eav_o_cuof.valor',
    'cua': 'eav_o_cua.valor',
    'regional': "BTRIM(COALESCE(eav_o_reg.valor, ''))",
    'cuof_ryc': 'eav_o_cuofryc.valor',
}

COLUMNAS_EXPORTACION = [
    ('CUE', 'cue'),
    ('Anexo', 'anexo'),
    ('Cód. Jurisdiccional', 'codigo_jurisdiccional'),
    ('Localización', 'localizacion'),
    ('Tipo Oferta', 'tipo_oferta'),
    ('Estado', 'estado'),
    ('Subvención', 'subvencion'),
    ('Jornada', 'jornada'),
    ('Matrícula', 'matricula_total'),
    ('Mod. Compl. Planes', 'mod_compl_planes'),
    ('Oferta Cabecera', 'oferta_cabecera'),
    ('Ámbito', 'oferta_ambito'),
    ('Tipo Ed.', 'oferta_tipo_ed'),
    ('Nivel', 'oferta_nivel'),
    ('Fecha Creación', 'fecha_creacion'),
    ('Sector', 'oferta_sector'),
    ('Acrónimo', 'acronimo'),
    ('Categoría', 'oferta_categoria'),
    ('Fecha Inst. Legal', 'fecha_inst_legal'),
    ('Nro Inst. Legal', 'nro_inst_legal'),
    ('Año Creación', 'anio_creacion'),
    ('Descrip. Legal', 'descrip_inst_legal'),
    ('CUI', 'cui'),
    ('Tel. Supervisor', 'tel_supervisor'),
    ('Email Supervisor', 'email_supervisor'),
    ('Sup. Técnico', 'supervisor_tecnico'),
    ('CUOF', 'cuof'),
    ('CUA', 'cua'),
    ('Regional', 'regional'),
    ('UDT', 'udt'),
    ('CUOF RyC', 'cuof_ryc'),
]

_SELECT_FIELDS = """
    SELECT 
        ol.id_oferta_local AS id,
        e.cue, 
        COALESCE(l.anexo, '') AS anexo, 
        UPPER(COALESCE(BTRIM(ol.codigo_jurisdiccional), '')) AS codigo_jurisdiccional, 
        COALESCE(BTRIM(l.nombre), '') AS localizacion,
        COALESCE(BTRIM(ot.descripcion), '') AS tipo_oferta, 
        COALESCE(BTRIM(est_of.descripcion), '') AS estado,
        COALESCE(BTRIM(st.descripcion), '') AS subvencion, 
        COALESCE(BTRIM(jt.descripcion), '') AS jornada,
        COALESCE(ol.matricula_total::text, '') AS matricula_total,
        COALESCE(BTRIM(eav_o_mod.valor), '') AS mod_compl_planes, -- Corregido: apunta al EAV
        COALESCE(BTRIM(eav_o_cab.valor), '') AS oferta_cabecera,
        COALESCE(BTRIM(SUBSTRING(eav_o_amb.descripcion FROM 1 FOR 1)), '') AS oferta_ambito,
        COALESCE(BTRIM(eav_o_amb.descripcion), '') AS ambito,
        COALESCE(BTRIM(eav_o_tipo_ed.descripcion), '') AS oferta_tipo_ed,
        COALESCE(BTRIM(eav_o_niv.descripcion), '') AS oferta_nivel,
        COALESCE(BTRIM(eav_o_fecha.valor), '') AS fecha_creacion,
        COALESCE(BTRIM(eav_o_sec.descripcion), '') AS oferta_sector,
        COALESCE(BTRIM(eav_o_acr.valor), '') AS acronimo,
        COALESCE(BTRIM(eav_o_cat.descripcion), '') AS oferta_categoria,
        COALESCE(BTRIM(eav_o_fecha_inst.valor), '') AS fecha_inst_legal,
        COALESCE(BTRIM(eav_o_nro_inst.valor), '') AS nro_inst_legal,
        COALESCE(BTRIM(eav_o_anio.valor), '') AS anio_creacion,
        COALESCE(BTRIM(eav_o_descrip.valor), '') AS descrip_inst_legal,
        COALESCE(BTRIM(eav_o_cui.valor), '') AS cui,

        COALESCE(BTRIM(eav_o_tel.valor), '') AS tel_supervisor,
        COALESCE(BTRIM(eav_o_mail.valor), '') AS email_supervisor,
        COALESCE(BTRIM(eav_o_sup.valor), '') AS supervisor_tecnico,
        COALESCE(BTRIM(eav_o_udt.valor), '') AS udt,

        COALESCE(BTRIM(eav_o_cuof.valor), '') AS cuof,
        COALESCE(BTRIM(eav_o_cua.valor), '') AS cua,
        COALESCE(BTRIM(eav_o_reg.valor), '') AS regional,
        COALESCE(BTRIM(eav_o_cuofryc.valor), '') AS cuof_ryc
"""

_BASE_SQL = """
    FROM oferta_local ol
    JOIN localizacion l ON ol.id_localizacion = l.id_localizacion
    JOIN establecimiento e ON l.id_establecimiento = e.id_establecimiento
    JOIN oferta_tipo ot ON ol.c_oferta = ot.c_oferta
    LEFT JOIN estado_tipo est_of ON ol.c_estado = est_of.c_estado
    LEFT JOIN subvencion_tipo st ON ol.c_subvencion = st.c_subvencion
    LEFT JOIN jornada_tipo jt ON ol.c_jornada = jt.c_jornada
    
    -- Eliminado el JOIN con modalidad1_tipo que causaba el conflicto

    LEFT JOIN oloc_campo_prov_valor eav_o_fecha ON (ol.id_oferta_local = eav_o_fecha.id_oferta_local AND eav_o_fecha.id_campo_prov = 1019638053)
    LEFT JOIN oloc_campo_prov_valor eav_o_fecha_inst ON (ol.id_oferta_local = eav_o_fecha_inst.id_oferta_local AND eav_o_fecha_inst.id_campo_prov = 1019638064)
    LEFT JOIN oloc_campo_prov_valor eav_o_nro_inst ON (ol.id_oferta_local = eav_o_nro_inst.id_oferta_local AND eav_o_nro_inst.id_campo_prov = 1019638065)
    LEFT JOIN oloc_campo_prov_valor eav_o_anio ON (ol.id_oferta_local = eav_o_anio.id_oferta_local AND eav_o_anio.id_campo_prov = 1019638066)
    LEFT JOIN oloc_campo_prov_valor eav_o_descrip ON (ol.id_oferta_local = eav_o_descrip.id_oferta_local AND eav_o_descrip.id_campo_prov = 1019638067)
    LEFT JOIN oloc_campo_prov_valor eav_o_cab ON (ol.id_oferta_local = eav_o_cab.id_oferta_local AND eav_o_cab.id_campo_prov = 1019638068)
    LEFT JOIN oloc_campo_prov_valor eav_o_cui ON (ol.id_oferta_local = eav_o_cui.id_oferta_local AND eav_o_cui.id_campo_prov = 1019638015)
    LEFT JOIN oloc_campo_prov_valor eav_o_cua ON (ol.id_oferta_local = eav_o_cua.id_oferta_local AND eav_o_cua.id_campo_prov = 1019638077)
    LEFT JOIN oloc_campo_prov_valor eav_o_cuof ON (ol.id_oferta_local = eav_o_cuof.id_oferta_local AND eav_o_cuof.id_campo_prov = 1019638017)
    LEFT JOIN oloc_campo_prov_valor eav_o_reg ON (ol.id_oferta_local = eav_o_reg.id_oferta_local AND eav_o_reg.id_campo_prov = 1019638018)
    LEFT JOIN oloc_campo_prov_valor eav_o_cuofryc ON (ol.id_oferta_local = eav_o_cuofryc.id_oferta_local AND eav_o_cuofryc.id_campo_prov = 1019638078)
    LEFT JOIN oloc_campo_prov_valor eav_o_acr ON (ol.id_oferta_local = eav_o_acr.id_oferta_local AND eav_o_acr.id_campo_prov = 1019638044)
    
    -- Corregido: Se vuelve a añadir el cruce para Mod.Compl.Planes
    LEFT JOIN oloc_campo_prov_valor eav_o_mod ON (ol.id_oferta_local = eav_o_mod.id_oferta_local AND eav_o_mod.id_campo_prov = 1019638096)

    LEFT JOIN oloc_campo_prov_valor eav_o_sup  ON (ol.id_oferta_local = eav_o_sup.id_oferta_local  AND eav_o_sup.id_campo_prov = 1019638061)
    LEFT JOIN oloc_campo_prov_valor eav_o_tel  ON (ol.id_oferta_local = eav_o_tel.id_oferta_local  AND eav_o_tel.id_campo_prov = 1019638062)
    LEFT JOIN oloc_campo_prov_valor eav_o_mail ON (ol.id_oferta_local = eav_o_mail.id_oferta_local AND eav_o_mail.id_campo_prov = 1019638063)
    LEFT JOIN oloc_campo_prov_valor eav_o_udt  ON (ol.id_oferta_local = eav_o_udt.id_oferta_local  AND eav_o_udt.id_campo_prov = 1019638019)

    LEFT JOIN oloc_campo_prov_valor v_amb ON (ol.id_oferta_local = v_amb.id_oferta_local AND v_amb.id_campo_prov = 1019638069)
    LEFT JOIN campo_prov_codigo eav_o_amb ON (v_amb.valor = eav_o_amb.codigo::text AND eav_o_amb.id_campo_prov = 1019638069)
    LEFT JOIN oloc_campo_prov_valor v_niv ON (ol.id_oferta_local = v_niv.id_oferta_local AND v_niv.id_campo_prov = 1019638071)
    LEFT JOIN campo_prov_codigo eav_o_niv ON (v_niv.valor = eav_o_niv.codigo::text AND eav_o_niv.id_campo_prov = 1019638071)
    LEFT JOIN oloc_campo_prov_valor v_sec ON (ol.id_oferta_local = v_sec.id_oferta_local AND v_sec.id_campo_prov = 1019638072)
    LEFT JOIN campo_prov_codigo eav_o_sec ON (v_sec.valor = eav_o_sec.codigo::text AND eav_o_sec.id_campo_prov = 1019638072)
    LEFT JOIN oloc_campo_prov_valor v_cat ON (ol.id_oferta_local = v_cat.id_oferta_local AND v_cat.id_campo_prov = 1019638073)
    LEFT JOIN campo_prov_codigo eav_o_cat ON (v_cat.valor = eav_o_cat.codigo::text AND eav_o_cat.id_campo_prov = 1019638073)
    LEFT JOIN oloc_campo_prov_valor v_tipo_ed ON (ol.id_oferta_local = v_tipo_ed.id_oferta_local AND v_tipo_ed.id_campo_prov = 1019638070)
    LEFT JOIN campo_prov_codigo eav_o_tipo_ed ON (v_tipo_ed.valor = eav_o_tipo_ed.codigo::text AND eav_o_tipo_ed.id_campo_prov = 1019638070)
"""

class _RawPage:
    def __init__(self, data_sql, count_sql, params, db):
        self._data_sql = data_sql
        self._count_sql = count_sql
        self._params = params
        self._db = db
        self._len = None

    def __len__(self):
        if self._len is None:
            with connections[self._db].cursor() as c:
                c.execute(self._count_sql, self._params)
                self._len = c.fetchone()[0]
        return self._len

    def __getitem__(self, s):
        if not isinstance(s, slice):
            raise TypeError
        sql = f"{self._data_sql} LIMIT {s.stop - s.start} OFFSET {s.start or 0}"
        with connections[self._db].cursor() as c:
            c.execute(sql, self._params)
            cols = [d[0] for d in c.description]
            return [dict(zip(cols, row)) for row in c.fetchall()]


OPERADOR_SQL = {
    '0': ('ILIKE', lambda v: f'%{v}%'),
    '1': ('NOT ILIKE', lambda v: f'%{v}%'),
    '2': ('=', lambda v: v),
    '3': ('>', lambda v: v),
    '4': ('>=', lambda v: v),
    '5': ('<', lambda v: v),
    '6': ('<=', lambda v: v),
    '7': ('!=', lambda v: v),
}


def _build_where(request):
    clauses, params = [], []
    grouped_positive_filters = {}

    campos = request.GET.getlist('campo_filtro')
    opers = request.GET.getlist('operador_filtro')
    valores = request.GET.getlist('valor_filtro')

    for i in range(len(campos)):
        campo = campos[i].strip()
        oper = opers[i] if i < len(opers) else '0'
        valor = valores[i].strip() if i < len(valores) else ''

        if campo and valor and campo in CAMPO_SQL:
            if oper in {'0', '2'}:
                group_key = (campo, oper)
                grouped_positive_filters.setdefault(group_key, [])
                if valor not in grouped_positive_filters[group_key]:
                    grouped_positive_filters[group_key].append(valor)
            else:
                col = CAMPO_SQL[campo]
                op_str, val_fn = OPERADOR_SQL.get(oper, OPERADOR_SQL['0'])
                clauses.append(f"{col}::text {op_str} %s")
                params.append(val_fn(valor))

    for (campo, oper), grouped_values in grouped_positive_filters.items():
        col = CAMPO_SQL[campo]
        op_str, val_fn = OPERADOR_SQL.get(oper, OPERADOR_SQL['0'])

        if len(grouped_values) == 1:
            clauses.append(f"{col}::text {op_str} %s")
            params.append(val_fn(grouped_values[0]))
            continue

        or_clauses = []
        for valor in grouped_values:
            or_clauses.append(f"{col}::text {op_str} %s")
            params.append(val_fn(valor))

        clauses.append(f"({' OR '.join(or_clauses)})")

    q = request.GET.get('q', '').strip()
    if q:
        like = f'%{q}%'
        global_search_clauses = [f"{sql_expr} ILIKE %s" for sql_expr in CAMPO_SQL.values()]
        clauses.append(f"({' OR '.join(global_search_clauses)})")
        params += [like] * len(global_search_clauses)

    where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    return where, params


def _armar_texto_filtros(request):
    if request.GET.get('formato') == 'excel_todo':
        return 'Sin filtros aplicados'

    partes = []

    q = request.GET.get('q', '').strip()
    if q:
        partes.append(f'Búsqueda: {q}')

    campos = request.GET.getlist('campo_filtro')
    opers = request.GET.getlist('operador_filtro')
    valores = request.GET.getlist('valor_filtro')

    operadores_txt = {
        '0': 'contiene',
        '1': 'no contiene',
        '2': 'igual a',
        '3': 'mayor a',
        '4': 'mayor o igual a',
        '5': 'menor a',
        '6': 'menor o igual a',
        '7': 'distinto de',
    }

    _nombres_campos_legacy = {
        'cue': 'CUE',
        'anexo': 'Anexo',
        'codigo_jurisdiccional': 'Cód. Jurisdiccional',
        'localizacion': 'Localización',
        'tipo_oferta': 'Tipo Oferta',
        'estado': 'Estado',
        'subvencion': 'Subvención',
        'jornada': 'Jornada',
        'matricula_total': 'Matrícula',
        'mod_compl_planes': 'Mod. Compl. Planes',
        'cabecera_anexo': 'Cabecera-Anexo',
        'ambito': 'Ámbito',
        'tipo_ed': 'Tipo Ed.',
        'nivel': 'Nivel',
        'fecha_creacion': 'Fecha Creación',
        'sector': 'Sector',
        'acronimo': 'Acrónimo',
        'categoria': 'Categoría',
        'fecha_inst_legal': 'Fecha Inst. Legal',
        'nro_inst_legal': 'Nro Inst. Legal',
        'anio_creacion': 'Año Creación',
        'descrip_inst_legal': 'Descrip. Legal',
        'cui': 'CUI',
        'tel_supervisor': 'Tel. Supervisor',
        'email_supervisor': 'Email Supervisor',
        'supervisor_tecnico': 'Sup. Técnico',
        'cuof': 'CUOF',
        'cua': 'CUA',
        'regional': 'Regional',
        'udt': 'UDT',
        'cuof_ryc': 'CUOF RyC',
    }

    nombres_campos = {
        'cue': 'Cue',
        'anexo': 'Anexo',
        'codigo_jurisdiccional': 'Codigo Jurisdiccional',
        'localizacion': 'Localizacion',
        'tipo_oferta': 'Tipo Oferta',
        'nombre_titulo': 'Nombre Titulo',
        'estado': 'Estado',
        'subvencion': 'Subvencion',
        'jornada': 'Jornada',
        'matricula_total': 'Matricula Total',
        'mod_compl_planes': 'Mod.Compl.Planes',
        'cabecera_anexo': 'Oferta CABECERA-ANEXO',
        'ambito': 'Oferta AMBITO',
        'tipo_ed': 'Oferta TIPO ED.',
        'nivel': 'Oferta NIVEL',
        'fecha_creacion': 'Fecha de creación de la Oferta',
        'sector': 'Oferta SECTOR',
        'acronimo': 'Acrónimo',
        'categoria': 'Oferta CATEGORIA',
        'fecha_inst_legal': 'FECHA Inst. Legal Creacion de la Oferta',
        'nro_inst_legal': 'NRO. Inst. Legal Creacion de la Oferta',
        'anio_creacion': 'AÑO Creacion de la Oferta',
        'descrip_inst_legal': 'DESCRIP. Inst. Legal Creacion de la Oferta',
        'cui': 'CUI de la Oferta',
        'tel_supervisor': 'Teléfono Supervisor Oferta',
        'email_supervisor': 'Email Supervisor Oferta',
        'supervisor_tecnico': 'Supervisor Técnico Oferta',
        'cuof': 'CUOF Código Único de la Oficina de la Oferta',
        'cua': 'CUA de la Oferta',
        'regional': 'Regional Educativa de la Oferta',
        'udt': 'UDT Universidad de Desarrollo Territorial UDT de la Oferta',
        'cuof_ryc': 'CUOF_RyC',
    }

    nombres_campos['fecha_creacion'] = 'Fecha de creaci\u00f3n de la Oferta'
    nombres_campos['acronimo'] = 'Acr\u00f3nimo'
    nombres_campos['anio_creacion'] = 'A\u00d1O Creacion de la Oferta'
    nombres_campos['tel_supervisor'] = 'Tel\u00e9fono Supervisor Oferta'
    nombres_campos['supervisor_tecnico'] = 'Supervisor T\u00e9cnico Oferta'
    nombres_campos['cuof'] = 'CUOF C\u00f3digo \u00danico de la Oficina de la Oferta'

    for i in range(len(campos)):
        campo = campos[i].strip() if i < len(campos) else ''
        oper = opers[i].strip() if i < len(opers) else '0'
        valor = valores[i].strip() if i < len(valores) else ''

        if campo and valor:
            campo_txt = nombres_campos.get(campo, campo)
            oper_txt = operadores_txt.get(oper, 'contiene')
            partes.append(f'{campo_txt} {oper_txt}: {valor}')

    if not partes:
        return 'Sin filtros aplicados'

    return ' | '.join(partes)

     
def _formatear_fecha_estilo_seguimiento():
    ahora = datetime.now()
    dia = ahora.day
    mes = ahora.month
    anio = ahora.year
    hora_12 = ahora.strftime('%I').lstrip('0') or '0'
    minuto = ahora.strftime('%M')
    ampm = 'p. m.' if ahora.hour >= 12 else 'a. m.'
    return f'{dia}/{mes}/{anio} a las {hora_12}:{minuto} {ampm}'


def _resolver_columnas_exportar(request, formato):
    if formato == 'excel_todo':
        return COLUMNAS_EXPORTACION

    visibles = request.GET.getlist('visible_col')
    if not visibles:
        return COLUMNAS_EXPORTACION

    visibles_set = {v.strip() for v in visibles if v.strip()}
    columnas_filtradas = [col for col in COLUMNAS_EXPORTACION if col[1] in visibles_set]

    return columnas_filtradas or COLUMNAS_EXPORTACION


def _exportar_excel(datos_exportar, formato, request):
    columnas_mapeo = _resolver_columnas_exportar(request, formato)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Ofertas Locales'

    total_columnas = len(columnas_mapeo)
    ultima_columna = get_column_letter(total_columnas)

    titulo = 'Informe Ofertas Locales'
    fecha_str = _formatear_fecha_estilo_seguimiento()
    filtros_str = _armar_texto_filtros(request)

    ws.merge_cells(f'A1:{ultima_columna}1')
    ws['A1'] = titulo
    ws['A1'].font = Font(bold=True, size=10)
    ws['A1'].alignment = Alignment(horizontal='left', vertical='center')

    ws.merge_cells(f'A2:{ultima_columna}2')
    ws['A2'] = f'Informe generado el: {fecha_str}'
    ws['A2'].font = Font(size=9)
    ws['A2'].alignment = Alignment(horizontal='left', vertical='center')

    ws.merge_cells(f'A3:{ultima_columna}3')
    ws['A3'] = f'Filtros aplicados: {filtros_str}'
    ws['A3'].font = Font(size=9)
    ws['A3'].alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

    ws.row_dimensions[1].height = 18
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 20

    fila_headers = 4
    for col_idx, (titulo_col, _) in enumerate(columnas_mapeo, start=1):
        celda = ws.cell(row=fila_headers, column=col_idx, value=titulo_col)
        celda.font = Font(bold=True, size=9)
        celda.alignment = Alignment(horizontal='left', vertical='center')

    for item in datos_exportar:
        fila = []
        for _, clave in columnas_mapeo:
            valor = item.get(clave, '')
            if valor is None:
                valor = ''
            fila.append(str(valor).replace('\r', ' ').replace('\n', ' '))
        ws.append(fila)

    ws.freeze_panes = 'A5'
    ws.auto_filter.ref = f'A4:{ultima_columna}{ws.max_row}'

    if formato == 'excel_todo':
        for col_num in range(1, total_columnas + 1):
            titulo_col = columnas_mapeo[col_num - 1][0]
            col_letter = get_column_letter(col_num)
            ws.column_dimensions[col_letter].width = min(max(len(str(titulo_col)) + 4, 14), 28)
    else:
        for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
            for cell in row:
                cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
                cell.font = Font(size=9)

        for col_num in range(1, total_columnas + 1):
            col_letter = get_column_letter(col_num)
            max_length = 0
            for row_num in range(1, ws.max_row + 1):
                cell_value = ws[f'{col_letter}{row_num}'].value
                cell_len = len(str(cell_value)) if cell_value is not None else 0
                if cell_len > max_length:
                    max_length = cell_len
            ws.column_dimensions[col_letter].width = min(max_length + 2, 40)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha_archivo = datetime.now().strftime('%Y%m%d_%H%M')
    sufijo = 'Filtros' if formato == 'excel_pagina' else 'Todo'
    nombre_archivo = f'OfertasLocales_{sufijo}_{fecha_archivo}.xlsx'

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response

def _dictfetchall(cursor):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _sanitize_json_payload(value):
    if isinstance(value, dict):
        return {k: _sanitize_json_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_payload(item) for item in value]
    return '' if value is None else value


def _fetch_one(sql, params):
    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, params)
        rows = _dictfetchall(cursor)
    return rows[0] if rows else None


def _fetch_all(sql, params):
    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(sql, params)
        return _dictfetchall(cursor)


@lru_cache(maxsize=None)
def _get_table_columns(table_name):
    with connections[PADRON_DB].cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            [table_name],
        )
        return {row[0] for row in cursor.fetchall()}


def _first_existing_column(table_name, candidates):
    columns = _get_table_columns(table_name)

    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def _description_expr(alias, table_name, fallback="''"):
    column = _first_existing_column(table_name, ('descripcion', 'nombre', 'detalle'))
    if column:
        return f"COALESCE({alias}.{column}, '')"
    return fallback


def _build_norma_expr():
    tipo_expr = _description_expr('inl', 'instr_legal_tipo', "''")
    return f"""
        TRIM(
            BOTH ' ' FROM
            CONCAT_WS(
                ' ',
                NULLIF({tipo_expr}, ''),
                NULLIF(COALESCE(pl.norma_nro::text, ''), '')
            )
        ) ||
        CASE
            WHEN COALESCE(pl.norma_anio::text, '') <> '' THEN ' (' || pl.norma_anio::text || ')'
            ELSE ''
        END
    """


def _build_duracion_expr():
    unidad_expr = _description_expr('de', 'duracion_en_tipo', "''")
    return f"""
        CASE
            WHEN COALESCE(pl.duracion::text, '') = '' THEN ''
            WHEN NULLIF({unidad_expr}, '') IS NOT NULL THEN pl.duracion::text || ' ' || {unidad_expr}
            ELSE pl.duracion::text
        END
    """


def _fetch_first_success(sql_variants, params):
    last_error = None

    for sql in sql_variants:
        try:
            return _fetch_all(sql, params)
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    return []

@padron_interno_admin_o_gestor_required
def detalle_oferta_local_json(request, id_oferta):
    oferta_sql = f"""
        SELECT
            oferta_det.*,
            COALESCE(oferta_det.tipo_oferta, '') AS carrera,
            COALESCE(oferta_det.tipo_oferta, '') AS oferta,
            ''::text AS fecha_alta,
            ''::text AS fecha_baja,
            ''::text AS fecha_actualizacion
        FROM (
            {_SELECT_FIELDS}
            {_BASE_SQL}
            WHERE ol.id_oferta_local = %s
            LIMIT 1
        ) AS oferta_det
    """

    titulos_sql_variants = [
        """
            SELECT
                COALESCE(tio.codigo::text, '') || ' - ' || COALESCE(tio.descripcion, '') AS titulo_completo,
                tio.c_titulo AS id_titulo,
                COALESCE(pel_sec.duracion::text || ' Años', '') AS duracion,
                COALESCE(
                    'Resolución ' || pel_sec.nro_resolucion::text || ' (' || pel_sec.anio_resolucion::text || ')',
                    ''
                ) AS norma,
                COALESCE(dt.descripcion, '') AS dictado,
                ''::text AS requisito,
                ''::text AS condicion_ingreso
            FROM plan_estudio_local pl
            JOIN titulo_oferta_tipo tot ON pl.c_titulo_oferta = tot.c_titulo_oferta
            JOIN titulo_tipo tio ON tot.c_titulo = tio.c_titulo
            LEFT JOIN plan_estudio_local_secundaria pel_sec ON pl.id_plan_estudio_local = pel_sec.id_plan_estudio_local
            LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
            WHERE pl.id_oferta_local = %s
            ORDER BY tio.descripcion
        """,
        """
            SELECT
                COALESCE(tio.cod_titulo::text, '') || ' - ' || COALESCE(tio.descripcion, '') AS titulo_completo,
                tio.c_titulo AS id_titulo,
                COALESCE(pel_sec.duracion::text || ' Años', '') AS duracion,
                COALESCE(
                    'Resolución ' || pel_sec.nro_resolucion::text || ' (' || pel_sec.anio_resolucion::text || ')',
                    ''
                ) AS norma,
                COALESCE(dt.descripcion, '') AS dictado,
                ''::text AS requisito,
                ''::text AS condicion_ingreso
            FROM plan_estudio_local pl
            JOIN titulo_oferta_tipo tot ON pl.c_titulo_oferta = tot.c_titulo_oferta
            JOIN titulo_tipo tio ON tot.c_titulo = tio.c_titulo
            LEFT JOIN plan_estudio_local_secundaria pel_sec ON pl.id_plan_estudio_local = pel_sec.id_plan_estudio_local
            LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
            WHERE pl.id_oferta_local = %s
            ORDER BY tio.descripcion
        """,
    ]

    historial_sql = """
        SELECT
            ce.id_movimiento,
            COALESCE(est.descripcion, '') AS estado_movimiento,
            COALESCE(est.descripcion, '') AS estado,
            COALESCE(ot.descripcion, '') AS carrera,
            COALESCE(m.fecha_instrumento_legal::text, '') AS fecha_instr_legal,
            COALESCE(m.fecha_vigencia::text, '') AS fecha_vigencia,
            COALESCE(m.observaciones, '') AS observacion,
            COALESCE(il.descripcion, '') AS instr_legal,
            COALESCE(mot.descripcion, '') AS motivo,
            COALESCE(m.usuario, '') AS usuario
        FROM cambio_estado_oferta_local ce
        JOIN movimiento m ON ce.id_movimiento = m.id_movimiento
        JOIN oferta_local ol ON ce.id_oferta_local = ol.id_oferta_local
        JOIN oferta_tipo ot ON ol.c_oferta = ot.c_oferta
        LEFT JOIN estado_tipo est ON ce.c_estado = est.c_estado
        LEFT JOIN instrumento_legal_tipo il ON m.c_instrumento_legal = il.c_instrumento_legal
        LEFT JOIN motivo_tipo mot ON m.c_motivo = mot.c_motivo
        WHERE ce.id_oferta_local = %s
        ORDER BY m.fecha_vigencia DESC
    """

    try:
        oferta = _fetch_one(oferta_sql, [id_oferta])

        if not oferta:
            return JsonResponse({'error': 'Oferta local no encontrada.'}, status=404)

        titulos = _fetch_first_success(titulos_sql_variants, [id_oferta])
        historial = _fetch_all(historial_sql, [id_oferta])

        return JsonResponse(_sanitize_json_payload({
            'oferta': oferta,
            'titulos': titulos,
            'historial': historial,
        }))
    except Exception as exc:
        return JsonResponse({'error': f'Error al obtener detalle de oferta local: {exc}'}, status=500)

@padron_interno_admin_o_gestor_required
def detalle_titulo_json(request, id_titulo):
    titulo_sql_variants = [
        """
            SELECT
                COALESCE(t.descripcion, '') AS titulo,
                COALESCE(t.cod_titulo::text, '') || ' - ' || COALESCE(t.descripcion, '') AS titulo_completo,
                COALESCE(t.cod_titulo::text, '') || ' - ' || COALESCE(t.descripcion, '') AS orientacion,
                COALESCE(c.descripcion, '') AS carrera,
                COALESCE(n.descripcion, '') AS nivel,
                COALESCE(d.descripcion, '') AS disciplina,
                COALESCE(r.descripcion, '') AS rama,
                COALESCE(pel_sec.duracion::text || ' Años', '') AS duracion,
                COALESCE(
                    'Resolución ' || pel_sec.nro_resolucion::text || ' (' || pel_sec.anio_resolucion::text || ')',
                    ''
                ) AS norma,
                COALESCE(dt.descripcion, '') AS dictado,
                ''::text AS requisito,
                ''::text AS condicion_ingreso
            FROM titulo_tipo t
            LEFT JOIN carrera_tipo c ON t.c_carrera = c.c_carrera
            LEFT JOIN nivel_tipo n ON t.c_nivel_titulo = n.c_nivel
            LEFT JOIN disciplina_tipo d ON t.cod_disciplina = d.c_disciplina
            LEFT JOIN rama_tipo r ON t.cod_rama = r.c_rama
            LEFT JOIN titulo_oferta_tipo tot ON t.c_titulo = tot.c_titulo
            LEFT JOIN plan_estudio_local pl ON tot.c_titulo_oferta = pl.c_titulo_oferta
            LEFT JOIN plan_estudio_local_secundaria pel_sec ON pl.id_plan_estudio_local = pel_sec.id_plan_estudio_local
            LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
            WHERE t.c_titulo = %s
            LIMIT 1
        """,
        """
            SELECT
                COALESCE(t.descripcion, '') AS titulo,
                COALESCE(t.codigo::text, '') || ' - ' || COALESCE(t.descripcion, '') AS titulo_completo,
                COALESCE(t.codigo::text, '') || ' - ' || COALESCE(t.descripcion, '') AS orientacion,
                COALESCE(c.descripcion, '') AS carrera,
                COALESCE(n.descripcion, '') AS nivel,
                COALESCE(d.descripcion, '') AS disciplina,
                COALESCE(r.descripcion, '') AS rama,
                COALESCE(pel_sec.duracion::text || ' Años', '') AS duracion,
                COALESCE(
                    'Resolución ' || pel_sec.nro_resolucion::text || ' (' || pel_sec.anio_resolucion::text || ')',
                    ''
                ) AS norma,
                COALESCE(dt.descripcion, '') AS dictado,
                ''::text AS requisito,
                ''::text AS condicion_ingreso
            FROM titulo_tipo t
            LEFT JOIN carrera_tipo c ON t.c_carrera = c.c_carrera
            LEFT JOIN nivel_tipo n ON t.c_nivel_titulo = n.c_nivel
            LEFT JOIN disciplina_tipo d ON t.cod_disciplina = d.c_disciplina
            LEFT JOIN rama_tipo r ON t.cod_rama = r.c_rama
            LEFT JOIN titulo_oferta_tipo tot ON t.c_titulo = tot.c_titulo
            LEFT JOIN plan_estudio_local pl ON tot.c_titulo_oferta = pl.c_titulo_oferta
            LEFT JOIN plan_estudio_local_secundaria pel_sec ON pl.id_plan_estudio_local = pel_sec.id_plan_estudio_local
            LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
            WHERE t.c_titulo = %s
            LIMIT 1
        """,
    ]

    try:
        titulo_rows = _fetch_first_success(titulo_sql_variants, [id_titulo])
        titulo = titulo_rows[0] if titulo_rows else None

        if not titulo:
            return JsonResponse({'error': 'Título no encontrado.'}, status=404)

        return JsonResponse(_sanitize_json_payload({'titulo': titulo}))
    except Exception as exc:
        return JsonResponse({'error': f'Error al obtener detalle del título: {exc}'}, status=500)

@padron_interno_admin_o_gestor_required
def detalle_oferta_local_json(request, id_oferta):
    oferta_sql = f"""
        SELECT
            oferta_det.*,
            COALESCE(oferta_det.tipo_oferta, '') AS carrera,
            COALESCE(oferta_det.tipo_oferta, '') AS oferta,
            ''::text AS fecha_alta,
            ''::text AS fecha_baja,
            ''::text AS fecha_actualizacion
        FROM (
            {_SELECT_FIELDS}
            {_BASE_SQL}
            WHERE ol.id_oferta_local = %s
            LIMIT 1
        ) AS oferta_det
    """

    titulos_sql = f"""
        SELECT
            COALESCE(tio.cod_titulo::text, '') || ' - ' || COALESCE(tio.descripcion, '') AS titulo_completo,
            tio.c_titulo AS id_titulo,
            {_build_duracion_expr()} AS duracion,
            {_build_norma_expr()} AS norma,
            COALESCE(dt.descripcion, '') AS dictado,
            {_description_expr('req', 'requisito_tipo', "COALESCE(pl.c_requisito::text, '')")} AS requisito,
            {_description_expr('cond', 'condicion_tipo', "COALESCE(pl.c_condicion::text, '')")} AS condicion_ingreso
        FROM plan_estudio_local pl
        JOIN titulo_oferta_tipo tot ON pl.c_titulo_oferta = tot.c_titulo_oferta
        JOIN titulo_tipo tio ON tot.c_titulo = tio.c_titulo
        LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
        LEFT JOIN requisito_tipo req ON pl.c_requisito = req.c_requisito
        LEFT JOIN condicion_tipo cond ON pl.c_condicion = cond.c_condicion
        LEFT JOIN duracion_en_tipo de ON pl.c_duracion_en = de.c_duracion_en
        LEFT JOIN instr_legal_tipo inl ON pl.c_norma = inl.c_instr_legal
        WHERE pl.id_oferta_local = %s
        ORDER BY tio.descripcion
    """

    historial_sql = """
        SELECT
            ce.id_movimiento,
            COALESCE(est.descripcion, '') AS estado_movimiento,
            COALESCE(est.descripcion, '') AS estado,
            COALESCE(ot.descripcion, '') AS carrera,
            COALESCE(m.fecha_inst_legal::text, '') AS fecha_instr_legal,
            COALESCE(m.fecha_vigencia::text, '') AS fecha_vigencia,
            COALESCE(m.observacion, '') AS observacion,
            COALESCE(il.descripcion, '') AS instr_legal,
            COALESCE(mot.descripcion, '') AS motivo,
            COALESCE(m.id_usuario::text, '') AS usuario
        FROM cambio_estado_oferta_local ce
        JOIN movimiento m ON ce.id_movimiento = m.id_movimiento
        JOIN oferta_local ol ON ce.id_oferta_local = ol.id_oferta_local
        JOIN oferta_tipo ot ON ol.c_oferta = ot.c_oferta
        LEFT JOIN estado_tipo est ON ce.c_estado = est.c_estado
        LEFT JOIN instr_legal_tipo il ON m.c_instr_legal = il.c_instr_legal
        LEFT JOIN motivo_tipo mot ON m.c_motivo = mot.c_motivo
        WHERE ce.id_oferta_local = %s
        ORDER BY m.fecha_vigencia DESC
    """

    try:
        oferta = _fetch_one(oferta_sql, [id_oferta])

        if not oferta:
            return JsonResponse({'error': 'Oferta local no encontrada.'}, status=404)

        titulos = _fetch_all(titulos_sql, [id_oferta])
        historial = _fetch_all(historial_sql, [id_oferta])

        return JsonResponse(_sanitize_json_payload({
            'oferta': oferta,
            'titulos': titulos,
            'historial': historial,
        }))
    except Exception as exc:
        return JsonResponse({'error': f'Error al obtener detalle de oferta local: {exc}'}, status=500)

@padron_interno_admin_o_gestor_required
def detalle_titulo_json(request, id_titulo):
    titulo_sql = f"""
        SELECT
            COALESCE(t.descripcion, '') AS titulo,
            COALESCE(t.cod_titulo::text, '') || ' - ' || COALESCE(t.descripcion, '') AS titulo_completo,
            {_build_duracion_expr()} AS duracion,
            {_build_norma_expr()} AS norma,
            COALESCE(dt.descripcion, '') AS dictado,
            {_description_expr('req', 'requisito_tipo', "COALESCE(pl.c_requisito::text, '')")} AS requisito,
            {_description_expr('cond', 'condicion_tipo', "COALESCE(pl.c_condicion::text, '')")} AS condicion_ingreso,
            COALESCE(c.descripcion, '') AS carrera,
            {_description_expr('nt', 'nivel_titulo_tipo', "COALESCE(t.c_nivel_titulo::text, '')")} AS nivel,
            COALESCE(d.descripcion, '') AS disciplina,
            COALESCE(r.descripcion, '') AS rama,
            {_description_expr('ori', 'orientacion_tipo', "COALESCE(pel_sec.c_orientacion::text, '')")} AS orientacion
        FROM titulo_tipo t
        LEFT JOIN carrera_tipo c ON t.c_carrera = c.c_carrera
        LEFT JOIN nivel_titulo_tipo nt ON t.c_nivel_titulo = nt.c_nivel_titulo
        LEFT JOIN disciplina_tipo d ON t.cod_disciplina = d.c_disciplina
        LEFT JOIN rama_tipo r ON t.cod_rama = r.c_rama
        LEFT JOIN titulo_oferta_tipo tot ON t.c_titulo = tot.c_titulo
        LEFT JOIN plan_estudio_local pl ON tot.c_titulo_oferta = pl.c_titulo_oferta
        LEFT JOIN plan_estudio_local_secundaria pel_sec ON pl.id_plan_estudio_local = pel_sec.id_plan_estudio_local
        LEFT JOIN orientacion_tipo ori ON pel_sec.c_orientacion = ori.c_orientacion
        LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
        LEFT JOIN requisito_tipo req ON pl.c_requisito = req.c_requisito
        LEFT JOIN condicion_tipo cond ON pl.c_condicion = cond.c_condicion
        LEFT JOIN duracion_en_tipo de ON pl.c_duracion_en = de.c_duracion_en
        LEFT JOIN instr_legal_tipo inl ON pl.c_norma = inl.c_instr_legal
        WHERE t.c_titulo = %s
        LIMIT 1
    """

    try:
        titulo = _fetch_one(titulo_sql, [id_titulo])

        if not titulo:
            return JsonResponse({'error': 'Titulo no encontrado.'}, status=404)

        return JsonResponse(_sanitize_json_payload({'titulo': titulo}))
    except Exception as exc:
        return JsonResponse({'error': f'Error al obtener detalle del titulo: {exc}'}, status=500)


def _table_exists(table_name):
    return bool(_get_table_columns(table_name))


def _first_column_from_set(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _build_user_display_expr(alias, fallback="''"):
    columns = _get_table_columns('usuario')
    direct_column = _first_column_from_set(
        columns,
        (
            'apellido_nombre',
            'apellido_y_nombre',
            'nombre_completo',
            'nombreyapellido',
            'apynom',
            'apenom',
            'descripcion',
            'nombre',
        ),
    )

    if direct_column:
        return f"COALESCE(BTRIM({alias}.{direct_column}::text), '')"

    surname_column = _first_column_from_set(columns, ('apellido', 'apellidos'))
    name_column = _first_column_from_set(columns, ('nombre', 'nombres'))

    if surname_column and name_column:
        return f"""
            TRIM(
                BOTH ' ' FROM
                CONCAT_WS(
                    ' ',
                    NULLIF(BTRIM({alias}.{surname_column}::text), ''),
                    NULLIF(BTRIM({alias}.{name_column}::text), '')
                )
            )
        """

    if name_column:
        return f"COALESCE(BTRIM({alias}.{name_column}::text), '')"

    return fallback


def _build_username_expr(alias, fallback="''"):
    columns = _get_table_columns('usuario')
    username_column = _first_column_from_set(
        columns,
        ('usuario', 'username', 'login', 'nombre_usuario', 'user_name'),
    )

    if username_column:
        return f"COALESCE(BTRIM({alias}.{username_column}::text), '')"

    return _build_user_display_expr(alias, fallback)


def _build_code_desc_expr(code_expr, desc_expr):
    return f"""
        CASE
            WHEN COALESCE({code_expr}, '') <> '' AND COALESCE({desc_expr}, '') <> '' THEN {code_expr} || ' - ' || {desc_expr}
            WHEN COALESCE({desc_expr}, '') <> '' THEN {desc_expr}
            ELSE COALESCE({code_expr}, '')
        END
    """


def _build_title_heading_expr(code_expr, orient_desc_expr, title_expr):
    return f"""
        CASE
            WHEN COALESCE({code_expr}, '') <> '' AND COALESCE({orient_desc_expr}, '') <> '' AND COALESCE({title_expr}, '') <> '' THEN
                {code_expr} || ' - ' || {orient_desc_expr} || ' - ' || {title_expr}
            WHEN COALESCE({code_expr}, '') <> '' AND COALESCE({title_expr}, '') <> '' THEN
                {code_expr} || ' - ' || {title_expr}
            ELSE
                COALESCE({title_expr}, '')
        END
    """


def _build_norma_expr():
    tipo_expr = _description_expr('inl', 'instr_legal_tipo', "''")
    return f"""
        TRIM(
            BOTH ' ' FROM
            CONCAT_WS(
                ' ',
                NULLIF({tipo_expr}, ''),
                CASE
                    WHEN COALESCE(pl.norma_nro::text, '') <> '' THEN 'nro'
                    ELSE NULL
                END,
                NULLIF(COALESCE(pl.norma_nro::text, ''), '')
            )
        ) ||
        CASE
            WHEN COALESCE(pl.norma_anio::text, '') <> '' THEN ' (' || pl.norma_anio::text || ')'
            ELSE ''
        END
    """


def _normalize_text(value):
    if value is None:
        return ''
    return ' '.join(str(value).split())


def _collapse_repeated_hyphen_value(value):
    normalized = _normalize_text(value)

    if '-' not in normalized:
        return normalized

    for index, char in enumerate(normalized):
        if char != '-':
            continue

        left = normalized[:index].strip()
        right = normalized[index + 1:].strip()

        if left and right and left == right:
            return left

    return normalized


def _clean_code_desc_value(value):
    normalized = _collapse_repeated_hyphen_value(value)

    if '-' not in normalized:
        return normalized

    prefix, suffix = normalized.split('-', 1)
    prefix = prefix.strip()
    suffix = suffix.strip()

    if (
        prefix
        and suffix
        and ' ' not in prefix
        and all(char.isalnum() or char in './' for char in prefix)
    ):
        return suffix

    return normalized


def _format_responsable(apellido, nombre, documento):
    apellido_txt = _normalize_text(apellido)
    nombre_txt = _normalize_text(nombre)
    documento_txt = _normalize_text(documento)

    if apellido_txt and nombre_txt:
        base = f'{apellido_txt}, {nombre_txt}'
    else:
        base = apellido_txt or nombre_txt

    if base:
        return f'{base}({documento_txt})'

    return base or documento_txt


def _postprocess_oferta_payload(oferta):
    if not oferta:
        return oferta

    cleaned = dict(oferta)

    for key in (
        'cabecera_anexo',
        'ambito',
        'tipo_ed',
        'nivel',
        'sector',
        'categoria',
        'acronimo',
        'regional',
        'udt',
        'supervisor_tecnico',
        'descrip_inst_legal',
    ):
        cleaned[key] = _clean_code_desc_value(cleaned.get(key, ''))

    cleaned['responsable'] = _format_responsable(
        cleaned.pop('apellido_responsable', ''),
        cleaned.pop('nombre_responsable', ''),
        cleaned.pop('documento_responsable', ''),
    )

    cleaned['mod_compl_planes'] = _normalize_text(cleaned.get('mod_compl_planes', ''))

    return cleaned

@padron_interno_admin_o_gestor_required
def detalle_oferta_local_json(request, id_oferta):
    historial_user_join = ''
    historial_user_select = "COALESCE(m.id_usuario::text, '') AS usuario"
    tipo_mov_desc_expr = _description_expr('tm', 'tipo_mov_tipo', "''")
    tipo_mov_codigo_col = _first_existing_column('tipo_mov_tipo', ('cod_tipo_mov', 'codigo', 'sigla'))
    if tipo_mov_codigo_col:
        tipo_mov_codigo_expr = f"COALESCE(BTRIM(tm.{tipo_mov_codigo_col}::text), '')"
    else:
        tipo_mov_codigo_expr = f"""
            CASE
                WHEN COALESCE(m.c_tipo_mov::text, '') IN ('1', 'A', 'a') THEN 'A'
                WHEN COALESCE(m.c_tipo_mov::text, '') IN ('2', 'B', 'b') THEN 'B'
                WHEN NULLIF({tipo_mov_desc_expr}, '') IS NOT NULL THEN UPPER(LEFT({tipo_mov_desc_expr}, 1))
                ELSE ''
            END
        """
    titulo_encabezado_expr = _build_title_heading_expr(
        "COALESCE(vpe.c_orientacion::text, '')",
        "COALESCE(vpe.orientacion, '')",
        "COALESCE(vpe.titulo, '')",
    )

    if _table_exists('usuario') and 'id_usuario' in _get_table_columns('usuario'):
        historial_username_expr = _build_username_expr('hist_u', "''")
        historial_user_join = "LEFT JOIN usuario hist_u ON m.id_usuario = hist_u.id_usuario"
        historial_user_select = f"""
            COALESCE(
                NULLIF(BTRIM({historial_username_expr}), ''),
                COALESCE(m.id_usuario::text, '')
            ) AS usuario
        """

    oferta_sql = """
        SELECT
            v.id_oferta_local AS id,
            COALESCE(v.cue::text, '') AS cue,
            COALESCE(v.anexo::text, '') AS anexo,
            COALESCE(v.oferta, '') AS carrera,
            COALESCE(v.oferta, '') AS oferta,
            COALESCE(v.codigo_jurisdiccional_oferta_local, '') AS codigo_jurisdiccional,
            COALESCE(v.estado_ofertalocal, '') AS estado,
            COALESCE(v.subvencion_oferta_local, '') AS subvencion,
            COALESCE(v.fecha_creacion_ofertalocal::text, '') AS fecha_creacion,
            COALESCE(v.fecha_alta_ofertalocal::text, '') AS fecha_alta,
            COALESCE(v.fecha_baja_ofertalocal::text, '') AS fecha_baja,
            COALESCE(v.fecha_actualizacion_ofertalocal::text, '') AS fecha_actualizacion,
            COALESCE(v.jornada_ofertalocal, '') AS jornada,
            COALESCE(v.matricula_total_ofertalocal::text, '') AS matricula_total,
            COALESCE(v.modalidad_basica, '') AS mod_compl_planes,
            COALESCE(v.cp_efvar4, '') AS cuof,
            COALESCE(v.cp_cuof_ryc, '') AS cuof_ryc,
            COALESCE(v.cp_efvar6, '') AS udt,
            COALESCE(v.cp_efvar5, '') AS regional,
            COALESCE(v.cp_acronimo, '') AS acronimo,
            COALESCE(v.cp_supervisortecnico_oferta, '') AS supervisor_tecnico,
            COALESCE(v.cp_tesupervisor_oferta, '') AS tel_supervisor,
            COALESCE(v.cp_mailsupervisor_oferta, '') AS email_supervisor,
            COALESCE(v.cp_efvar2, '') AS cui,
            COALESCE(v.cp_of_cua, '') AS cua,
            COALESCE(v.cp_of_nro_inst_legal, '') AS nro_inst_legal,
            COALESCE(v.cp_of_anio_inst_legal, '') AS anio_creacion,
            COALESCE(v.cp_of_fecha_inst_legal, '') AS fecha_inst_legal,
            COALESCE(v.cp_of_descrip_inst_legal, '') AS descrip_inst_legal,
            COALESCE(v.cp_of_cab_anexo, '') AS cabecera_anexo,
            COALESCE(v.cp_of_ambito, '') AS ambito,
            COALESCE(v.cp_of_tipo_ed, '') AS tipo_ed,
            COALESCE(v.cp_of_nivel, '') AS nivel,
            COALESCE(v.cp_of_sector, '') AS sector,
            COALESCE(v.cp_of_categoria, '') AS categoria,
            COALESCE(r.apellido, '') AS apellido_responsable,
            COALESCE(r.nombre, '') AS nombre_responsable,
            COALESCE(r.nro_documento::text, '') AS documento_responsable,
            COALESCE(v.c_oferta_base::text, '') AS c_oferta_base
        FROM vp_oferta_local v
        LEFT JOIN oferta_local ol ON ol.id_oferta_local = v.id_oferta_local
        LEFT JOIN responsable r ON r.id_responsable = ol.id_responsable
        WHERE v.id_oferta_local = %s
        LIMIT 1
    """

    titulos_sql = f"""
        SELECT
            vpe.id_plan_estudio_local AS id_titulo,
            COALESCE(vpe.titulo, '') AS titulo,
            {titulo_encabezado_expr} AS titulo_completo,
            {_build_duracion_expr()} AS duracion,
            {_build_norma_expr()} AS norma,
            COALESCE(BTRIM(dt.descripcion), '') AS dictado,
            {_description_expr('req', 'requisito_tipo', "COALESCE(pl.c_requisito::text, '')")} AS requisito,
            {_description_expr('cond', 'condicion_tipo', "COALESCE(pl.c_condicion::text, '')")} AS condicion_ingreso
        FROM v_planes_estudio vpe
        JOIN plan_estudio_local pl ON pl.id_plan_estudio_local = vpe.id_plan_estudio_local
        LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
        LEFT JOIN requisito_tipo req ON pl.c_requisito = req.c_requisito
        LEFT JOIN condicion_tipo cond ON pl.c_condicion = cond.c_condicion
        LEFT JOIN duracion_en_tipo de ON pl.c_duracion_en = de.c_duracion_en
        LEFT JOIN instr_legal_tipo inl ON pl.c_norma = inl.c_instr_legal
        WHERE vpe.id_oferta_local = %s
        ORDER BY COALESCE(vpe.titulo, ''), vpe.id_plan_estudio_local
    """

    historial_sql = f"""
        SELECT
            ce.id_movimiento,
            COALESCE(BTRIM(est.descripcion), '') AS estado_movimiento,
            COALESCE(BTRIM(est.descripcion), '') AS estado,
            COALESCE(BTRIM(ot.descripcion), '') AS carrera,
            COALESCE(BTRIM(ot.descripcion), '') AS oferta_local,
            COALESCE(m.fecha_inst_legal::text, '') AS fecha_instr_legal,
            COALESCE(m.fecha_vigencia::text, '') AS fecha_vigencia,
            COALESCE(BTRIM(m.observacion), '') AS observacion,
            CASE
                WHEN COALESCE(m.nro_instr_legal::text, '') <> '' AND COALESCE(BTRIM(il.descripcion), '') <> '' THEN
                    '(' || m.nro_instr_legal::text || ') ' || BTRIM(il.descripcion)
                WHEN COALESCE(m.nro_instr_legal::text, '') <> '' THEN
                    m.nro_instr_legal::text
                ELSE
                    COALESCE(BTRIM(il.descripcion), '')
            END AS instr_legal,
            COALESCE(BTRIM(mot.descripcion), '') AS motivo,
            COALESCE(
                NULLIF(
                    CONCAT_WS(
                        ' - ',
                        NULLIF(m.id_movimiento::text, ''),
                        NULLIF({tipo_mov_codigo_expr}, ''),
                        NULLIF({tipo_mov_desc_expr}, '')
                    ),
                    ''
                ),
                COALESCE(m.id_movimiento::text, '')
            ) AS movimiento,
            {historial_user_select}
        FROM cambio_estado_oferta_local ce
        JOIN movimiento m ON ce.id_movimiento = m.id_movimiento
        JOIN oferta_local ol ON ce.id_oferta_local = ol.id_oferta_local
        JOIN oferta_tipo ot ON ol.c_oferta = ot.c_oferta
        LEFT JOIN estado_tipo est ON ce.c_estado = est.c_estado
        LEFT JOIN tipo_mov_tipo tm ON m.c_tipo_mov = tm.c_tipo_mov
        LEFT JOIN instr_legal_tipo il ON m.c_instr_legal = il.c_instr_legal
        LEFT JOIN motivo_tipo mot ON m.c_motivo = mot.c_motivo
        {historial_user_join}
        WHERE ce.id_oferta_local = %s
        ORDER BY m.fecha_vigencia DESC, m.id_movimiento DESC
    """

    try:
        oferta = _fetch_one(oferta_sql, [id_oferta])

        if not oferta:
            return JsonResponse({'error': 'Oferta local no encontrada.'}, status=404)

        titulos = _fetch_all(titulos_sql, [id_oferta])
        historial = _fetch_all(historial_sql, [id_oferta])

        return JsonResponse(_sanitize_json_payload({
            'oferta': _postprocess_oferta_payload(oferta),
            'titulos': titulos,
            'historial': historial,
        }))
    except Exception as exc:
        return JsonResponse({'error': f'Error al obtener detalle de oferta local: {exc}'}, status=500)

@padron_interno_admin_o_gestor_required
def detalle_titulo_json(request, id_titulo):
    orientacion_desc_expr = _description_expr('ori', 'orientacion_tipo', "''")
    orientacion_expr = _build_code_desc_expr(
        "COALESCE(pel_sec.c_orientacion::text, '')",
        orientacion_desc_expr,
    )

    titulo_sql = f"""
        SELECT
            COALESCE(BTRIM(t.descripcion), '') AS titulo,
            COALESCE(t.cod_titulo::text, '') || ' - ' || COALESCE(BTRIM(t.descripcion), '') AS titulo_completo,
            {_build_duracion_expr()} AS duracion,
            {_build_norma_expr()} AS norma,
            COALESCE(BTRIM(dt.descripcion), '') AS dictado,
            {_description_expr('req', 'requisito_tipo', "COALESCE(pl.c_requisito::text, '')")} AS requisito,
            {_description_expr('cond', 'condicion_tipo', "COALESCE(pl.c_condicion::text, '')")} AS condicion_ingreso,
            COALESCE(BTRIM(c.descripcion), '') AS carrera,
            {_description_expr('nt', 'nivel_titulo_tipo', "COALESCE(t.c_nivel_titulo::text, '')")} AS nivel,
            COALESCE(BTRIM(d.descripcion), '') AS disciplina,
            COALESCE(BTRIM(r.descripcion), '') AS rama,
            {orientacion_expr} AS orientacion
        FROM plan_estudio_local pl
        JOIN titulo_oferta_tipo tot ON pl.c_titulo_oferta = tot.c_titulo_oferta
        JOIN titulo_tipo t ON tot.c_titulo = t.c_titulo
        LEFT JOIN carrera_tipo c ON t.c_carrera = c.c_carrera
        LEFT JOIN nivel_titulo_tipo nt ON t.c_nivel_titulo = nt.c_nivel_titulo
        LEFT JOIN disciplina_tipo d ON c.c_disciplina = d.c_disciplina
        LEFT JOIN rama_tipo r ON t.cod_rama = r.c_rama
        LEFT JOIN plan_estudio_local_secundaria pel_sec ON pl.id_plan_estudio_local = pel_sec.id_plan_estudio_local
        LEFT JOIN orientacion_tipo ori ON pel_sec.c_orientacion = ori.c_orientacion
        LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
        LEFT JOIN requisito_tipo req ON pl.c_requisito = req.c_requisito
        LEFT JOIN condicion_tipo cond ON pl.c_condicion = cond.c_condicion
        LEFT JOIN duracion_en_tipo de ON pl.c_duracion_en = de.c_duracion_en
        LEFT JOIN instr_legal_tipo inl ON pl.c_norma = inl.c_instr_legal
        WHERE pl.id_plan_estudio_local = %s
        LIMIT 1
    """

    try:
        titulo = _fetch_one(titulo_sql, [id_titulo])

        if not titulo:
            return JsonResponse({'error': 'Titulo no encontrado.'}, status=404)

        return JsonResponse(_sanitize_json_payload({'titulo': titulo}))
    except Exception as exc:
        return JsonResponse({'error': f'Error al obtener detalle del titulo: {exc}'}, status=500)

@padron_interno_admin_o_gestor_required
def listar_ofertas_locales(request):
    formato = request.GET.get('formato')

    if formato == 'excel_todo':
        where, params = '', []
    else:
        where, params = _build_where(request)

    orden_key = request.GET.get('orden', 'cue')
    col_orden = CAMPO_SQL.get(orden_key, 'e.cue::text')

    data_sql = f"{_SELECT_FIELDS} {_BASE_SQL} {where} ORDER BY {col_orden}, l.anexo"

    if formato in ['excel_pagina', 'excel_todo']:
        datos_exportar = _fetch_all(data_sql, params)
        return _exportar_excel(datos_exportar, formato, request)

    count_sql = f"SELECT COUNT(*) {_BASE_SQL} {where}"

    try:
        current_page_size = int(request.GET.get('page_size', PAGE_SIZE))
    except (ValueError, TypeError):
        current_page_size = PAGE_SIZE

    raw = _RawPage(data_sql, count_sql, params, PADRON_DB)
    paginator = Paginator(raw, current_page_size)

    try:
        page_number = request.GET.get('page', 1)
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    total = len(raw)
    desde = (page_obj.number - 1) * current_page_size + 1 if total else 0
    hasta = min(page_obj.number * current_page_size, total)

    return render(request, 'padroninterno/ofertaslocales.html', {
        'lista_items': page_obj.object_list,
        'page_obj': page_obj,
        'resultado_total': total,
        'resultado_desde': desde,
        'resultado_hasta': hasta,
        'username': getattr(request.user, 'username', ''),
    })
