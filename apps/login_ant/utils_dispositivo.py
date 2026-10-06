import hashlib

from django.conf import settings

from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError

from typing import Optional


def get_client_ip(request) -> Optional[str]:

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
    

def obtener_geolocalizacion(ip):

    if not ip:
        return None

    # 🔥 IPs locales o privadas → fallback seguro
    if ip.startswith(("127.", "192.168.", "10.", "172.", "::1")):
        return {
            "pais": "Local",
            "provincia": "Local",
            "ciudad": "Local",
            "lat": -27.451,
            "lon": -58.986
        }

    try:
        path = settings.GEOIP_PATH + "/GeoLite2-City.mmdb"

        with Reader(path) as geo:
            data = geo.city(ip)

            return {
                "pais": data.country.name,
                "provincia": data.subdivisions.most_specific.name,
                "ciudad": data.city.name,
                "lat": float(data.location.latitude),
                "lon": float(data.location.longitude),
            }

    except AddressNotFoundError:
        return {
            "pais": "Desconocido",
            "provincia": "Desconocido",
            "ciudad": "Desconocido",
            "lat": -27.451,
            "lon": -58.986
        }

    except Exception:
        return {
            "pais": "Error",
            "provincia": "Error",
            "ciudad": "Error",
            "lat": -27.451,
            "lon": -58.986
        }