"""
Importación segura de catálogos BNH.

Se mantienen separados:
  * catálogos legacy de Cargo / CEIC;
  * catálogos nuevos del circuito curricular.

El comando funciona en modo simulación por defecto y sólo escribe con --aplicar.
"""
import csv
from pathlib import Path

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.core.management.color import no_style

from ..domain.access import is_admin
from ..models import (
    EspacioCurricularNombre,
    Grado_anio,
    Modalidades,
    ModalidadNivel,
    ModalidadNivelCeic,
    ModalidadTipo,
    NivelServicio,
    NivelServicioTipo,
    RegistroActividades,
    RevisionCatalogos,
    Secciones,
    TitulacionFP,
    TitulacionNombre,
    TitulacionSuperior,
    TipoPersonal,
    CondicionActividadNombre,
)
from .crud import audit, snapshot
from .concurrency import advisory_xact_lock, configure_transaction


LEGACY_SPECS = (
    ("modalidades_tipo.csv", Modalidades, ("c_modalidad", "descrip_modalidad")),
    ("nivel_servicio.csv", NivelServicio, ("c_nivel", "descrip_nivel")),
)

CURRICULAR_SPECS = (
    ("modalidad1_tipo.csv", ModalidadTipo, ("id", "c_modalidad1", "descripcion", "orden")),
    ("nivel_servicio_tipo.csv", NivelServicioTipo, ("c_nivel", "descripcion", "c_modalidad1")),
    ("titulacion_nombre.csv", TitulacionNombre, (
        "id", "id_nombre_titulacion", "id_titulacion", "descripcion_adicional",
        "nombre", "c_nivel_servicio", "c_modalidad1",
    )),
    ("titulacion_superior.csv", TitulacionSuperior, (
        "id", "id_titulacion", "c_nivel_servicio", "c_modalidad1", "descripcion",
    )),
    ("titulacion_fp.csv", TitulacionFP, (
        "id", "id_titulacion", "c_nivel_servicio", "c_modalidad1", "descripcion",
    )),
    ("espacio_curricular_nombre.csv", EspacioCurricularNombre, (
        "id", "id_espacio_curricular", "id_titulacion", "id_nombre_espacio_curricular", "nombre",
    )),
    ("Secciones.csv", Secciones, (
        "c_seccion", "nombre_seccion", "estado", "c_niv_seccion", "t_niv_seccion", "c_modalidad1",
    )),
)

PERSONAL_SPECS = (
    ("tipo_personal.csv", TipoPersonal, ("id", "c_tpersonal", "descripcion")),
    (
        "condicion_actividad_nombre.csv",
        CondicionActividadNombre,
        (
            "id", "c_nomen", "encuadre", "sit_rev",
            "c_homo_sit_rev", "c_homo_c_act",
            "denominacion", "t_personal",
        ),
    ),
)

GRADE_FILENAMES = ("grado_anio.csv", "gardo_anio.csv")
GRADE_COLUMNS = (
    "c_grado_anio", "nombre_grado_anio", "estado", "c_niv_grado", "t_niv_grado", "c_modalidad1",
)

INTEGER_FIELDS = {
    "id", "c_modalidad", "c_modalidad1", "c_nivel", "c_niv_grado", "c_niv_seccion",
    "c_grado_anio", "c_seccion", "id_nombre_titulacion", "id_titulacion",
    "c_nivel_servicio", "id_espacio_curricular", "id_nombre_espacio_curricular",
    "c_tpersonal", "sit_rev", "c_homo_sit_rev", "c_homo_c_act", "t_personal",
}


def parse_value(filename, line, key, raw):
    value = (raw or "").strip()
    if key == "estado":
        lowered = value.casefold()
        if lowered not in ("true", "false", "1", "0", "si", "sí", "no"):
            raise ValidationError(f"{filename}, fila {line}: estado inválido.")
        return lowered in ("true", "1", "si", "sí")

    if key in INTEGER_FIELDS:
        if not value or not value.lstrip("-").isascii() or not value.lstrip("-").isdecimal():
            raise ValidationError(f"{filename}, fila {line}: {key} debe ser entero.")
        return int(value)

    if not value and key not in ("descripcion_adicional",):
        raise ValidationError(f"{filename}, fila {line}: {key} está vacío.")
    return value


