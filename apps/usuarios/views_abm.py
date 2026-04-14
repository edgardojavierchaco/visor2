# usuarios/views_abm.py

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import UsuariosVisualizador
from .forms_abm import UsuarioForm
from django.db.models import Q

# ==========
# LISTADO 
# ==========
@login_required
def usuarios_list(request):
    return render(request, "usuarios/list_abm.html", {
        "titulo": "Usuarios"
    })
    

# =================
# LISTADO CON AJAX
# ==================
@login_required
def usuarios_list_ajax(request):

    import traceback

    try:
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))

        username = request.GET.get("username", "")
        estado = request.GET.get("estado", "")

        qs = UsuariosVisualizador.objects.all()

        if username:
            qs = qs.filter(username__icontains=username)

        if estado == "activo":
            qs = qs.filter(activo=True)
        elif estado == "inactivo":
            qs = qs.filter(activo=False)

        total = qs.count()
        qs = qs[start:start + length]

        # -----------------------------
        # 🎭 ICONO POR ROL
        # -----------------------------
        def get_rol_icon(nombre):
            nombre = (nombre or "").lower()

            if "administrador" in nombre:
                return "🛡️"
            if "ministro" in nombre:
                return "🏛️"
            if "subsecret" in nombre:
                return "🏢"
            if "director general" in nombre:
                return "⭐"
            if "nivel" in nombre:
                return "🎓"
            if "supervisor" in nombre:
                return "📊"
            if "director" in nombre:
                return "📁"

            return "👤"

        data = []

        for u in qs:

            rol_nombre = ""
            nivel = ""

            if getattr(u, "perfil", None):
                rol_nombre = getattr(getattr(u.perfil, "rol", None), "nombre", "")

            if getattr(u, "nivelacceso", None):
                nivel = getattr(u.nivelacceso, "tacceso", "")

            # 🎭 Rol con icono
            icono = get_rol_icon(rol_nombre)
            rol_html = f"{icono} {rol_nombre}"

            # 🎨 Estado con badge
            estado_html = (
                '<span class="badge bg-success">Activo</span>'
                if u.activo
                else '<span class="badge bg-danger">Inactivo</span>'
            )

            data.append([
                u.username,
                rol_html,
                nivel,
                estado_html
            ])

        return JsonResponse({
            "draw": draw,
            "recordsTotal": total,
            "recordsFiltered": total,
            "data": data
        })

    except Exception:
        print(traceback.format_exc())
        return JsonResponse({
            "error": "server error",
            "data": []
        }, status=500)
        

# ==========================
# CREAR
# ==========================
@login_required
def usuario_create(request):

    form = UsuarioForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect("usuarios_list")

    return render(request, "usuarios/form_abm.html", {
        "form": form,
        "titulo": "Crear Usuario"
    })


# ==========================
# EDITAR
# ==========================
@login_required
def usuario_update(request, pk):

    user = get_object_or_404(UsuariosVisualizador, pk=pk)

    form = UsuarioForm(request.POST or None, instance=user)

    if form.is_valid():
        form.save()
        return redirect("usuarios_list")

    return render(request, "usuarios/form_abm.html", {
        "form": form,
        "titulo": "Editar Usuario"
    })


# ==========================
# BAJA LÓGICA
# ==========================
@login_required
def usuario_delete(request, pk):

    user = get_object_or_404(UsuariosVisualizador, pk=pk)

    user.activo = False
    user.save()

    return redirect("usuarios_list")