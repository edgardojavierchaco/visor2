# -*- coding: utf-8 -*-

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Prefetch, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET

from .forms import (
    CefInventarioMaterialEstadoForm,
    CefInventarioMaterialForm,
    CefInventarioMaterialObservacionesForm,
)
from .models import (
    CefEstadoMaterialTipo,
    CefInventarioMaterial,
    CefInventarioMaterialEstado,
)
from .permisos import cef_required
from .performance import perf_render, perf_start_view
from .views_contexto import (
    contexto_base,
    redirect_con_contexto,
    render_fragmento_cef,
    resolver_contexto_operativo,
)


MENSAJE_CATALOGO_VACIO = (
    "Falta cargar el catálogo de estados de materiales. "
    "No se pueden crear materiales ni distribuciones hasta completarlo."
)
MENSAJE_ESTADO_DUPLICADO = (
    "Ese estado ya está cargado para el material. Editá su cantidad."
)
MENSAJE_MATERIAL_DUPLICADO = (
    "Este material ya existe. Gestioná sus estados desde el desplegable del listado."
)


def _inventario_base_queryset(cef_context):
    return CefInventarioMaterial.objects.filter(
        cueanexo=cef_context["cueanexo"],
        ciclo=cef_context["ciclo"],
    )


def _inventario_queryset(cef_context):
    estados = (
        CefInventarioMaterialEstado.objects.filter(estado__isnull=False)
        .select_related("estado")
        .order_by(
            "estado__orden",
            "estado__codigo",
            "estado__nombre",
            "pk",
        )
    )
    return (
        _inventario_base_queryset(cef_context)
        .select_related("material")
        .annotate(
            total_distribuciones=Sum(
                "distribuciones_estado__cantidad",
                filter=Q(distribuciones_estado__estado__isnull=False),
            )
        )
        .prefetch_related(
            Prefetch(
                "distribuciones_estado",
                queryset=estados,
                to_attr="estados_prefetched",
            )
        )
        .order_by("material__orden", "material__nombre")
    )


def _id_entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise Http404("Objeto de inventario no válido.")


def _item_seguro(item_id, cef_context, bloquear=False):
    queryset = _inventario_base_queryset(cef_context).select_related("material")
    if bloquear:
        queryset = queryset.select_for_update()
    return get_object_or_404(queryset, pk=_id_entero(item_id))


def _estado_seguro(estado_id, item, bloquear=False):
    queryset = CefInventarioMaterialEstado.objects.filter(
        inventario_material=item,
    )
    if bloquear:
        queryset = queryset.select_for_update()
    else:
        queryset = queryset.select_related("estado")
    return get_object_or_404(queryset, pk=_id_entero(estado_id))


def _preparar_inventario(
    inventario,
    estados_catalogo,
    observaciones_form_activo=None,
):
    for item in inventario:
        item.tiene_distribuciones = bool(item.estados_prefetched)
        item.cantidad_visible = item.total_distribuciones or 0

        estados_usados = {
            distribucion.estado_id
            for distribucion in item.estados_prefetched
        }
        item.estados_disponibles = [
            estado
            for estado in estados_catalogo
            if estado.pk not in estados_usados
        ]
        item.todos_estados_cargados = not item.estados_disponibles

        material_nombre = (
            item.material.nombre
            if item.material_id
            else item.material_nombre_snapshot
        )
        textos_busqueda = [material_nombre, item.observaciones]
        for distribucion in item.estados_prefetched:
            textos_busqueda.append(distribucion.estado.nombre)
        item.texto_busqueda = " ".join(
            str(texto or "") for texto in textos_busqueda
        ).lower()

        if (
            observaciones_form_activo is not None
            and observaciones_form_activo.instance.pk == item.pk
        ):
            item.observaciones_form = observaciones_form_activo
        else:
            item.observaciones_form = CefInventarioMaterialObservacionesForm(
                instance=item,
                prefix=f"observaciones-{item.pk}",
            )

    return inventario


def _sincronizar_campos_heredados(item, user):
    """Mantiene los campos anteriores solo para consumidores aún no adaptados."""
    resumen = CefInventarioMaterialEstado.objects.filter(
        inventario_material=item,
        estado__isnull=False,
    ).aggregate(
        cantidad_total=Sum("cantidad"),
        total_estados=Count("pk"),
        estado_unico=Max("estado__nombre"),
    )
    estado_unico = (
        resumen["estado_unico"]
        if resumen["total_estados"] == 1
        else ""
    )
    CefInventarioMaterial.objects.filter(pk=item.pk).update(
        cantidad=resumen["cantidad_total"] or 0,
        estado_descripcion=estado_unico,
        actualizado_por=user,
        actualizado_en=timezone.now(),
    )


