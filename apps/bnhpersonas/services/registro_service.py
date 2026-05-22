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

        # =========================
        # BUSQUEDA
        # =========================
        if cuil:
            persona = Personas.objects.filter(
                cuil=cuil
            ).first()

        if (
            persona is None and dni
        ):
            persona = Personas.objects.filter(
                dni=dni
            ).first()

        # =========================
        # EXISTE
        # =========================
        if persona:
            for k, v in form.cleaned_data.items():
                if v not in (
                    None,
                    "",
                ):
                    setattr(persona, 
                            k, 
                            v
                        )
            
            # AUDITORIA
            persona.usuario_modificacion = user
            
            persona.save()
        
        # =========================
        # NUEVA
        # =========================
        else:
            persona = form.save(
                commit=False
            )

            # AUDITORIA
            persona.usuario_creacion = user
            persona.usuario_modificacion = user

            persona.save()

        return persona


    # =========================
    # ACTIVIDADES
    # =========================
    @staticmethod
    def crear_actividades(persona, forms, user):

        cueanexos = set(
            str(x)
            for x in get_ofertas_usuario(user)
            .values_list("cueanexo", flat=True)
        )    
        
        print("USER:", user.username)
        print("CUES USUARIO:", cueanexos)

        actividades = []

        for f in forms:

            cd = getattr(f, "cleaned_data", None)

            if not cd or cd.get("DELETE"):
                continue

            cue = cd.get("cueanexo")
            ceic = cd.get("ceic")
            
            print("USER:", user.username)
            print("CUES USUARIO:", list(cueanexos))
            print("CUE FORM:", cue)
            
            if cue not in cueanexos:
                raise ValidationError(f"CUE {cue} no autorizado para este usuario")

            obj = f.save(commit=False)
            obj.persona = persona
            obj.cueanexo = cue

            actividades.append(obj)

        return BulkService.safe_bulk_create(
            RegistroActividades,
            actividades,
            user=user,
            source='carga_personal'
        )