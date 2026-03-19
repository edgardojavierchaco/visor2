from .services import get_user_data
import copy

# Menú extra para Directores
menu_extra = [
    {
        "label": "Establecimiento",
        "icon": "fas fa-globe text-primary",
        "children": [
            {"label": "Matrícula", "url": "directores:matricula", "icon": "far fa-circle", "children": []},
        ]
    },
    {
        "label": "Fluidez",
        "icon": "fas fa-archive text-dark",
        "children": [
            {
                "label": "Resultados",
                "icon": "far fa-circle",
                "children": [
                    {"label": "Mayo 2024", "url": "lectocomprension:resultados", "icon": "far fa-dot-circle", "children": []},
                    {"label": "Noviembre 2024", "icon": "far fa-dot-circle", "children": [
                        {"label": "Listado", "url": "oplectura:evaluacion_directores", "icon": "far fa-circle", "children": []},
                        {"label": "Gráfico", "url": "oplectura:resultados", "icon": "far fa-circle", "children": []},
                    ]},
                    {"label": "Noviembre 2025", "url": "evaluaciones_educativas:analisis_evaluacion", "icon": "far fa-dot-circle", "children": []},
                ]
            }
        ]
    },
    {
        "label": "Relevamiento",
        "icon": "fas fa-file text-violet",
        "children": [
            {"label": "ABM Alumnos Pueblos Originarios", "url": "intercultural:dashboard_comun", "icon": "far fa-circle", "children": []},
            {"label": "Bibliotecas", "url": "bibliotecas:dashboard", "icon": "far fa-circle", "children": []},
        ]
    }
]

def user_menu(request):
    if not request.user.is_authenticated:
        return {"menu": []}

    data = get_user_data(request.user)
    rol = data.get("rol")

    menu = []

    if rol in ('Administrador', 'Gestor'):
        menu = [{"label": "Inicio", "icon": "fas fa-home", "url": "archivos:portada_gestor", "children": []}]

    elif rol == 'Director':
        director_menu = copy.deepcopy(menu_extra)

        # Filtrar Bibliotecas según cueanexo
        for sec in director_menu:
            if sec['label'] == 'Relevamiento':
                sec['children'] = [
                    item for item in sec['children']
                    if item['label'] != 'Bibliotecas' or request.user.tiene_biblioteca()
                ]

        menu = [{"label": "Inicio", "icon": "fas fa-home", "url": "directores:institucional", "children": []}] + director_menu

    return {"menu": menu, "user_rol": rol}

def menu_context(request):
    return user_menu(request)