def _agregar_errores_validacion(form, error):
    if hasattr(error, "message_dict"):
        for campo, errores in error.message_dict.items():
            destino = campo if campo in form.fields else None
            for mensaje in errores:
                form.add_error(destino, mensaje)
        return

    for mensaje in getattr(error, "messages", [str(error)]):
        form.add_error(None, mensaje)


def _redirect_detalle(cef_context, item_id):
    destino = redirect_con_contexto("cef:carga_inventario", cef_context)
    separador = "&" if "?" in destino else "?"
    return f"{destino}{separador}detalle={item_id}"


def _inventario_listado_context(
    cef_context,
    estados_catalogo,
    observaciones_form=None,
    detalle_item=None,
    estado_form=None,
    estado_edicion=None,
    mostrar_form_estado=False,
    inventario_mensaje="",
):
    inventario = (
        _preparar_inventario(
            list(_inventario_queryset(cef_context)),
            estados_catalogo,
            observaciones_form,
        )
        if cef_context["puede_operar"]
        else []
    )
    return {
        "inventario": inventario,
        "detalle_item": detalle_item,
        "estado_form": estado_form,
        "estado_edicion": estado_edicion,
        "mostrar_form_estado": mostrar_form_estado,
        "catalogo_estados_disponible": bool(estados_catalogo),
        "inventario_mensaje": inventario_mensaje,
    }


def _inventario_detalle_get_context(request, cef_context, estados_catalogo):
    context = {
        "detalle_item": None,
        "estado_form": None,
        "estado_edicion": None,
        "mostrar_form_estado": False,
        "inventario_mensaje": "",
    }
    if not cef_context["puede_operar"] or not request.GET.get("detalle"):
        return context

    detalle_item = _item_seguro(request.GET.get("detalle"), cef_context)
    context["detalle_item"] = detalle_item
    estado_accion = request.GET.get("estado_accion")
    if estado_accion not in {"agregar", "editar"}:
        return context
    if not estados_catalogo:
        context["inventario_mensaje"] = MENSAJE_CATALOGO_VACIO
        return context

    if estado_accion == "editar":
        estado_edicion = _estado_seguro(
            request.GET.get("estado_id"),
            detalle_item,
        )
        context.update(
            {
                "estado_edicion": estado_edicion,
                "estado_form": CefInventarioMaterialEstadoForm(
                    instance=estado_edicion,
                    inventario_material=detalle_item,
                ),
                "mostrar_form_estado": True,
            }
        )
        return context

    estado_form = CefInventarioMaterialEstadoForm(
        inventario_material=detalle_item,
    )
    if estado_form.fields["estado"].queryset.exists():
        context.update(
            {
                "estado_form": estado_form,
                "mostrar_form_estado": True,
            }
        )
    else:
        context["inventario_mensaje"] = (
            "El material ya tiene cargados todos los estados disponibles."
        )
    return context


