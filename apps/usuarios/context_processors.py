from .services import get_user_context
import copy


# Menú extra para Directores
MENU_DIRECTOR = [
    {
        "label": "Establecimiento",
        "icon": "fas fa-globe text-primary",
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
                    {
                        "label": "Noviembre 2024",
                        "icon": "far fa-dot-circle",
                        "children": [
                            {"label": "Listado", "url": "oplectura:evaluacion_directores", "icon": "far fa-circle", "children": []},
                            {"label": "Gráfico", "url": "oplectura:resultados", "icon": "far fa-circle", "children": []},
                        ]
                    },
                    {"label": "Mayo 2025", "url": "evaluaciones_educativas:analisis_evaluacion_mayo_2025", "icon": "far fa-dot-circle", "children": []},
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


def build_director_menu(user):
    """
    Construye menú específico para Directores
    """
    menu = copy.deepcopy(MENU_DIRECTOR)

    # 🔎 Filtrar Bibliotecas
    for sec in menu:
        if sec.get('label') == 'Relevamiento':
            sec['children'] = [
                item for item in sec.get('children', [])
                if item['label'] != 'Bibliotecas' or user.tiene_biblioteca()
            ]

    return menu


def user_menu(request):
    """
    Genera el menú dinámico según rol
    """

    if not request.user.is_authenticated:
        return {"menu": []}

    ctx = get_user_context(request.user)
    
    # 👇 AGREGALO ACÁ
    print("ROL LOGUEADO:", ctx.rol)

    # 🏠 Base común
    base_menu = [{
        "label": "Inicio",
        "icon": "fas fa-home",
        "children": []
    }]

    # 🔀 Routing por rol
    if ctx.rol in ('Administrador', 'Gestor'):
        base_menu[0]["url"] = "archivos:portada_gestor"
        return {"menu": base_menu, "user_rol": ctx.rol}

    if ctx.rol == 'Director':
        base_menu[0]["url"] = "directores:institucional"

        full_menu = base_menu + build_director_menu(request.user)

        return {"menu": full_menu, "user_rol": ctx.rol}

    # 🧩 fallback
    return {"menu": base_menu, "user_rol": ctx.rol}


def menu_context(request):
    return user_menu(request)