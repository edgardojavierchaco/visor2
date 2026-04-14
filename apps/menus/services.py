from django.core.cache import cache
from .models import MenuItem
from apps.usuarios.services import get_user_context
from django.urls import reverse, NoReverseMatch

CACHE_TTL = 60 * 5


def get_menu_cache_key(rol, categoria, flags):
    if not flags:
        flags_str = "no_flags"
    else:
        flags_str = "|".join(sorted(list(flags)))

    key = f"menu:{rol}:{categoria}:{flags_str}"

    print("🧠 CACHE KEY:", key)  # debug

    return key


REGLAS_MENU = {
    "solo_director": lambda user: (
        getattr(user.perfil.rol, "nombre", None) == "Director"
    ),
    "no_regional_total": lambda user: (
        (rol := getattr(getattr(user, "perfil", None), "rol", None)) and
        rol.nombre not in ["Regional", "Director"] and
        rol.categoria_acceso not in ["regional", "propio"]
    ),
    "no_director_total": lambda user: (
        (rol := getattr(getattr(user, "perfil", None), "rol", None)) and
        rol.nombre != "Director" and
        rol.categoria_acceso != "propio"
    ),
    "no_supervisor_total": lambda user: (
        (rol := getattr(getattr(user, "perfil", None), "rol", None)) and
        rol.nombre != "Supervisor" and
        rol.categoria_acceso != "supervisor"
    ),
    "ocultar_ministro_subsecretario": lambda user: not (
    getattr(getattr(user, "perfil", None), "rol", None) and
    getattr(user.perfil.rol, "nombre", None) in ["Ministro", "Subsecretario"]
)
    
}


def evaluar_clave(clave, user, request):
    if not clave:
        return True

    flags = getattr(request, "flags_menu", set())

    print("\n🧪 Evaluando clave:", clave)
    print("👉 Flags actuales:", flags)
    

    grupos_or = [grupo.strip() for grupo in clave.split("|")]

    for grupo in grupos_or:
        condiciones = [c.strip() for c in grupo.split("&")]
        cumple_todo = True

        for cond in condiciones:

            if cond in flags:
                continue

            if cond in REGLAS_MENU:
                if REGLAS_MENU[cond](user):
                    continue
                else:
                    cumple_todo = False
                    break

            cumple_todo = False
            break

        if cumple_todo:
            print("  ✅ RESULTADO: SE MUESTRA\n")
            return True

    print("  ❌ RESULTADO: NO SE MUESTRA\n")
    return False


def tiene_permiso(item, ctx, user, request):

    if item.roles and ctx.rol not in item.roles:
        return False

    if item.categorias and ctx.categoria not in item.categorias:
        return False

    if item.clave:
        return evaluar_clave(item.clave, user, request)

    return True


def build_menu_tree(items, ctx, user, request, parent=None):

    resultado = []

    hijos = [i for i in items if i.parent_id == (parent.id if parent else None)]

    for item in hijos:

        children = build_menu_tree(items, ctx, user, request, item)
        tiene_acceso = tiene_permiso(item, ctx, user, request)

        if not tiene_acceso and not children:
            continue

        activo = es_activo(item, request)

        if any(child.get("active") for child in children):
            activo = True

        resultado.append({
            "label": item.label,
            "icon": item.icon,
            "url": item.url if tiene_acceso else None,
            "children": children,
            "active": activo,
            "open": activo,
        })

        print(f"\n🧱 Item: {item.label}")
        print("   clave:", item.clave)

    return resultado


def get_menu_for_user(user, request):

    ctx = get_user_context(user)
    rol = ctx.rol
    categoria = ctx.categoria

    if not rol:
        return []

    flags = getattr(request, "flags_menu", set())
    cache_key = get_menu_cache_key(rol, categoria, flags)
    
    print("🧠 CACHE KEY:", cache_key)  # ✅ ACÁ

    menu = cache.get(cache_key)
    if menu:
        return menu

    items = MenuItem.objects.filter(activo=True).select_related("parent")
    menu = build_menu_tree(items, ctx, user, request)

    cache.set(cache_key, menu, CACHE_TTL)

    return menu


def es_activo(item, request):
    if not item.url:
        return False

    try:
        return request.path.startswith(reverse(item.url))
    except NoReverseMatch:
        return False


def find_active_path(menu):

    for item in menu:

        if item.get("active"):
            if item.get("children"):
                child_path = find_active_path(item["children"])
                if child_path:
                    return [item] + child_path

            return [item]

    return []
