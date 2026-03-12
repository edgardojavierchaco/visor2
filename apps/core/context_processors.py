def user_roles(request):

    if request.user.is_authenticated:
        roles = set(request.user.groups.values_list("name", flat=True))
    else:
        roles = set()

    return {
        "USER_ROLES": roles
    }