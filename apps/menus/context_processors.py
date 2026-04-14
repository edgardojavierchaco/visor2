from .services import get_menu_for_user, find_active_path

def menu_context(request):

    if not request.user.is_authenticated:
        return {
            "menu": [],
            "breadcrumbs": []
        }

    try:
        # 🔥 NO recalcular flags
        flags = getattr(request, "flags_menu", set())

        print("\n🚀 FLAGS DESDE CONTEXT:", flags)

        menu = get_menu_for_user(request.user, request) or []
        breadcrumbs = find_active_path(menu) or []

    except Exception as e:
        print(f"❌ Error en menu_context: {e}")
        menu = []
        breadcrumbs = []

    return {
        "menu": menu,
        "breadcrumbs": breadcrumbs
    }