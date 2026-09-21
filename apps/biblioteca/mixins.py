import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.contrib import messages
from django.core.cache import cache
from django.db.models import F, Func, Value
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from apps.consultasge.models_padron import CapaUnicaOfertas

from .models import GenerarInforme


PERIODO_ACTIVO_SESSION_KEY = "biblioteca_periodo_activo_id"
IDENTIDAD_ESTABLECIMIENTO_CACHE_TTL = 15 * 60
_IDENTIDAD_ESTABLECIMIENTO_CACHE_KEY_PREFIX = (
    "biblioteca:identidad_establecimiento:v1"
)
_IDENTIDAD_ESTABLECIMIENTO_CACHE_FIELDS = (
    "cueanexo",
    "nombre",
    "nombre_navbar",
    "titulo_hero",
)
_PERIODO_NO_RESUELTO = object()
_IDENTIDAD_NO_RESUELTA = object()


def get_cueanexos_usuario(user):
    usuario_limpio = re.sub(r"\D", "", user.username)
    return list(
        CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F("resploc_cuitcuil"),
                Value("-"),
                Value(""),
                function="REPLACE",
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta="Común - Servicios complementarios ",
            acronimo__startswith="BI",
        ).values_list("cueanexo", flat=True)
    )


def _get_cueanexos_autorizados_request(request: HttpRequest):
    cueanexos = getattr(
        request,
        "_biblioteca_cueanexos_autorizados",
        None,
    )
    if cueanexos is None:
        cueanexos = list(dict.fromkeys(
            str(valor) for valor in get_cueanexos_usuario(request.user)
        ))
        request._biblioteca_cueanexos_autorizados = cueanexos
    return cueanexos


def _identidad_establecimiento_cache_key(cueanexo):
    return f"{_IDENTIDAD_ESTABLECIMIENTO_CACHE_KEY_PREFIX}:{cueanexo}"


def _identidad_establecimiento_cache_valida(identidad, cueanexo):
    return (
        isinstance(identidad, dict)
        and str(identidad.get("cueanexo")) == cueanexo
        and all(campo in identidad for campo in _IDENTIDAD_ESTABLECIMIENTO_CACHE_FIELDS)
    )


def resolver_identidad_establecimiento(
    request: HttpRequest,
    periodo=_PERIODO_NO_RESUELTO,
):
    """Resuelve una sola vez la identidad visual BI inequívoca del request."""
    identidad_cache = getattr(
        request,
        "_biblioteca_identidad_establecimiento",
        _IDENTIDAD_NO_RESUELTA,
    )
    if identidad_cache is not _IDENTIDAD_NO_RESUELTA:
        return identidad_cache

    if periodo is _PERIODO_NO_RESUELTO:
        periodo = resolver_periodo_activo(request)

    if periodo is not None:
        cueanexo = str(periodo.cueanexo)
    else:
        cueanexos_autorizados = _get_cueanexos_autorizados_request(request)
        if len(cueanexos_autorizados) != 1:
            request._biblioteca_identidad_establecimiento = None
            return None
        cueanexo = cueanexos_autorizados[0]

    cache_key = _identidad_establecimiento_cache_key(cueanexo)
    try:
        identidad_cache = cache.get(cache_key)
        cache_hit_valido = _identidad_establecimiento_cache_valida(
            identidad_cache,
            cueanexo,
        )
    except Exception:
        cache_hit_valido = False
    if cache_hit_valido:
        request._biblioteca_identidad_establecimiento = identidad_cache
        return identidad_cache

    nombres = list(
        CapaUnicaOfertas.objects.filter(
            cueanexo=cueanexo,
            oferta="Común - Servicios complementarios ",
            acronimo__startswith="BI",
        ).values_list("nom_est", flat=True).distinct()
    )
    nombres_inequivocos = {
        nombre for nombre in nombres if nombre and nombre.strip()
    }
    if len(nombres_inequivocos) != 1:
        request._biblioteca_identidad_establecimiento = None
        return None

    nombre = nombres_inequivocos.pop()
    nombre_navbar = re.sub(
        r"^BIBLIOTECA ",
        "",
        nombre,
        count=1,
        flags=re.IGNORECASE,
    )
    identidad = {
        "cueanexo": cueanexo,
        "nombre": nombre,
        "nombre_navbar": nombre_navbar,
        "titulo_hero": (
            nombre
            if nombre_navbar != nombre
            else f"BIBLIOTECA · {nombre}"
        ),
    }
    try:
        cache.set(
            cache_key,
            identidad,
            timeout=IDENTIDAD_ESTABLECIMIENTO_CACHE_TTL,
        )
    except Exception:
        pass
    request._biblioteca_identidad_establecimiento = identidad
    return identidad


