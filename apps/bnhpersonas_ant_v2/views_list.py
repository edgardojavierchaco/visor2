import csv
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from .domain.access import operator_required, person_scope, activity_scope, scoped_offers, is_admin, is_regional
from .models import EventoAuditoria


def filtered_activities(request):
    qs = activity_scope(request.user)
    for param, field in (("cueanexo", "cueanexo"), ("categoria", "categoria"), ("estado", "estado"), ("validacion", "validacion")):
        if request.GET.get(param):
            qs = qs.filter(**{field: request.GET[param][:100]})
    search = request.GET.get("q", "").strip()[:150]
    if search:
        for term in search.split()[:8]:
            qs = qs.filter(Q(persona__apellido__icontains=term) | Q(persona__nombre__icontains=term) | Q(persona__dni__startswith=term) | Q(persona__cuil__startswith=term))
    return qs


@method_decorator(operator_required, name="dispatch")
class PersonasListView(View):
    def get(self, request):
        activities = filtered_activities(request)
        people = person_scope(request.user)
        filters = any(request.GET.get(key) for key in ("cueanexo", "categoria", "estado", "validacion", "q"))
        if filters:
            people = people.filter(actividades__in=activities).distinct()
        people = people.annotate(total_actividades=Count("actividades", filter=Q(actividades__in=activities), distinct=True)).order_by("apellido", "nombre", "pk")
        page = Paginator(people, 25).get_page(request.GET.get("page"))
        params = request.GET.copy()
        params.pop("page", None)
        totals = activities.aggregate(cargos=Count("pk"), docentes=Count("pk", filter=Q(categoria="DOCENTE")), no_docentes=Count("pk", filter=Q(categoria="NO DOCENTE")), pendientes=Count("pk", filter=Q(validacion="BORRADOR")))
        return render(request, "bnh/personas/list.html", {"page_obj": page, "personas": page.object_list, "total_personas": page.paginator.count, "totals": totals, "query": params.urlencode(), "instituciones": scoped_offers(request.user).order_by("cueanexo_str").values("cueanexo_str", "nom_est").distinct(), "filters": request.GET})


@method_decorator(operator_required, name="dispatch")
class PersonaDetailView(View):
    def get(self, request, pk):
        person = get_object_or_404(person_scope(request.user).select_related("sexo", "provincia", "localidad", "codigo_area"), pk=pk)
        activities = activity_scope(request.user, include_deleted=True).filter(persona=person).select_related("ceic", "sit_revista", "modalidad", "niveles").order_by("eliminado", "cueanexo", "-f_desde", "pk")
        # El historial institucional tampoco revela cargos de otras escuelas.
        events = EventoAuditoria.objects.filter(entidad="registroactividades", objeto_id__in=activities.values("pk")).select_related("usuario")[:40]
        return render(request, "bnh/personas/detail.html", {"persona": person, "actividades": activities, "eventos": events, "can_observe": is_admin(request.user) or is_regional(request.user)})


class Echo:
    def write(self, value):
        return value


def csv_cell(value):
    value = str(value or "")
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


@operator_required
@require_GET
def exportar_personal(request):
    qs = filtered_activities(request).select_related("persona", "ceic").order_by("cueanexo", "persona__apellido", "pk")
    writer = csv.writer(Echo(), delimiter=";")
    def rows():
        yield "\ufeff" + writer.writerow(["CUEANEXO", "Apellido", "Nombre", "CUIL", "DNI", "Categoría", "Cargo", "Estado", "Validación"])
        for obj in qs.iterator(chunk_size=1000):
            yield writer.writerow([csv_cell(x) for x in (obj.cueanexo, obj.persona.apellido, obj.persona.nombre, obj.persona.cuil, obj.persona.dni, obj.categoria, obj.ceic, obj.estado, obj.validacion)])
    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="personal_educativo.csv"'
    response["Cache-Control"] = "private, no-store"
    return response
