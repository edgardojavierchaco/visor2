from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.db import transaction

from .models import Personas, RegistroActividades, NomencladorCeic, Localidades, CodAreasTelefonos
from .forms import PersonaForm, ActividadFormSet
from .utils import get_ofertas_usuario
from apps.consultasge.models_padron import CapaUnicaOfertas

from .services.registro_service import RegistroService
from django.shortcuts import get_object_or_404


# =========================
# FILTRO CEIC (limpio)
# =========================
def filtrar_ceic(request):

    modalidad = request.GET.get("modalidad")
    nivel = request.GET.get("nivel")

    print("MODALIDAD:", modalidad)
    print("NIVEL:", nivel)

    qs = NomencladorCeic.objects.all()

    if nivel:
        qs = qs.filter(
            t_nivel="Nivel",
            c_niv=int(nivel)
        )

    elif modalidad:
        qs = qs.filter(
            t_nivel="Modalidad",
            c_niv=int(modalidad)
        )

    print("SQL:", qs.query)
    print("COUNT:", qs.count())

    data = list(
        qs.values("c_ceic", "descripcion")
    )

    return JsonResponse(data, safe=False)


# =========================
# CARGA PERSONAL (CORE)
# =========================
def carga_personal(request, pk=None):

    persona = None

    # =========================
    # CASO 2 y 3: existe persona
    # =========================
    if pk:
        persona = get_object_or_404(
            Personas.objects.select_related(
                "sexo",
                "provincia",
                "localidad",
                "codigo_area"
            ),
            pk=pk
        )

    if request.method == "POST":

        form = PersonaForm(
            request.POST,
            instance=persona
        )

        formset = ActividadFormSet(
            request.POST,
            instance=persona,
            user=request.user
        )

        if form.is_valid() and formset.is_valid():

            with transaction.atomic():

                # ==================================================
                # PERSONA (SOLO SI SE ENVÍA DATA Y CAMBIOS)
                # ==================================================
                persona_obj = form.save(commit=False)

                es_nueva_persona = not persona_obj.pk
                
                if es_nueva_persona:
                    persona_obj.usuario_creacion = request.user

                persona_obj.usuario_modificacion = request.user

                persona_obj.full_clean()
                persona_obj.save()

                # ==================================================
                # ACTIVIDADES SIEMPRE
                # ==================================================
                RegistroService.sync_actividades(
                    persona=persona_obj,
                    forms=formset.forms,
                    user=request.user
                )

            return redirect("bnhpersonas:personas_detail", pk=persona_obj.pk)

    else:

        form = PersonaForm(instance=persona)

        formset = ActividadFormSet(
            instance=persona,
            user=request.user
        )

    return render(request, "bnh/personas/carga_personal.html", {
        "form": form,
        "formset": formset,
        "persona": persona
    })


# =========================
# BUSCAR PERSONA (limpio)
# =========================
def buscar_persona(request):

    cuil = request.GET.get("cuil")

    if not cuil:
        return JsonResponse({}, status=400)

    persona = (
        Personas.objects
        .select_related(
            "sexo",
            "provincia",
            "localidad",
            "codigo_area"
        )
        .filter(cuil=cuil)
        .first()
    )

    if not persona:
        return JsonResponse({
            "existe": False
        })

    codigo_area = getattr(
        persona,
        "codigo_area",
        None
    )

    return JsonResponse({

        "existe": True,

        "dni":
            persona.dni,

        "apellido":
            persona.apellido,

        "nombre":
            persona.nombre,

        "sexo":
            persona.sexo_id,

        "f_nac":
            getattr(
                persona,
                "f_nac",
                None
            ),

        "provincia":
            persona.provincia_id,

        "localidad":
            persona.localidad_id,

        "telefono":
            persona.telefono or "",

        "whatsapp":
            bool(
                getattr(
                    persona,
                    "whatsapp",
                    False
                )
            ),

        "codigo_area":
            codigo_area.id
            if codigo_area
            else "",

        "codigo_area_label":
            str(codigo_area)
            if codigo_area
            else "",
    })
    
    

def filtrar_localidades(request):

    provincia_id = request.GET.get("provincia")

    if not provincia_id:
        return JsonResponse([], safe=False)

    qs = (Localidades.objects.filter(
        c_provincia_id=provincia_id
    )
    .order_by("descrip_localidad")
    
    .values("c_localidad", "descrip_localidad")
    )

    return JsonResponse(list(qs), safe=False)


def buscar_codigos_area(request):
    q = request.GET.get("q", "").strip()

    qs = CodAreasTelefonos.objects.all()

    if q:
        # 🔥 solo números
        qs = qs.filter(codigo__startswith=q)

    qs = qs.order_by("codigo")[:20]

    data = [
        {
            "id": c.id,
            "label": f"{c.codigo} - {c.localidad} ({c.provincia})"
        }
        for c in qs
    ]

    return JsonResponse(data, safe=False)