def resolver_periodo_activo(request: HttpRequest):
    """Resuelve una sola vez el GenerarInforme editable y autorizado del request."""
    periodo_cache = getattr(
        request,
        "_biblioteca_periodo_activo",
        _PERIODO_NO_RESUELTO,
    )
    if periodo_cache is not _PERIODO_NO_RESUELTO:
        return periodo_cache

    periodo_explicito = "periodo" in request.GET
    periodo_id = (
        request.GET.get("periodo")
        if periodo_explicito
        else request.session.get(PERIODO_ACTIVO_SESSION_KEY)
    )
    periodo = None

    try:
        periodo_id = int(periodo_id)
    except (TypeError, ValueError):
        periodo_id = None

    if periodo_id is not None:
        cueanexos_autorizados = _get_cueanexos_autorizados_request(request)
        try:
            periodo = (
                GenerarInforme.objects
                .only("pk", "cueanexo", "meses", "annos", "estado")
                .get(
                    pk=periodo_id,
                    estado="GENERADO",
                    cueanexo__in=cueanexos_autorizados,
                )
            )
        except GenerarInforme.DoesNotExist:
            periodo = None

        if periodo is not None and GenerarInforme.objects.filter(
            cueanexo=periodo.cueanexo,
            estado="GENERADO",
        ).exclude(pk=periodo.pk).exists():
            periodo = None

    request._biblioteca_periodo_explicito_invalido = (
        periodo_explicito and periodo is None
    )
    request._biblioteca_periodo_activo = periodo

    if periodo is None:
        if not periodo_explicito:
            request.session.pop(PERIODO_ACTIVO_SESSION_KEY, None)
            request.session.pop("cueanexo_activo", None)
        return None

    cueanexo = str(periodo.cueanexo)
    request.session[PERIODO_ACTIVO_SESSION_KEY] = periodo.pk
    request.session["cueanexo_activo"] = cueanexo
    return periodo


class PeriodoActivoMixin(View):
    request: HttpRequest

    def get_periodo_activo(self):
        return resolver_periodo_activo(self.request)

    def get_cueanexo_activo(self):
        periodo = self.get_periodo_activo()
        return str(periodo.cueanexo) if periodo else None

    def aplicar_periodo_activo(self, instance):
        periodo = self.get_periodo_activo()
        instance.cueanexo = str(periodo.cueanexo)
        instance.mes = periodo.meses
        instance.anio = periodo.annos
        return instance

    def get_periodo_url(self, url):
        periodo = self.get_periodo_activo()
        if not periodo or not url:
            return url

        partes = urlsplit(str(url))
        parametros = dict(parse_qsl(partes.query, keep_blank_values=True))
        parametros.update({
            "periodo": str(periodo.pk),
            "anio": str(periodo.annos),
            "mes": str(periodo.meses),
        })
        return urlunsplit((
            partes.scheme,
            partes.netloc,
            partes.path,
            urlencode(parametros),
            partes.fragment,
        ))

    def handle_periodo_invalido(self):
        mensaje = (
            "El período indicado no está disponible para edición."
            if getattr(self.request, "_biblioteca_periodo_explicito_invalido", False)
            else "No hay un período activo válido para esta operación."
        )
        if self.request.method == "POST":
            return JsonResponse({"error": True, "message": mensaje}, status=403)

        messages.error(self.request, mensaje)
        return redirect(reverse("bibliotecas:periodos"))

    def dispatch(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        self.request = request
        if self.get_periodo_activo() is None:
            return self.handle_periodo_invalido()

        if "pk" in kwargs:
            try:
                self.object = self.get_object()
            except Http404:
                if request.method == "POST":
                    return JsonResponse(
                        {"error": True, "message": "Registro no disponible."},
                        status=404,
                    )
                raise

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        periodo = self.get_periodo_activo()
        return super().get_queryset().filter(
            cueanexo=str(periodo.cueanexo),
            mes=periodo.meses,
            anio=periodo.annos,
        )

    def get_object(self, queryset=None):
        if hasattr(self, "_biblioteca_objeto_periodo"):
            return self._biblioteca_objeto_periodo
        objeto = super().get_object(queryset=queryset)
        self._biblioteca_objeto_periodo = objeto
        return objeto

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        periodo = self.get_periodo_activo()
        data = kwargs.get("data")
        if data is not None:
            data = data.copy()
            campos = self.get_form_class().base_fields
            valores = {
                "cueanexo": str(periodo.cueanexo),
                "mes": periodo.meses,
                "anio": periodo.annos,
            }
            for campo, valor in valores.items():
                if campo in campos:
                    data[campo] = valor
            kwargs["data"] = data
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        self.aplicar_periodo_activo(form.instance)
        return form

    def form_valid(self, form):
        self.aplicar_periodo_activo(form.instance)
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_periodo_url(super().get_success_url())

    def render_to_response(self, context, **response_kwargs):
        periodo = self.get_periodo_activo()
        context["periodo_activo"] = periodo
        context["periodo_activo_id"] = periodo.pk
        context["cueanexo"] = str(periodo.cueanexo)
        context["mes"] = periodo.meses
        context["anno"] = periodo.annos
        context["bloqueado"] = False

        for clave in (
            "create_url",
            "list_url",
            "update_url",
            "delete_url",
            "before_url",
            "next_url",
        ):
            if context.get(clave):
                context[clave] = self.get_periodo_url(context[clave])

        return super().render_to_response(context, **response_kwargs)


class InformeBloqueoMixin(PeriodoActivoMixin):
    """Compatibilidad: la edición solo existe para el período exacto GENERADO."""

    def informe_bloqueado(self) -> bool:
        return self.get_periodo_activo() is None

    def handle_bloqueo(self):
        return self.handle_periodo_invalido()
