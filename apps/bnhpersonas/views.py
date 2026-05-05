from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db import transaction

from django.core.exceptions import ValidationError

from .models import Personas, RegistroActividades, NomencladorCeic, Localidades
from .forms import PersonaForm, ActividadFormSet
from .utils import get_cueanexos_usuario
from apps.consultasge.models_padron import CapaUnicaOfertas

from .services.registro_service import RegistroService


# =========================
# FILTRO CEIC (limpio)
# =========================
def filtrar_ceic(request):

    modalidad = request.GET.get("modalidad")
    nivel = request.GET.get("nivel")

    qs = NomencladorCeic.objects.all()

    if modalidad:
        modalidad = int(modalidad)

        qs = qs.filter(
            t_nivel="Nivel" if modalidad == 1 else "Modalidad",
            c_niv=nivel if modalidad == 1 and nivel else modalidad
        )
    
    data = list(qs.values("c_ceic", "descripcion"))

    return JsonResponse(data, safe=False)


# =========================
# CARGA PERSONAL (CORE)
# =========================
def carga_personal(request):

    if request.method == "POST":
        
        form = PersonaForm(request.POST)
        
        # ⚠️ primero creamos instancia dummy para formset
        persona = Personas()
        
        formset = ActividadFormSet(
            request.POST,
            instance=persona,
            user=request.user
        )


        if form.is_valid() and formset.is_valid():

            with transaction.atomic():

                # =========================
                # 🔥 TODO EL NEGOCIO SE VA AL SERVICE
                # =========================
                persona = RegistroService.upsert_persona(form)

                RegistroService.crear_actividades(
                    persona=persona,
                    forms=formset.forms,
                    user=request.user
                )

                return redirect("carga_personal")

    else:
        form = PersonaForm()
        
        persona = Personas()  # instancia dummy para formset
        formset = ActividadFormSet(
            instance=persona,
            user=request.user
        )

    return render(request, "bnh/personas/carga_personal.html", {
        "form": form,
        "formset": formset,
    })


# =========================
# BUSCAR PERSONA (limpio)
# =========================
def buscar_persona(request):

    cuil = request.GET.get("cuil")

    if not cuil:
        return JsonResponse({}, status=400)

    persona = Personas.objects.filter(cuil=cuil).first()

    if not persona:
        return JsonResponse({"existe": False})

    return JsonResponse({
        "existe": True,
        "dni": persona.dni,
        "apellido": persona.apellido,
        "nombre": persona.nombre,
        "sexo": persona.sexo_id,
        "f_nac": getattr(persona, "f_nac", None),
        "provincia": persona.provincia_id,
        "localidad": persona.localidad_id,
        "telefono": persona.telefono_normalizado,
    })
    

def filtrar_localidades(request):

    provincia_id = request.GET.get("provincia")

    if not provincia_id:
        return JsonResponse([], safe=False)

    qs = Localidades.objects.filter(
        c_provincia_id=provincia_id
    ).values("c_localidad", "descrip_localidad")

    return JsonResponse(list(qs), safe=False)