@cef_required
def carga_inventario(request, item_id=None):
    context = contexto_base(request, "inventario", "Inventario CEF")
    perf_start_view(request)
    cef_context = context["cef_context"]
    puede_operar = cef_context["puede_operar"]

    if item_id:
        item_anterior = _item_seguro(item_id, cef_context)
        if request.method != "GET":
            raise Http404("La edición del material ya no está disponible.")
        return redirect(_redirect_detalle(cef_context, item_anterior.pk))

    estados_catalogo = (
        list(
            CefEstadoMaterialTipo.objects.filter(activo=True).order_by(
                "orden",
                "codigo",
                "nombre",
            )
        )
        if puede_operar
        else []
    )
    catalogo_estados_disponible = bool(estados_catalogo)

    form = None
    estado_inicial_form = None
    estado_form = None
    observaciones_form = None
    detalle_item = None
    estado_edicion = None
    mostrar_form = False
    mostrar_form_estado = False

    if request.method == "POST":
        if not puede_operar:
            raise Http404("No hay un contexto operativo habilitado.")

        accion = request.POST.get("accion")

        if accion == "guardar_material":
            mostrar_form = True
            form = CefInventarioMaterialForm(request.POST)
            form.instance.cueanexo = cef_context["cueanexo"]
            form.instance.ciclo = cef_context["ciclo"]
            estado_inicial_form = CefInventarioMaterialEstadoForm(
                request.POST,
                prefix="estado",
            )

            formularios_validos = form.is_valid()
            formularios_validos = (
                estado_inicial_form.is_valid() and formularios_validos
            )
            if not catalogo_estados_disponible:
                estado_inicial_form.add_error(None, MENSAJE_CATALOGO_VACIO)
                formularios_validos = False

            if formularios_validos:
                material = form.cleaned_data["material"]
                if _inventario_base_queryset(cef_context).filter(
                    material=material,
                ).exists():
                    form.add_error("material", MENSAJE_MATERIAL_DUPLICADO)
                    messages.error(request, MENSAJE_MATERIAL_DUPLICADO)
                else:
                    formulario_error = form
                    try:
                        with transaction.atomic():
                            item = form.save(commit=False)
                            item.cueanexo = cef_context["cueanexo"]
                            item.ciclo = cef_context["ciclo"]
                            item.cantidad = 0
                            item.estado_descripcion = ""
                            item.creado_por = request.user
                            item.actualizado_por = request.user
                            item.save(validar=False)

                            formulario_error = estado_inicial_form
                            estado = estado_inicial_form.save(commit=False)
                            estado.inventario_material = item
                            estado.creado_por = request.user
                            estado.actualizado_por = request.user
                            estado.save(
                                validar=False,
                                sincronizar_estado=False,
                            )
                            _sincronizar_campos_heredados(item, request.user)
                    except ValidationError as error:
                        _agregar_errores_validacion(formulario_error, error)
                        messages.error(
                            request,
                            "Revisá los datos antes de guardar el material.",
                        )
                    except IntegrityError:
                        form.add_error("material", MENSAJE_MATERIAL_DUPLICADO)
                        messages.error(request, MENSAJE_MATERIAL_DUPLICADO)
                    else:
                        messages.success(
                            request,
                            "Material de inventario guardado correctamente.",
                        )
                        return redirect(_redirect_detalle(cef_context, item.pk))
            else:
                messages.error(
                    request,
                    "Revisá los datos antes de guardar el material.",
                )

        elif accion == "guardar_observaciones":
            detalle_item_id = _id_entero(request.POST.get("item_id"))
            prefijo = f"observaciones-{detalle_item_id}"
            guardado = False
            try:
                with transaction.atomic():
                    item_bloqueado = _item_seguro(
                        detalle_item_id,
                        cef_context,
                        bloquear=True,
                    )
                    detalle_item = item_bloqueado
                    observaciones_form = CefInventarioMaterialObservacionesForm(
                        request.POST,
                        instance=item_bloqueado,
                        prefix=prefijo,
                    )
                    if observaciones_form.is_valid():
                        item = observaciones_form.save(commit=False)
                        item.actualizado_por = request.user
                        item.save(
                            update_fields=[
                                "observaciones",
                                "actualizado_por",
                                "actualizado_en",
                            ],
                            validar=False,
                            actualizar_snapshot=False,
                        )
                        guardado = True
            except ValidationError as error:
                _agregar_errores_validacion(observaciones_form, error)

            if guardado:
                messages.success(
                    request,
                    "Observaciones generales guardadas correctamente.",
                )
                return redirect(_redirect_detalle(cef_context, detalle_item.pk))

            messages.error(
                request,
                "Revisá las observaciones antes de guardar.",
            )

        elif accion == "guardar_estado":
            detalle_item_id = _id_entero(request.POST.get("item_id"))
            estado_id = request.POST.get("estado_id")
            mostrar_form_estado = True

            guardado = False
            if not catalogo_estados_disponible:
                detalle_item = _item_seguro(detalle_item_id, cef_context)
                estado_edicion = (
                    _estado_seguro(estado_id, detalle_item) if estado_id else None
                )
                estado_form = CefInventarioMaterialEstadoForm(
                    request.POST,
                    instance=estado_edicion,
                    inventario_material=detalle_item,
                )
                estado_form.is_valid()
                estado_form.add_error(None, MENSAJE_CATALOGO_VACIO)
            else:
                try:
                    with transaction.atomic():
                        item_bloqueado = _item_seguro(
                            detalle_item_id,
                            cef_context,
                            bloquear=True,
                        )
                        instancia_estado = (
                            _estado_seguro(
                                estado_id,
                                item_bloqueado,
                                bloquear=True,
                            )
                            if estado_id
                            else None
                        )
                        detalle_item = item_bloqueado
                        estado_edicion = instancia_estado

                        estado_form = CefInventarioMaterialEstadoForm(
                            request.POST,
                            instance=instancia_estado,
                            inventario_material=item_bloqueado,
                        )

                        if estado_form.is_valid():
                            estado = estado_form.save(commit=False)
                            estado.inventario_material = item_bloqueado
                            if not estado.pk:
                                estado.creado_por = request.user
                            estado.actualizado_por = request.user
                            estado.save(
                                validar=False,
                                sincronizar_estado=False,
                            )
                            _sincronizar_campos_heredados(
                                item_bloqueado,
                                request.user,
                            )
                            guardado = True
                except ValidationError as error:
                    _agregar_errores_validacion(estado_form, error)
                except IntegrityError:
                    estado_form.add_error(
                        "estado",
                        MENSAJE_ESTADO_DUPLICADO,
                    )

            if guardado:
                messages.success(
                    request,
                    "Estado del material guardado correctamente.",
                )
                return redirect(
                    _redirect_detalle(cef_context, detalle_item.pk)
                )

            messages.error(
                request,
                "Revisá los datos del estado antes de guardar.",
            )

        elif accion == "eliminar_estado":
            detalle_item_id = _id_entero(request.POST.get("item_id"))
            estado_id = request.POST.get("estado_id")
            with transaction.atomic():
                item_bloqueado = _item_seguro(
                    detalle_item_id,
                    cef_context,
                    bloquear=True,
                )
                estado = _estado_seguro(
                    estado_id,
                    item_bloqueado,
                    bloquear=True,
                )
                estado.delete()
                _sincronizar_campos_heredados(item_bloqueado, request.user)
            messages.success(
                request,
                "Estado del material eliminado correctamente.",
            )
            return redirect(_redirect_detalle(cef_context, detalle_item_id))

        elif accion == "eliminar_material":
            detalle_item = _item_seguro(request.POST.get("item_id"), cef_context)
            with transaction.atomic():
                item_bloqueado = _item_seguro(
                    detalle_item.pk,
                    cef_context,
                    bloquear=True,
                )
                material_nombre = (
                    item_bloqueado.material.nombre
                    if item_bloqueado.material_id
                    else item_bloqueado.material_nombre_snapshot
                )
                item_bloqueado.delete()
            messages.success(
                request,
                f'El material "{material_nombre}" fue eliminado correctamente.',
            )
            return redirect(
                redirect_con_contexto("cef:carga_inventario", cef_context)
            )

        else:
            raise Http404("Acción de inventario no válida.")

    elif puede_operar:
        mostrar_form = request.GET.get("accion") == "agregar"
        if mostrar_form:
            form = CefInventarioMaterialForm()
            estado_inicial_form = CefInventarioMaterialEstadoForm(prefix="estado")
            if not catalogo_estados_disponible:
                estado_inicial_form.add_error(None, MENSAJE_CATALOGO_VACIO)
        detalle_context = _inventario_detalle_get_context(
            request,
            cef_context,
            estados_catalogo,
        )
        detalle_item = detalle_context["detalle_item"]
        estado_form = detalle_context["estado_form"]
        estado_edicion = detalle_context["estado_edicion"]
        mostrar_form_estado = detalle_context["mostrar_form_estado"]

    inventario_mensaje = (
        detalle_context["inventario_mensaje"]
        if request.method == "GET" and puede_operar
        else ""
    )
    context.update(
        _inventario_listado_context(
            cef_context,
            estados_catalogo,
            observaciones_form=observaciones_form,
            detalle_item=detalle_item,
            estado_form=estado_form,
            estado_edicion=estado_edicion,
            mostrar_form_estado=mostrar_form_estado,
            inventario_mensaje=inventario_mensaje,
        )
    )

    context.update(
        {
            "form": form,
            "estado_inicial_form": estado_inicial_form,
            "estado_form": estado_form,
            "mostrar_form": mostrar_form,
            "catalogo_estados_disponible": catalogo_estados_disponible,
            "mensaje_catalogo_vacio": MENSAJE_CATALOGO_VACIO,
        }
    )
    return perf_render(request, "cef/inventario_cef.html", context)


@cef_required
@require_GET
def inventario_fragmento(request):
    cef_context = resolver_contexto_operativo(request)
    estados_catalogo = (
        list(
            CefEstadoMaterialTipo.objects.filter(activo=True).order_by(
                "orden",
                "codigo",
                "nombre",
            )
        )
        if cef_context["puede_operar"]
        else []
    )
    detalle_context = _inventario_detalle_get_context(
        request,
        cef_context,
        estados_catalogo,
    )
    context = {
        "cef_context": cef_context,
        "cef_partial": True,
        "catalogo_estados_disponible": bool(estados_catalogo),
        "mensaje_catalogo_vacio": MENSAJE_CATALOGO_VACIO,
    }
    context.update(
        _inventario_listado_context(
            cef_context,
            estados_catalogo,
            **detalle_context,
        )
    )
    return render_fragmento_cef(request, "cef/inventario_seccion_cef.html", context)
