from .domain.access import get_user_cueanexos, scoped_offers

def get_ofertas_usuario(user):
    return scoped_offers(user)
