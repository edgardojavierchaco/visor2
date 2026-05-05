from django.core.exceptions import ValidationError

from apps.bnhpersonas.models import Personas, RegistroActividades
from .bulk_service import BulkService
from apps.consultasge.models_padron import CapaUnicaOfertas
from apps.bnhpersonas.utils import get_ofertas_usuario


class RegistroService:

    # =========================
    # PERSONA UPSERT
    # =========================
    @staticmethod
    def upsert_persona(form):

        dni = form.cleaned_data.get("dni")
        cuil = form.cleaned_data.get("cuil")

        persona = None

        if cuil:
            persona = Personas.objects.filter(cuil=cuil).first()

        if persona is None and dni:
            persona = Personas.objects.filter(dni=dni).first()

        if persona:
            for k, v in form.cleaned_data.items():
                if v and not getattr(persona, k):
                    setattr(persona, k, v)
            persona.save()
        else:
            persona = form.save()

        return persona


    # =========================
    # ACTIVIDADES
    # =========================
    @staticmethod
    def crear_actividades(persona, forms, user):

        cueanexos = set(get_cueanexos_usuario(user))

        cue_map = {
            c.cueanexo: c
            for c in CapaUnicaOfertas.objects.filter(cueanexo__in=cueanexos)
        }

        actividades = []

        for f in forms:

            cd = getattr(f, "cleaned_data", None)

            if not cd or cd.get("DELETE"):
                continue

            cue = cd.get("cueanexo")
            ceic = cd.get("ceic")

            if cue not in cueanexos:
                raise ValidationError("CUE no autorizado")

            cue_obj = cue_map.get(cue)

            if not cue_obj:
                raise ValidationError("CUE inexistente")

            obj = f.save(commit=False)
            obj.persona = persona
            obj.cueanexo = cue

            actividades.append(obj)

        return BulkService.safe_bulk_create(
            RegistroActividades,
            actividades
        )