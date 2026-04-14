import json
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse

# Importamos modelos y funciones auxiliares
from .models import PadronRegional

# =====================================================================
# 1. FUNCIÓN DE JERARQUÍA OFICIAL (EL "MAPA MAESTRO")
# =====================================================================
def get_jerarquia_oficial_padron(request):
    """
    Endpoint JSON que define la estructura geográfica oficial.
    Se usa para blindar los filtros contra errores de carga en la BD.
    Resuelve casos como 'Maipú' apareciendo en 'Región 3' por error.
    """
    jerarquia_data = {
        "region_depto_localidad": {
            "REGION 1": {"GENERAL GUEMES": ["MISIÓN NUEVA POMPEYA"]},
            "SUBSEDE 1 A": {"GENERAL GUEMES": ["FUERTE ESPERANZA", "COMANDANCIA FRIAS"]},
            "SUBSEDE 1 B": {"GENERAL GUEMES": ["EL SAUZALITO"]},
            "REGION 2": {"GENERAL GUEMES": ["JUAN JOSE CASTELLI", "EL ESPINILLO", "MIRAFLORES", "VILLA RIO BERMEJITO"]},
            "SUBSEDE 2": {"MAIPU": ["TRES ISLETAS"]},
            "REGION 3": {
                "INDEPENDENCIA": ["NAPENAY", "AVIA TERAI"],
                "ALMIRANTE BROWN": ["CONCEPCION DEL BERMEJO", "RIO MUERTO", "LOS FRENTONES", "PAMPA DEL INFIER."]
            },
            "SUBSEDE 3": {"ALMIRANTE BROWN": ["TACO POZO"]},
            "REGION 4-A": {"COMANDANTE FERNANDEZ": ["PRESIDENCIA ROQUE SAENZ PEÑA"]},
            "REGION 4-B": {
                "QUITILIPI": ["QUITILIPI"],
                "25 DE MAYO": ["MACHAGAI"],
                "PRESIDENCIA DE LA PLAZA": ["PRESIDENCIA DE LA PLAZA"]
            },
            "REGION 5": {"LIBERTADOR GENERAL SAN MARTIN": ["GRAL. JOSE DE SAN MARTIN", "LA EDUVIGIS", "SELVA RIO DE ORO", "PAMPA ALMIRON"]},
            "SUBSEDE 5": {"LIBERTADOR GENERAL SAN MARTIN": ["PAMPA DEL INDIO", "LAGUNA LIMPIA", "CIERVO PETISO", "PRESIDENCIA ROCA"]},
            "REGION 6": {"BERMEJO": ["LA LEONESA", "PUERTO EVA PERON", "PUERTO BERMEJO", "LAS PALMAS", "GENERAL VEDIA", "ISLA DEL CERRITO"]},
            "REGION 7": {
                "GENERAL DONOVAN": ["LA ESCONDIDA", "LA VERDE", "LAPACHITO", "MAKALLE"],
                "SARGENTO CABRAL": ["COLONIA ELISA", "CAPITAN SOLARI", "COLONIAS UNIDAS", "LAS GARCITAS"],
                "LIBERTAD": ["LAGUNA BLANCA"]
            },
            "REGION 8-A": {
                "9 DE JULIO": ["LAS BREÑAS"],
                "GRAL BELGRANO": ["CORZUELA"],
                "INDEPENDENCIA": ["CAMPO LARGO"],
                "CHACABUCO": ["CHARATA"]
            },
            "REGION 8-B": {
                "12 DE OCTUBRE": ["GENERAL PINEDO", "GENERAL CAPDEVILA", "GANCEDO"],
                "2 DE ABRIL": ["HERMOSO CAMPO"]
            },
            "REGION 9": {
                "MAYOR LUIS J. FONTANA": ["VILLA ANGELA", "CORONEL DU GRATY", "ENRIQUE URIEN"],
                "FRAY JUSTO SANTA M. DE ORO": ["CHOROTIS", "SANTA SYLVINA"],
                "SAN LORENZO": ["SAMUHU", "VILLA BERTHET"],
                "O HIGGINS": ["SAN BERNARDO", "LA CLOTILDE", "LA TIGRA"]
            },
            "REGION 10-A": {"SAN FERNANDO": ["RESISTENCIA"]},
            "REGION 10-B": {"SAN FERNANDO": ["COLONIA BARANDA", "RESISTENCIA"]},
            "REGION 10-C": {
                "SAN FERNANDO": ["BARRANQUERAS", "PUERTO VILELAS", "FONTANA", "BASAIL"],
                "1° DE MAYO": ["COLONIA BENITEZ", "MARGARITA BELEN"],
                "LIBERTAD": ["COLONIA POPULAR", "PUERTO TIROL"],
                "TAPENAGA": ["COTE LAI", "CHARADAI"]
            }
        }
    }
    return JsonResponse(jerarquia_data)

