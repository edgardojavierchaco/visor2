from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Transform, Distance
from django.contrib.gis.db.models import PointField
from django.db.models import F, Func, Q
from .models_mapas import CapaEscuelas
from django.http import HttpResponse
import openpyxl


def mapa_escuelas(request):

    ofertas_raw = CapaEscuelas.objects.values_list('oferta', flat=True)

    ofertas_set = set()
    for o in ofertas_raw:
        if o:
            for item in o.split(','):
                ofertas_set.add(item.strip())

    ofertas = sorted(ofertas_set)

    sectores = sorted(set(
        s.strip() for s in
        CapaEscuelas.objects.values_list('sector', flat=True)
        if s
    ))

    ambitos = sorted(set(
        a.strip() for a in
        CapaEscuelas.objects.values_list('ambito', flat=True)
        if a
    ))

    regional = sorted(set(
        a.strip() for a in
        CapaEscuelas.objects.values_list('region_loc', flat=True)
        if a
    ))
    
    localidad = sorted(set(
        a.strip() for a in
        CapaEscuelas.objects.values_list('localidad', flat=True)
        if a
    ))
    
    palette_oferta = ["red","green","blue","orange","purple","darkred","darkgreen","darkblue","pink","cadetblue"]
    palette_sector = ["black","brown","gray","cadetblue","darkorange","darkpurple"]

    color_oferta = {o: palette_oferta[i % len(palette_oferta)] for i, o in enumerate(ofertas)}
    color_sector = {s: palette_sector[i % len(palette_sector)] for i, s in enumerate(sectores)}

    context = {
        "ofertas": ofertas,
        "sectores": sectores,
        "ambitos": ambitos,
        "color_oferta": color_oferta,
        "color_sector": color_sector,
        "regional": regional,
        "localidad": localidad        
    }

    return render(request, 'mapa/escuelas/mapa_filtros_tabla.html', context)


def escuelas_cercanas(request):
    if request.method == "POST":

        lat = float(request.POST.get("lat"))
        lon = float(request.POST.get("lon"))
        radio = float(request.POST.get("radio"))

        oferta_filter = request.POST.getlist("oferta[]")
        sector_filter = request.POST.get("sector")
        ambito_filter = request.POST.get("ambito")

        punto = Point(lon, lat, srid=4326)

        qs = CapaEscuelas.objects.annotate(
            geom_wgs=Func(
                F('long'),
                F('lat'),
                function='ST_MakePoint',
                output_field=PointField()
            )
        ).annotate(
            geom_wgs_4326=Func(
                F('geom_wgs'),
                function='ST_SetSRID',
                template="ST_SetSRID(%(expressions)s, 4326)",
                output_field=PointField(srid=4326)
            )
        ).annotate(
            geom_5347=Transform('geom_wgs_4326', 5347),
            punto_5347=Transform(punto, 5347)
        ).annotate(
            distancia=Distance('geom_5347', 'punto_5347')
        ).filter(
            distancia__lte=radio
        )

        # 🔥 MULTI OFERTA
        if oferta_filter:
            from django.db.models import Q

            query = Q()
            for o in oferta_filter:
                if o != "Todos":
                    query |= Q(oferta__icontains=o)

            qs = qs.filter(query)

        if sector_filter and sector_filter != "Todos":
            qs = qs.filter(sector=sector_filter)

        if ambito_filter and ambito_filter != "Todos":
            qs = qs.filter(ambito=ambito_filter)

        data = [
            {
                "cueanexo": e.cueanexo,
                "nom_est": e.nom_est,
                "calle": e.calle,
                "nro": e.numero,
                "localidad": e.localidad,
                "oferta": e.oferta,
                "sector": e.sector,
                "ambito": e.ambito,
                "regional": e.region_loc,
                "lat": e.lat,
                "lon": e.long,
            }
            for e in qs
        ]
        print(data)

        return JsonResponse({
            "escuelas": data,
            "count": qs.count()
        })

    return JsonResponse({"error": "Método no permitido"}, status=400)


def exportar_escuelas(request):
    cues = request.GET.getlist("cue[]")  # recibir solo los visibles

    qs = CapaEscuelas.objects.filter(cueanexo__in=cues)

    # 📊 Generar Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Escuelas visibles en el mapa"

    ws.append(["CUEANEXO", "Nombre", "Sector", "Ámbito", "Oferta"])

    for e in qs:
        ws.append([e.cueanexo, e.nom_est, e.sector, e.ambito, e.oferta,e.region_loc,e.localidad])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename=escuelas_visibles_en_mapa.xlsx'
    wb.save(response)
    return response