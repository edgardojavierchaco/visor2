from apps.usuarios.menu import get_menu

def menu_context(request):
    if request.user.is_authenticated:
        return {
            'menu': get_menu(request.user)
        }
    return {}

def user_roles(request):

    if request.user.is_authenticated:
        roles = set(request.user.groups.values_list("name", flat=True))
    else:
        roles = set()

    return {
        "USER_ROLES": roles
    }