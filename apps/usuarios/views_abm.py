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
    from django.db.models import Q

    try:
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))

        search = request.GET.get("search[value]", "").strip()
        username = request.GET.get("username", "").strip()
        estado = request.GET.get("estado", "").strip()

        # 🔢 total SIN filtros
        total = UsuariosVisualizador.objects.count()

        qs = UsuariosVisualizador.objects.select_related(
            "perfil__rol",
            "nivelacceso"
        ).all()

        # 🔍 filtro por username
        if username:
            qs = qs.filter(username__icontains=username)

        # 🎯 filtro estado
        if estado == "activo":
            qs = qs.filter(activo=True)
        elif estado == "inactivo":
            qs = qs.filter(activo=False)

        # 🔥 BUSQUEDA GLOBAL (tipo Google)
        if search:
            palabras = search.split()

            for palabra in palabras:
                qs = qs.filter(
                    Q(username__icontains=palabra) |
                    Q(apellido__icontains=palabra) |
                    Q(nombres__icontains=palabra) |
                    Q(perfil__rol__nombre__icontains=palabra) |
                    Q(nivelacceso__tacceso__icontains=palabra)
                )

        # 🔢 total filtrado
        filtered = qs.count()

        # 🔽 ORDENAMIENTO
        order_col_index = request.GET.get("order[0][column]", "0")
        order_dir = request.GET.get("order[0][dir]", "asc")

        columnas = ["id","username", "apellido", "perfil__rol__nombre", "nivelacceso__tacceso", "activo"]

        if order_col_index.isdigit():
            col = columnas[int(order_col_index)]
            if order_dir == "desc":
                col = "-" + col
            qs = qs.order_by(col)

        # 📄 paginado
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
            if "aplicador" in nombre:
                return "📝"

            return "👤"

        data = []

        for u in qs:

            rol_nombre = ""
            nivel = ""

            try:
                rol_nombre = u.perfil.rol.nombre
            except UsuariosVisualizador.perfil.RelatedObjectDoesNotExist:
                rol_nombre = ""

            if u.nivelacceso:
                nivel = str(u.nivelacceso)

            icono = get_rol_icon(rol_nombre)
            rol_html = f"{icono} {rol_nombre}"

            estado_html = (
                '<span class="badge bg-success">Activo</span>'
                if u.activo
                else '<span class="badge bg-danger">Inactivo</span>'
            )
            
            acciones = f"""
                <button onclick="editar({u.pk})" class="btn btn-sm btn-warning me-1">✏️</button>
                <button onclick="eliminar({u.pk}, this)" 
                        class="btn btn-sm btn-danger"
                        {'disabled' if not u.activo else ''}>
                    🗑️
                </button>
                """
                
            apellido = getattr(u, "apellido", "") or ""
            nombres = getattr(u, "nombres", "") or ""
            nombre_completo = f"{apellido} {nombres}".strip()

            data.append([
                u.pk,
                u.username,
                nombre_completo,
                rol_html,
                nivel,
                estado_html,
                acciones
            ])

        return JsonResponse({
            "draw": draw,
            "recordsTotal": total,
            "recordsFiltered": filtered,
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
        return redirect("usuarios:usuarios_list")

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
    user.is_staff = False   # 🔥 clave que pediste
    user.save()

    return JsonResponse({"ok": True})