from typing import List, Dict

def get_menu(user) -> List[Dict]:
    if not hasattr(user, 'perfil') or not user.perfil.rol:
        return []

    rol = user.perfil.rol.nombre
    categoria = user.perfil.rol.categoria_acceso

    menu = [
        {
            "key": "inicio",
            "label": "Inicio",
            "icon": "fas fa-home",
            "roles": ["Administrador", "Gestor"],
            "categorias": ["all"],
            "url": "archivos:portada_gestor"
        },
        {
            "key": "inicio_func",
            "label": "Inicio",
            "icon": "fas fa-home",
            "roles": ["Ministro", "Subsecretario", "Director General", "Director de Nivel"],
            "categorias": ["nivel"],
            "url": "funcionario:portada_func"
        },
        {
            "key": "institucional",
            "label": "Institucional",
            "icon": "fas fa-school",
            "roles": ["Director/a"],
            "categorias": ["propio"],
            "url": "directores:institucional"
        },
        {
            "key": "regional",
            "label": "Regional",
            "icon": "fas fa-map",
            "roles": [],
            "categorias": ["regional"],
            "url": "oplectura:portada_regional"
        },
        {
            "key": "reportes",
            "label": "Reportes",
            "icon": "fas fa-chart-bar",
            "roles": ["Administrador", "Gestor"],
            "categorias": ["all"],
            "url": "archivos:reportes"
        },
    ]

    # 🎯 FILTRAR SEGÚN USUARIO
    menu_filtrado = []

    for item in menu:
        if item["roles"] and rol in item["roles"]:
            menu_filtrado.append(item)
        elif item["categorias"] and categoria in item["categorias"]:
            menu_filtrado.append(item)

    return menu_filtrado