def read_table(path, columns):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(columns):
            raise ValidationError(
                f"{path.name}: encabezados inesperados. Esperado: {', '.join(columns)}"
            )
        rows = []
        identities = set()
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValidationError(f"{path.name}, fila {line}: columnas incompletas.")
            parsed = {k: parse_value(path.name, line, k, v) for k, v in row.items()}
            identity = parsed[columns[0]]
            if identity in identities:
                raise ValidationError(f"{path.name}: identificador duplicado {identity}.")
            identities.add(identity)
            rows.append(parsed)
        return rows


def existing_grade_path(directory):
    for name in GRADE_FILENAMES:
        path = directory / name
        if path.exists():
            return path
    return None


def load_catalogs(directory):
    directory = Path(directory)
    data = {}

    for filename, _model, columns in LEGACY_SPECS + CURRICULAR_SPECS + PERSONAL_SPECS:
        path = directory / filename
        if path.exists():
            data[filename] = read_table(path, columns)

    grade_path = existing_grade_path(directory)
    if grade_path:
        data[grade_path.name] = read_table(grade_path, GRADE_COLUMNS)

    legacy_pairs_path = directory / "modalidad_nivel.csv"
    if legacy_pairs_path.exists():
        data["modalidad_nivel.csv"] = read_table(
            legacy_pairs_path, ("c_modalidad", "c_nivel")
        )

    # Validación del circuito curricular.
    if "modalidad1_tipo.csv" in data and "nivel_servicio_tipo.csv" in data:
        modalidad_codes = {r["c_modalidad1"] for r in data["modalidad1_tipo.csv"]}
        for row in data["nivel_servicio_tipo.csv"]:
            if row["c_modalidad1"] not in modalidad_codes:
                raise ValidationError(
                    "nivel_servicio_tipo.csv contiene una modalidad1 inexistente."
                )

    level_pairs = set()
    if "nivel_servicio_tipo.csv" in data:
        level_pairs = {
            (r["c_modalidad1"], r["c_nivel"])
            for r in data["nivel_servicio_tipo.csv"]
        }

    for filename, nivel_field in (
        (grade_path.name if grade_path else "", "c_niv_grado"),
        ("Secciones.csv", "c_niv_seccion"),
    ):
        if filename and filename in data and level_pairs:
            for row in data[filename]:
                if row["t_niv_grado" if nivel_field == "c_niv_grado" else "t_niv_seccion"].casefold() != "nivel":
                    raise ValidationError(f"{filename}: sólo se admite t_niv='Nivel'.")
                if (row["c_modalidad1"], row[nivel_field]) not in level_pairs:
                    raise ValidationError(
                        f"{filename}: modalidad/nivel curricular inexistente."
                    )

    return data


def meaningful_text(value):
    return " ".join(str(value or "").split()).casefold()


def get_specs_for_data(data):
    specs = []
    lookup = {name: (model, columns) for name, model, columns in LEGACY_SPECS + CURRICULAR_SPECS + PERSONAL_SPECS}
    for filename in data:
        if filename in lookup:
            model, columns = lookup[filename]
            specs.append((filename, model, columns))
        elif filename in GRADE_FILENAMES:
            specs.append((filename, Grado_anio, GRADE_COLUMNS))
    return specs


