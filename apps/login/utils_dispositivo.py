import hashlib


def get_client_ip(request):

    x_forwarded = request.META.get(
        'HTTP_X_FORWARDED_FOR'
    )

    if x_forwarded:
        return x_forwarded.split(',')[0]

    return request.META.get(
        'REMOTE_ADDR'
    )


def generar_fingerprint(request):

    user_agent = request.META.get(
        'HTTP_USER_AGENT',
        ''
    )

    idioma = request.META.get(
        'HTTP_ACCEPT_LANGUAGE',
        ''
    )

    raw = f'{user_agent}|{idioma}'

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()