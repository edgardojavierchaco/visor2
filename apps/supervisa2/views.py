from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.supervisa2.models.supervisor import Supervisor2
from apps.supervisa2.forms import Supervisor2DynamicForm

from apps.supervisa2.selectors.supervisor_selector import (
    get_supervisores_por_region,
    get_supervisores_global,
    get_supervisor_by_user
)

from apps.supervisa2.services.supervisor_service import crear_o_actualizar_supervisor
from apps.supervisa2.services.regional_service import validar_supervisor_regional


# =========================================================
# 🧠 ROLE
# =========================================================
def get_user_role(user):

    if user.is_superuser:
        return "ADMIN"

    if hasattr(user, "perfil") and user.perfil and user.perfil.rol:
        return user.perfil.rol.nombre.upper()

    return "SUPERVISOR"


# =========================================================
# 🔐 PERMISOS OBJETO
# =========================================================
def get_supervisor_or_403(user, pk):

    obj = get_object_or_404(Supervisor2, pk=pk)

    role = get_user_role(user)

    if role == "ADMIN":
        return obj

    if role == "SUPERVISOR" and obj.usuario == user:
        return obj

    if role == "REGIONAL":
        qs = get_supervisores_por_region(user)
        if not qs.filter(pk=obj.pk).exists():
            raise PermissionDenied("Sin acceso regional")
        return obj

    raise PermissionDenied("Sin permisos")


# =========================================================
# 📋 LIST
# =========================================================
@login_required
def supervisor_list(request):

    role = get_user_role(request.user)
    query = request.GET.get("q")

    if role == "SUPERVISOR":
        return redirect("supervisores2:mi")

    if role == "ADMIN":
        qs = get_supervisores_global(query=query)

    elif role == "REGIONAL":
        qs = get_supervisores_por_region(request.user, query=query)

    else:
        qs = Supervisor2.objects.none()

    return render(request, "supervisores2/supervisor_list.html", {
        "supervisores": qs,
        "query": query,
        "role": role
    })


# =========================================================
# 👤 MI SUPERVISOR
# =========================================================
@login_required
def mi_supervisor(request):

    obj = get_supervisor_by_user(request.user)

    if not obj:
        return redirect("supervisores2:create")

    return redirect("supervisores2:update", pk=obj.pk)


# =========================================================
# 🟢 CREATE
# =========================================================
@login_required
def supervisor_create(request):

    existente = get_supervisor_by_user(request.user)
    if existente:
        return redirect("supervisores2:update", pk=existente.pk)

    form = Supervisor2DynamicForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():

        crear_o_actualizar_supervisor(
            form=form,
            user=request.user
        )

        return redirect("supervisores2:list")

    return render(request, "supervisores2/supervisor_form.html", {
        "form": form,
        "title": "Alta Supervisor"
    })


# =========================================================
# ✏️ UPDATE
# =========================================================
@login_required
def supervisor_update(request, pk):

    obj = get_supervisor_or_403(request.user, pk)

    form = Supervisor2DynamicForm(
        request.POST or None,
        instance=obj,
        user=request.user
    )

    if request.method == "POST" and form.is_valid():

        crear_o_actualizar_supervisor(
            form=form,
            user=request.user,
            instance=obj
        )

        return redirect("supervisores2:list")

    return render(request, "supervisores2/supervisor_form.html", {
        "form": form,
        "object": obj,
        "title": "Editar Supervisor"
    })


# =========================================================
# 🗑 DELETE
# =========================================================
@login_required
def supervisor_delete(request, pk):

    obj = get_supervisor_or_403(request.user, pk)

    if request.method == "POST":
        obj.delete()
        return redirect("supervisores2:list")

    return render(request, "supervisores2/supervisor_confirm_delete.html", {
        "object": obj
    })


# =========================================================
# 🗺 MAPA
# =========================================================
@login_required
def mapa_supervisores(request):

    role = get_user_role(request.user)

    if role == "ADMIN":
        qs = get_supervisores_global()
    elif role == "REGIONAL":
        qs = get_supervisores_por_region(request.user)
    else:
        qs = Supervisor2.objects.filter(usuario=request.user)

    return render(request, "mapa/supervisores.html", {
        "supervisores": qs
    })


# =========================================================
# 📤 ENVIAR A REVISIÓN (CORREGIDO)
# =========================================================
@login_required
def supervisor_send_review(request, pk):

    obj = get_supervisor_or_403(request.user, pk)

    # 🔒 solo si está rechazado o pendiente
    if obj.estado_validacion == "APROBADO":
        raise PermissionDenied("Ya aprobado")

    obj.marcar_pendiente()
    obj.save()

    return redirect("supervisores2:list")


# =========================================================
# ✅ APROBAR (REGIONAL)
# =========================================================
@login_required
def supervisor_approve(request, pk):

    obj = get_supervisor_or_403(request.user, pk)

    validar_supervisor_regional(
        supervisor=obj,
        user=request.user,
        aprobar=True
    )

    return redirect("supervisores2:list")


# =========================================================
# ❌ RECHAZAR (REGIONAL)
# =========================================================
@login_required
def supervisor_reject(request, pk):

    obj = get_supervisor_or_403(request.user, pk)

    validar_supervisor_regional(
        supervisor=obj,
        user=request.user,
        aprobar=False
    )

    return redirect("supervisores2:list")