@transaction.atomic
def import_catalogs(directory, *, apply=False, actor=None):
    if apply and not is_admin(actor):
        raise PermissionDenied(
            "Para aplicar la importación se requiere un administrador activo."
        )

    revision = None
    if apply:
        configure_transaction()
        advisory_xact_lock("bnh:catalogos", "global")
        revision, _ = RevisionCatalogos.objects.select_for_update().get_or_create(
            pk=1, defaults={"version": 1, "actualizado_por": actor}
        )

    data = load_catalogs(directory)
    stats = {}
    conflicts = []
    updates = []

    for filename, model, columns in get_specs_for_data(data):
        stats[filename] = {"crear": 0, "actualizar": 0, "sin_cambios": 0}
        for row in data[filename]:
            pk = row[columns[0]]
            previous = model.objects.select_for_update().filter(pk=pk).first()
            obj = previous or model()
            before = snapshot(previous) if previous else {}

            # Grado/sección ya pertenecen al circuito curricular.
            if model in (Grado_anio, Secciones):
                relation_field = "grado_anio" if model is Grado_anio else "secciones"
                niv = "c_niv_grado" if model is Grado_anio else "c_niv_seccion"
                label = "nombre_grado_anio" if model is Grado_anio else "nombre_seccion"
                used = RegistroActividades.objects.filter(**{relation_field + "_id": pk})
                mismatch = used.exclude(
                    modalidad_curricular__c_modalidad1=row["c_modalidad1"],
                    nivel_curricular_id=row[niv],
                )
                if previous and meaningful_text(getattr(previous, label)) != meaningful_text(row[label]):
                    mismatch = used
                ids = list(mismatch.values_list("pk", flat=True)[:30])
                if ids:
                    conflicts.append({
                        "archivo": filename,
                        "id": pk,
                        "actividades_a_revisar": ids,
                        "limite_muestra": 30,
                    })

            for field, value in row.items():
                setattr(obj, field, value)
            obj.full_clean()

            changed = not previous or any(before.get(key) != value for key, value in row.items())
            category = "crear" if not previous else ("actualizar" if changed else "sin_cambios")
            stats[filename][category] += 1
            if changed:
                updates.append((obj, before))

    result = {
        "aplicado": False,
        "tablas": stats,
        "conflictos": conflicts,
    }

    # Información legacy CEIC, sin modificar su lógica.
    if "modalidad_nivel.csv" in data:
        configured = set(ModalidadNivelCeic.objects.values_list("modalidad_id", "nivel_id"))
        result["pares_sin_configuracion_ceic"] = [
            row for row in data["modalidad_nivel.csv"]
            if (row["c_modalidad"], row["c_nivel"]) not in configured
        ]

    if conflicts or not apply:
        return result

    for obj, before in updates:
        obj.save()
        audit(actor, obj, "IMPORTAR_CATALOGO", before, reason="Importación validada de CSV.")

    # Relaciones legacy modalidad/nivel sólo si se suministró el archivo.
    created_pairs = 0
    for row in data.get("modalidad_nivel.csv", []):
        obj, created = ModalidadNivel.objects.get_or_create(
            modalidad_id=row["c_modalidad"],
            nivel_id=row["c_nivel"],
        )
        if created:
            created_pairs += 1
            audit(actor, obj, "IMPORTAR_CATALOGO", reason="Relación legacy Cargo/CEIC.")

    with connection.cursor() as cursor:
        reset_models = [
            Grado_anio,
            Secciones,
            ModalidadNivel,
            ModalidadTipo,
            TitulacionNombre,
            TitulacionSuperior,
            TitulacionFP,
            EspacioCurricularNombre,
        ]
        for sql in connection.ops.sequence_reset_sql(no_style(), reset_models):
            cursor.execute(sql)

    if updates or created_pairs:
        before_revision = snapshot(revision)
        revision.version += 1
        revision.actualizado_por = actor
        revision.save(update_fields=["version", "actualizado_por", "actualizado_en"])
        audit(
            actor,
            revision,
            "ACTUALIZAR_VERSION_CATALOGOS",
            before_revision,
            reason="Aplicación de catálogos BNH.",
        )

    result.update(
        aplicado=True,
        relaciones_creadas=created_pairs,
        version_catalogos=revision.version,
    )
    return result
