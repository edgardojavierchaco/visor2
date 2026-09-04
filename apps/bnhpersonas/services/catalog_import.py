"""Importación de los CSV normalizados: validación completa, ensayo y aplicación atómica."""
import csv
from pathlib import Path
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction, connection
from django.core.management.color import no_style
from ..models import Modalidades, NivelServicio, ModalidadNivel, ModalidadNivelCeic, Grado_anio, Secciones, RegistroActividades
from ..domain.access import is_admin
from .crud import audit, snapshot

SPECS = (
    ('modalidades_tipo.csv', Modalidades, ('c_modalidad', 'descrip_modalidad')),
    ('nivel_servicio.csv', NivelServicio, ('c_nivel', 'descrip_nivel')),
    ('grado_anio.csv', Grado_anio, ('c_grado_anio','nombre_grado_anio','estado','c_niv_grado','t_niv_grado','c_modalidad')),
    ('Secciones.csv', Secciones, ('c_seccion','nombre_seccion','estado','c_niv_seccion','t_niv_seccion','c_modalidad')),
)


def read_table(path, columns):
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(columns):
            raise ValidationError(f'{path.name}: encabezados inesperados; utilice los CSV normalizados.')
        rows=[]; keys=set()
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValidationError(f'{path.name}, fila {line}: columnas incompletas.')
            for key, value in row.items():
                value=value.strip()
                if key.startswith('c_'):
                    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
                        raise ValidationError(f'{path.name}, fila {line}: {key} debe ser un entero positivo.')
                    row[key]=int(value)
                elif key == 'estado':
                    if value not in ('true','false'):
                        raise ValidationError(f'{path.name}, fila {line}: estado debe ser true o false.')
                    row[key]=value=='true'
                else:
                    if not value:
                        raise ValidationError(f'{path.name}, fila {line}: {key} está vacío.')
                    row[key]=value
            identity = tuple(row[c] for c in columns) if path.name == 'modalidad_nivel.csv' else row[columns[0]]
            if identity in keys:
                raise ValidationError(f'{path.name}: identificador duplicado {identity}.')
            keys.add(identity);rows.append(row)
        return rows


def load_catalogs(directory):
    directory=Path(directory)
    data={name:read_table(directory/name, columns) for name, _, columns in SPECS}
    data['modalidad_nivel.csv']=read_table(directory/'modalidad_nivel.csv',('c_modalidad','c_nivel'))
    mods={r['c_modalidad'] for r in data['modalidades_tipo.csv']}
    levels={r['c_nivel'] for r in data['nivel_servicio.csv']}
    pairs={(r['c_modalidad'],r['c_nivel']) for r in data['modalidad_nivel.csv']}
    for mod,niv in pairs:
        if mod not in mods or niv not in levels:
            raise ValidationError('modalidad_nivel.csv contiene una referencia inexistente.')
    inferred=set()
    for filename,niv,typ in [('grado_anio.csv','c_niv_grado','t_niv_grado'),('Secciones.csv','c_niv_seccion','t_niv_seccion')]:
        for row in data[filename]:
            pair=(row['c_modalidad'],row[niv])
            if pair not in pairs or row[typ] != 'Nivel':
                raise ValidationError(f'{filename}: relación inválida o tipo diferente de Nivel.')
            inferred.add(pair)
    if inferred != pairs:
        raise ValidationError('Las relaciones modalidad/nivel deben coincidir con las presentes en grados y secciones.')
    return data


def meaningful_text(value):
    return ' '.join(str(value or '').split()).casefold()


@transaction.atomic
def import_catalogs(directory, *, apply=False, actor=None):
    if apply and not is_admin(actor):
        raise PermissionDenied('Para aplicar la importación se requiere un administrador activo.')
    data=load_catalogs(directory)
    stats={}; conflicts=[]; updates=[]
    for filename, model, columns in SPECS:
        stats[filename]={'crear':0,'actualizar':0,'sin_cambios':0}
        for row in data[filename]:
            pk=row[columns[0]]
            previous=model.objects.select_for_update().filter(pk=pk).first()
            obj=previous or model()
            before=snapshot(previous) if previous else {}
            if model in (Grado_anio,Secciones):
                field='grado_anio' if model is Grado_anio else 'secciones'
                niv='c_niv_grado' if model is Grado_anio else 'c_niv_seccion'
                label='nombre_grado_anio' if model is Grado_anio else 'nombre_seccion'
                used=RegistroActividades.objects.filter(**{field+'_id':pk})
                mismatch=used.exclude(modalidad_id=row['c_modalidad'],niveles_id=row[niv])
                if previous and meaningful_text(getattr(previous,label)) != meaningful_text(row[label]):
                    mismatch=used
                ids=list(mismatch.values_list('pk',flat=True)[:30])
                if ids:
                    conflicts.append({'archivo':filename,'id':pk,'actividades_a_revisar':ids,'limite_muestra':30})
            for field,value in row.items():
                setattr(obj,field,value)
            obj.full_clean()
            changed=not previous or any(before.get(key)!=value for key,value in row.items())
            category='crear' if not previous else ('actualizar' if changed else 'sin_cambios')
            stats[filename][category]+=1
            if changed: updates.append((obj,before))
    result={'aplicado':False,'tablas':stats,'conflictos':conflicts,'relaciones_solicitadas':len(data['modalidad_nivel.csv'])}
    configured=set(ModalidadNivelCeic.objects.values_list('modalidad_id','nivel_id'))
    result['pares_sin_configuracion_ceic']=[row for row in data['modalidad_nivel.csv'] if (row['c_modalidad'],row['c_nivel']) not in configured]
    if conflicts or not apply:
        return result
    for obj,before in updates:
        obj.save()
        audit(actor,obj,'IMPORTAR_CATALOGO',before,reason='Importación validada de CSV.')
    count=0
    for row in data['modalidad_nivel.csv']:
        obj,created=ModalidadNivel.objects.get_or_create(modalidad_id=row['c_modalidad'],nivel_id=row['c_nivel'])
        if created:
            count+=1
            audit(actor,obj,'IMPORTAR_CATALOGO',reason='Relación derivada de los CSV de grados/secciones.')
    # Evita colisiones de próximos IDs automáticos tras insertar códigos explícitos.
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(),[Grado_anio,Secciones,ModalidadNivel]):
            cursor.execute(sql)
    result.update(aplicado=True,relaciones_creadas=count)
    return result
