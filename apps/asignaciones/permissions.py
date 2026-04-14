def es_supervisor(user):
    return hasattr(user, "supervisores")


def es_regional(user):
    return user.groups.filter(name="REGIONAL").exists()