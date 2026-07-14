from apps.sirtee.catalogos.models import (
    SistemaConstructivo,
    AreaAfectada,
    TipoHallazgo,
    Criticidad,
    Riesgo,
    EstadoHallazgo,
    TipoIntervencion,
    EstadoIntervencion,
    Prioridad,
    FuenteFinanciamiento,
    OrganismoResponsable,
)

from apps.sirtee.models.empresas import Empresa


def cargar_catalogos_10_2a():

    # =====================================
    # SISTEMAS CONSTRUCTIVOS
    # =====================================

    sistemas = [

        ("ESTRUCTURA","Estructura"),

        ("CUBIERTA","Cubierta"),

        ("MAMPOSTERIA","Mampostería"),

        ("PISOS","Pisos"),

        ("REVESTIMIENTOS","Revestimientos"),

        ("CIELORRASOS","Cielorrasos"),

        ("CARPINTERIAS","Carpinterías"),

        ("INST_ELECTRICA","Instalación eléctrica"),

        ("INST_SANITARIA","Instalación sanitaria"),

        ("INST_GAS","Instalación de gas"),

        ("INCENDIOS","Sistema contra incendios"),

        ("CLIMATIZACION","Climatización"),

        ("ACCESIBILIDAD","Accesibilidad"),

        ("MOBILIARIO","Mobiliario"),

        ("ESP_EXTERIORES","Espacios exteriores"),

        ("OTRO","Otro"),
    ]

    for i, dato in enumerate(sistemas, 1):

        SistemaConstructivo.objects.get_or_create(

            codigo=dato[0],

            defaults=dict(

                nombre=dato[1],

                orden=i,

            )

        )

    # =====================================
    # AREAS AFECTADAS
    # =====================================

    areas = [

        ("AULAS","Aulas"),

        ("LABORATORIO","Laboratorio"),

        ("BIBLIOTECA","Biblioteca"),

        ("SUM","SUM"),

        ("DIRECCION","Dirección"),

        ("SECRETARIA","Secretaría"),

        ("SALA_DOCENTES","Sala de docentes"),

        ("SALA_INFORMATICA","Sala informática"),

        ("COMEDOR","Comedor"),

        ("COCINA","Cocina"),

        ("DEPOSITO","Depósito"),

        ("SANITARIOS_ALUMNOS","Sanitarios alumnos"),

        ("SANITARIOS_DOCENTES","Sanitarios docentes"),

        ("SANITARIO_ACCESIBLE","Sanitario accesible"),

        ("PATIO","Patio"),

        ("PLAYON","Playón deportivo"),

        ("GIMNASIO","Gimnasio"),

        ("ESCALERAS","Escaleras"),

        ("RAMPAS","Rampas"),

        ("GALERIAS","Galerías"),

        ("CUBIERTA","Cubierta"),

        ("TANQUE","Tanque"),

        ("SALA_MAQUINAS","Sala de máquinas"),

        ("CERCO","Cerco perimetral"),

        ("ACCESO","Acceso principal"),

        ("ESTACIONAMIENTO","Estacionamiento"),

        ("ESPACIOS_VERDES","Espacios verdes"),

        ("OTRO","Otro"),
    ]

    for i, dato in enumerate(areas, 1):

        AreaAfectada.objects.get_or_create(

            codigo=dato[0],

            defaults=dict(

                nombre=dato[1],

                orden=i,

            )

        )

    # =====================================
    # TIPOS DE HALLAZGO
    # =====================================

    hallazgos = [

        ("FISURA","Fisura"),

        ("GRIETA","Grieta"),

        ("HUMEDAD","Humedad"),

        ("FILTRACION","Filtración"),

        ("CORROSION","Corrosión"),

        ("ROTURA","Rotura"),

        ("DESPRENDIMIENTO","Desprendimiento"),

        ("ASENTAMIENTO","Asentamiento"),

        ("FALLA_ELECTRICA","Falla eléctrica"),

        ("FUGA_GAS","Fuga de gas"),

        ("PERDIDA_AGUA","Pérdida de agua"),

        ("OBSTRUCCION","Obstrucción"),

        ("RIESGO_ESTRUCTURAL","Riesgo estructural"),

        ("RIESGO_ELECTRICO","Riesgo eléctrico"),

        ("RIESGO_SANITARIO","Riesgo sanitario"),

        ("RIESGO_INCENDIO","Riesgo de incendio"),

        ("FALTA_MANTENIMIENTO","Falta de mantenimiento"),

        ("OBSOLESCENCIA","Obsolescencia"),

        ("INCUMPLIMIENTO_NORMA","Incumplimiento normativo"),

        ("OTRO","Otro"),
    ]

    for i, dato in enumerate(hallazgos, 1):

        TipoHallazgo.objects.get_or_create(

            codigo=dato[0],

            defaults=dict(

                nombre=dato[1],

                orden=i,

            )

        )

    print("Catálogos técnicos 10.2A cargados.")
    
    # ======================================================
    # CRITICIDAD
    # ======================================================

    criticidades = [

        ("CRITICA","Crítica","danger",4),

        ("ALTA","Alta","warning",3),

        ("MEDIA","Media","info",2),

        ("BAJA","Baja","success",1),

    ]

    for i,c in enumerate(criticidades,1):

        Criticidad.objects.get_or_create(

            codigo=c[0],

            defaults=dict(

                nombre=c[1],

                color=c[2],

                nivel=c[3],

                orden=i,

            )

        )

    # ======================================================
    # RIESGOS
    # ======================================================

    riesgos = [

        ("COLAPSO","Colapso estructural"),

        ("INCENDIO","Incendio"),

        ("ELECTRICO","Choque eléctrico"),

        ("GAS","Explosión por gas"),

        ("INUNDACION","Inundación"),

        ("CAIDA","Caída de personas"),

        ("DESPRENDIMIENTO","Desprendimiento"),

        ("BIOLOGICO","Riesgo biológico"),

        ("SANITARIO","Riesgo sanitario"),

        ("AMBIENTAL","Riesgo ambiental"),

        ("VANDALISMO","Vandalismo"),

        ("SEGURIDAD","Seguridad física"),

        ("OPERATIVO","Riesgo operativo"),

        ("NINGUNO","Sin riesgo"),

    ]

    for i,r in enumerate(riesgos,1):

        Riesgo.objects.get_or_create(

            codigo=r[0],

            defaults=dict(

                nombre=r[1],

                orden=i,

            )

        )

    # ======================================================
    # ESTADOS DEL HALLAZGO
    # ======================================================

    estados = [

        ("ABIERTO","Abierto","danger",False),

        ("VALIDADO","Validado","warning",False),

        ("PLANIFICADO","Planificado","primary",False),

        ("EN_EJECUCION","En ejecución","info",False),

        ("RESUELTO","Resuelto","success",True),

        ("DESCARTADO","Descartado","secondary",True),

    ]

    for i,e in enumerate(estados,1):

        EstadoHallazgo.objects.get_or_create(

            codigo=e[0],

            defaults=dict(

                nombre=e[1],

                color=e[2],

                cerrado=e[3],

                orden=i,

            )

        )

    # ======================================================
    # TIPOS DE INTERVENCIÓN
    # ======================================================
    tipos = [

    ("REPARACION","Reparación"),

    ("REEMPLAZO","Reemplazo"),

    ("MANTENIMIENTO","Mantenimiento preventivo"),

    ("CORRECTIVO","Mantenimiento correctivo"),

    ("CONSTRUCCION","Construcción"),

    ("AMPLIACION","Ampliación"),

    ("REFUNCIONALIZACION","Refuncionalización"),

    ("INSTALACION","Instalación"),

    ("ADECUACION","Adecuación normativa"),

    ("LIMPIEZA","Limpieza especializada"),

    ("ADMINISTRATIVA","Gestión administrativa"),

    ("COMPRA","Adquisición"),

    ("OTRA","Otra"),

    ]

    for i,x in enumerate(tipos,1):

        TipoIntervencion.objects.get_or_create(

            codigo=x[0],

            defaults=dict(

                nombre=x[1],

                orden=i,

            )

        )

    # ======================================================
    # ESTADOS
    # ======================================================
    estados = [

    ("PENDIENTE","Pendiente","secondary",False),

    ("PROGRAMADA","Programada","primary",False),

    ("EN_EJECUCION","En ejecución","warning",False),

    ("PAUSADA","Pausada","info",False),

    ("FINALIZADA","Finalizada","success",True),

    ("CANCELADA","Cancelada","danger",True),

    ]

    for i,x in enumerate(estados,1):

        EstadoIntervencion.objects.get_or_create(

            codigo=x[0],

            defaults=dict(

                nombre=x[1],

                color=x[2],

                finaliza=x[3],

                orden=i,

            )

        )


    # ======================================================
    # PRIORIDADES
    # ======================================================
    prioridades = [

    ("MUY_ALTA","Muy alta","danger",5),

    ("ALTA","Alta","warning",4),

    ("MEDIA","Media","info",3),

    ("BAJA","Baja","success",2),

    ("MUY_BAJA","Muy baja","secondary",1),

    ]

    for i,x in enumerate(prioridades,1):

        Prioridad.objects.get_or_create(

            codigo=x[0],

            defaults=dict(

                nombre=x[1],

                color=x[2],

                nivel=x[3],

                orden=i,

            )

        )


    # ======================================================
    # FUENTES DE FINANCIAMIENTO
    # ======================================================
    fuentes = [

    ("PROVINCIA","Gobierno Provincial"),

    ("NACION","Gobierno Nacional"),

    ("MUNICIPIO","Municipio"),

    ("FONID","Fondos Educativos"),

    ("INFRAESCOLAR","Programa Infraestructura Escolar"),

    ("BID","Banco Interamericano de Desarrollo"),

    ("CAF","Banco de Desarrollo de América Latina"),

    ("PRIVADO","Financiamiento privado"),

    ("COOPERADORA","Cooperadora escolar"),

    ("DONACION","Donación"),

    ("OTRO","Otro"),

    ]

    for i,x in enumerate(fuentes,1):

        FuenteFinanciamiento.objects.get_or_create(

            codigo=x[0],

            defaults=dict(

                nombre=x[1],

                orden=i,

            )

        )


    # ======================================================
    # ORGANISMOS RESPONSABLES
    # ======================================================
    organismos = [

    ("MECCYT","Ministerio de Educación"),

    ("INFRAESTRUCTURA","Subsecretaría de Infraestructura Escolar"),

    ("MUNICIPIO","Municipio"),

    ("OBRAS_PUBLICAS","Ministerio de Obras Públicas"),

    ("EMPRESA","Empresa contratista"),

    ("COOPERADORA","Cooperadora"),

    ("DIRECTIVO","Equipo directivo"),

    ("REGIONAL","Dirección Regional"),

    ("SUPERVISION","Supervisión Técnica"),

    ("OTRO","Otro"),

    ]

    for i,x in enumerate(organismos,1):

        OrganismoResponsable.objects.get_or_create(

            codigo=x[0],

            defaults=dict(

                nombre=x[1],

                orden=i,

            )

        )
    
# ======================================================
# EMPRESAS
# ======================================================

def cargar_empresas():

    empresas = [

        (
            "Constructora Demo S.A.",
            "Constructora Demo",
            "30-00000000-0",
            "CONSTRUCTORA",
            "Resistencia",
        ),

        (
            "Servicios Infraestructura Norte",
            "Servicios Norte",
            None,
            "SERVICIOS",
            "Resistencia",
        ),

    ]


    for e in empresas:


        Empresa.objects.get_or_create(

            razon_social=e[0],

            defaults={

                "nombre_fantasia": e[1],

                "cuit": e[2],

                "tipo": e[3],

                "localidad": e[4],

            }

        )


    print(
        "Empresas SIRTEE cargadas."
    )