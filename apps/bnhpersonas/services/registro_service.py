# services/registro_service.py
from django.core.exceptions import ValidationError

from apps.bnhpersonas.models import RegistroActividades
from apps.bnhpersonas.utils import get_ofertas_usuario
from .bulk_service import BulkService


class RegistroService:

    # =========================
    # SOLO ACTIVIDADES (CRUD)
    # =========================
    @staticmethod
    def sync_actividades(persona, forms, user):

        cueanexos = set(
            str(x)
            for x in get_ofertas_usuario(user)
            .values_list("cueanexo", flat=True)
        )

        nuevas = []

        for f in forms:

            cd = getattr(f, "cleaned_data", None)
            if not cd:
                continue

            # =========================
            # DELETE
            # =========================
            if cd.get("DELETE"):

                if f.instance.pk:

                    if f.instance.persona_id != persona.id:
                        raise ValidationError("No autorizado")

                    f.instance.delete()

                continue

            cue = str(cd.get("cueanexo"))

            if cue not in cueanexos:
                raise ValidationError(f"CUE {cue} no autorizado")

            obj = f.save(commit=False)

            obj.persona = persona
            obj.cueanexo = cue

            # =========================
            # UPDATE
            # =========================
            if obj.pk:

                if obj.persona_id != persona.id:
                    raise ValidationError("No autorizado")

                obj.usuario_modificacion = user
                obj.full_clean()
                obj.save()

            # =========================
            # CREATE
            # =========================
            else:

                obj.usuario_creacion = user
                obj.usuario_modificacion = user
                obj.full_clean()

                nuevas.append(obj)

        if nuevas:
            return BulkService.safe_bulk_create(
                RegistroActividades,
                nuevas,
                user=user,
                source="carga_personal"
            )

        return {"created": [], "errors": []}