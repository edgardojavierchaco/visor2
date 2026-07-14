from django.contrib import admin


from apps.sirtee.models.relevamientos import Relevamiento

from apps.sirtee.models.hallazgos import Hallazgo

from apps.sirtee.models.intervenciones import Intervencion



# =====================================================
# INLINE: INTERVENCIÓN
# =====================================================

class IntervencionInline(
    admin.TabularInline
):

    model = Intervencion

    extra = 0

    show_change_link = True


    fields = (

        "titulo",

        "tipo",

        "estado",

        "prioridad",

        "responsable",

        "porcentaje_avance",

        "costo_estimado",

        "costo_real",

    )


    readonly_fields = (

        "porcentaje_avance",

    )



    autocomplete_fields = (

        "tipo",

        "estado",

        "prioridad",

    )




# =====================================================
# INLINE: HALLAZGO
# =====================================================

class HallazgoInline(
    admin.TabularInline
):

    model = Hallazgo

    extra = 0

    show_change_link = True


    fields = (

        "titulo",

        "tipo_hallazgo",

        "criticidad",

        "riesgo",

        "estado",

    )


    autocomplete_fields = (

        "tipo_hallazgo",

        "criticidad",

        "riesgo",

        "estado",

    )



# =====================================================
# RELEVAMIENTO ADMIN
# =====================================================

@admin.register(Relevamiento)
class RelevamientoAdmin(
    admin.ModelAdmin
):


    list_display = (

        "id",

        "cueanexo",

        "escuela_nombre",

        "fecha",

        "estado",

        "tipo_relevamiento",

        "finalizado",

    )


    list_filter = (

        "estado",

        "tipo_relevamiento",

        "finalizado",

        "fecha",

    )


    search_fields = (

        "cueanexo",

        "observaciones",

    )


    inlines = [

        HallazgoInline

    ]



    fieldsets = (

        (
            "📍 Escuela",
            {
                "fields": (
                    "cueanexo",
                    "fecha",
                )
            }
        ),

        (
            "⚙️ Estado",
            {
                "fields": (
                    "estado",
                    "tipo_relevamiento",
                    "finalizado",
                    "fecha_finalizacion",
                )
            }
        ),

        (
            "🧾 Observaciones",
            {
                "fields": (
                    "observaciones",
                )
            }
        ),

    )


    readonly_fields = (

        "fecha_finalizacion",

    )



    def escuela_nombre(
        self,
        obj
    ):

        from apps.sirtee.data.padron import PadronEscuelas


        data = PadronEscuelas.get_by_cueanexo(
            obj.cueanexo
        )


        return data[0]["nom_est"] if data else "-"



    escuela_nombre.short_description = (
        "Escuela"
    )




# =====================================================
# HALLAZGO ADMIN
# =====================================================

@admin.register(Hallazgo)
class HallazgoAdmin(
    admin.ModelAdmin
):


    list_display = (

        "titulo",

        "relevamiento",

        "tipo_hallazgo",

        "criticidad",

        "estado",

    )



    list_filter = (

        "tipo_hallazgo",

        "criticidad",

        "riesgo",

        "estado",

        "area_afectada",

    )



    search_fields = (

        "titulo",

        "descripcion",

        "relevamiento__cueanexo",

    )



    inlines = [

        IntervencionInline

    ]



    autocomplete_fields = (

        "relevamiento",

        "sistema_constructivo",

        "area_afectada",

        "tipo_hallazgo",

        "criticidad",

        "riesgo",

        "estado",

    )



    def get_queryset(
        self,
        request
    ):

        return (

            super()

            .get_queryset(request)

            .select_related(

                "relevamiento",

                "tipo_hallazgo",

                "criticidad",

                "estado",

                "riesgo",

                "area_afectada",

            )

        )



# =====================================================
# INTERVENCIÓN ADMIN
# =====================================================

@admin.register(Intervencion)
class IntervencionAdmin(
    admin.ModelAdmin
):


    list_display = (

        "titulo",

        "hallazgo",

        "tipo",

        "estado",

        "prioridad",

        "porcentaje_avance",

        "costo_estimado",

        "costo_real",

    )


    list_filter = (

        "tipo",

        "estado",

        "prioridad",

        "organismo_responsable",

        "fuente_financiamiento",

    )


    search_fields = (

        "titulo",

        "descripcion",

        "hallazgo__titulo",

        "hallazgo__relevamiento__cueanexo",

    )


    autocomplete_fields = (

        "hallazgo",

        "tipo",

        "estado",

        "prioridad",

        "organismo_responsable",

        "fuente_financiamiento",

    )


    fieldsets = (

        (
            "📝 Información",
            {
                "fields": (
                    "hallazgo",
                    "titulo",
                    "descripcion",
                    "tipo",
                    "estado",
                    "prioridad",
                )
            }
        ),


        (
            "👷 Responsables",
            {
                "fields": (
                    "responsable",
                    "equipo_ejecutor",
                    "organismo_responsable",
                )
            }
        ),


        (
            "💰 Financiamiento",
            {
                "fields": (
                    "fuente_financiamiento",
                    "costo_estimado",
                    "costo_real",
                )
            }
        ),


        (
            "📅 Fechas y avance",
            {
                "fields": (
                    "fecha_inicio",
                    "fecha_fin",
                    "fecha_estimada_fin",
                    "porcentaje_avance",
                )
            }
        ),


        (
            "🧾 Observaciones",
            {
                "fields": (
                    "observaciones",
                )
            }
        ),

    )



    def get_queryset(
        self,
        request
    ):

        return (

            super()

            .get_queryset(request)

            .select_related(

                "hallazgo",

                "hallazgo__relevamiento",

                "tipo",

                "estado",

                "prioridad",

                "organismo_responsable",

                "fuente_financiamiento",

            )

        )