# =====================================================================
# 2. VISTA DE LISTADO DE PADRÓN REGIONAL
# =====================================================================
@method_decorator(login_required, name='dispatch')
class PadronRegionalListView(ListView):
    model = PadronRegional
    template_name = 'indicadoresie/seguimiento/padron_regionales.html'
    context_object_name = 'escuelas'

    # TRADUCTOR DE REGIONES: Formato BD ("R.E. 1") <-> Formato Humano ("REGION 1")
    TRADUCTOR_REGIONES = {
        'R.E. 1': 'REGION 1', 'R.E. 2': 'REGION 2', 'R.E. 3': 'REGION 3',
        'R.E. 4-A': 'REGION 4-A', 'R.E. 4-B': 'REGION 4-B', 'R.E. 5': 'REGION 5',
        'R.E. 6': 'REGION 6', 'R.E. 7': 'REGION 7', 'R.E. 8-A': 'REGION 8-A',
        'R.E. 8-B': 'REGION 8-B', 'R.E. 9': 'REGION 9', 'R.E. 10-A': 'REGION 10-A',
        'R.E. 10-B': 'REGION 10-B', 'R.E. 10-C': 'REGION 10-C',
        'SUB. R.E. 1-A': 'SUBSEDE 1 A', 'SUB. R.E. 1-B': 'SUBSEDE 1 B',
        'SUB. R.E. 2': 'SUBSEDE 2', 'SUB. R.E. 3': 'SUBSEDE 3', 'SUB. R.E. 5': 'SUBSEDE 5',
    }
    INV_TRADUCTOR_REGIONES = {v: k for k, v in TRADUCTOR_REGIONES.items()}

    # ESCUDO DE NORMALIZACIÓN: Filtra entradas hacia el formato exacto de la BD
    DEPT_NAME_MAP = {
        '1 DE MAYO': '1§ DE MAYO', '1° DE MAYO': '1§ DE MAYO',
        'MAYOR LUIS J. FONTANA': 'MAYOR LUIS J FONTANA',
        'PCIA. DE LA PLAZA': 'PRESIDENCIA DE LA PLAZA',
        'GRAL BELGRANO': 'GENERAL BELGRANO',
        'FRAY JUSTO SANTA M. DE ORO': 'FRAY JUSTO SANTA MARIA DE ORO',
        "O'HIGGINS": "O HIGGINS",
    }

    LOC_NAME_MAP = {
        'MISIÓN NUEVA POMPEYA': 'NUEVA POMPEYA',
        'PUERTO BERMEJO': 'PUERTO BERMEJO NUEVO',
        'GRAL. JOSE DE SAN MARTIN': 'GENERAL JOSE DE SAN MARTIN',
        'PAMPA DEL INFIER.': 'PAMPA DEL INFIERNO'
    }

    # TRADUCTORES VISUALES: Estética para el usuario (BD -> Pantalla)
    VISUAL_DEPT_MAP = {
        '1§ DE MAYO': '1 DE MAYO',
        'MAYOR LUIS J FONTANA': 'MAYOR LUIS J. FONTANA',
        'O HIGGINS': "O'HIGGINS",
    }

    VISUAL_LOC_MAP = {
        'NUEVA POMPEYA': 'MISIÓN NUEVA POMPEYA',
        'PUERTO BERMEJO NUEVO': 'PUERTO BERMEJO',
        'VILLA RIO BERMEJITO': 'VILLA RÍO BERMEJITO'
    }

    def get_queryset(self):
        # ABIERTO PARA TODOS: Devuelve absolutamente todas las escuelas
        # sin importar los permisos del usuario logueado.
        return PadronRegional.objects.all().order_by('nom_est')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['titulo'] = "Padrón de Escuelas Regionales"
        # Forzamos la etiqueta para que no muestre zonas limitadas
        context['region_actual'] = "Todas las Regiones" 

        # Serialización de mapas para JavaScript
        context['mapa_regiones'] = json.dumps(self.INV_TRADUCTOR_REGIONES)
        context['mapa_regiones_inverso'] = json.dumps(self.TRADUCTOR_REGIONES)
        context['mapa_deptos'] = json.dumps(self.DEPT_NAME_MAP)
        context['mapa_locs'] = json.dumps(self.LOC_NAME_MAP)
        context['visual_dept_map'] = json.dumps(self.VISUAL_DEPT_MAP)
        context['visual_loc_map'] = json.dumps(self.VISUAL_LOC_MAP)

        # Obtención de ofertas únicas para el filtro
        qs = self.get_queryset()
        ofertas_brutas = qs.exclude(oferta__isnull=True).exclude(oferta__exact='').values_list('oferta', flat=True).distinct()
        ofertas_limpias = set()
        for string_oferta in ofertas_brutas:
            texto_limpio = str(string_oferta).strip().upper()
            if texto_limpio:
                ofertas_limpias.add(texto_limpio)

        context['lista_ofertas'] = sorted(list(ofertas_limpias))
        return context