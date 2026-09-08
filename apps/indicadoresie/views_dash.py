from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import CharField, Func, Value
from django.db.models.functions import Cast
from django.utils.decorators import method_decorator
import psycopg2
import os
import re

from .models import InformeSGE, PadronRegional, UsuarioPerfil


ROLES_GLOBALES_SGE = {
    "Administrador",
    "Director de Modalidad Adultos",
    "Director de Modalidad Contexto",
    "Director de Modalidad Especial",
    "Director de Modalidad Rural",
    "Director de Nivel",
    "Director de Nivel Inicial",
    "Director de Nivel Primario",
    "Director de Nivel Secundario",
    "Director de Nivel Superior",
    "Director de Servicios Complementarios",
    "Director General",
    "Ministro",
    "Subsecretario",
    "Supervisor",
}
ROLES_REGIONALES_SGE = {"Regional"}
ROLES_GESTORES_SGE = {"Gestor", "Gestor / Agente"}
SESSION_SGE_CUEANEXO_KEY = "sge_cueanexo_actual"
PARAM_SGE_CUEANEXO = "cueanexo_contexto_sge"

# =====================================================================
# AUXILIARES DE ROL (COMPLETO: Evita errores y reconoce Gestores)
# =====================================================================

def obtener_cargo_usuario(user_or_cuil):
    """
    Retorna el nombre del cargo. 
    Acepta tanto el objeto 'user' como un 'string' con el CUIL.
    Busca primero en la tabla nueva de roles. Si no lo encuentra,
    revisa las tablas viejas para ver si es Regional o Gestor.
    """
    try:
        # Extraemos el CUIL
        if hasattr(user_or_cuil, 'username'):
            cuil = user_or_cuil.username
        else:
            cuil = str(user_or_cuil)

        # 1. Intentamos buscar en la tabla NUEVA (Ministros, Directores, etc.)
        try:
            perfil = UsuarioPerfil.objects.select_related('rol').get(usuario__username=cuil)
            return perfil.rol.nombre
        except UsuarioPerfil.DoesNotExist:
            pass # Si no está acá, seguimos al paso 2

        # 2. Si no está en la nueva, buscamos en las tablas VIEJAS (Regionales y Gestores)
        connection = None
        try:
            connection = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST'),
                user=os.getenv('POSTGRES_USER'),
                password=os.getenv('POSTGRES_PASSWORD'),
                database=os.getenv('POSTGRES_DB') 
            )
            cursor = connection.cursor()
            
            # ¿Es un Director Regional?
            cursor.execute("SELECT 1 FROM public.usuarios_regionalusuarios WHERE usuario = %s AND activo = true LIMIT 1", [cuil])
            if cursor.fetchone():
                return "Regional" # Mantenemos "Regional" para compatibilidad con ROLES_BYPASS si fuera necesario
                
            # ¿Es un Gestor/Agente?
            cursor.execute("SELECT 1 FROM public.usuarios_regionalusuariosagentes WHERE usuario = %s AND activo = true LIMIT 1", [cuil])
            if cursor.fetchone():
                return "Gestor / Agente"
                
        except Exception as e:
            print(f"Error verificando tablas viejas en obtener_cargo_usuario: {e}")
        finally:
            if connection:
                connection.close()

        # Si no está en NINGUNA tabla, es un usuario genérico
        return "Usuario"

    except Exception:
        return "Usuario"

# =====================================================================
# MOTOR DE PERMISOS (Respetando Regionales y Gestores)
# =====================================================================

def obtener_regiones_permitidas(user_or_cuil):
    """
    Acepta tanto el objeto 'user' como un 'string' con el CUIL.
    """
    cargo = obtener_cargo_usuario(user_or_cuil)

    if hasattr(user_or_cuil, 'username'):
        username = user_or_cuil.username
    else:
        username = str(user_or_cuil)

    if cargo in ROLES_GLOBALES_SGE:
        return "TODAS"

    if cargo not in ROLES_REGIONALES_SGE and cargo not in ROLES_GESTORES_SGE:
        return set()

    regiones = set()
    connection = None
    try:
        connection = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )
        cursor = connection.cursor()

        if cargo in ROLES_REGIONALES_SGE:
            cursor.execute(
                "SELECT region_loc FROM public.usuarios_regionalusuarios "
                "WHERE usuario = %s AND activo = true",
                [username],
            )
        else:
            cursor.execute(
                "SELECT region_loc FROM public.usuarios_regionalusuariosagentes "
                "WHERE usuario = %s AND activo = true",
                [username],
            )

        for fila in cursor.fetchall():
            region = str(fila[0] or "").strip()
            if region:
                regiones.add(region)

    except Exception as e:
        print(f"Error BD Permisos: {e}")
    finally:
        if connection:
            connection.close()

    if cargo in ROLES_GESTORES_SGE and any(
        region.casefold() == "todas" for region in regiones
    ):
        return "TODAS"

    return regiones

# =====================================================================
# FILTRO MAESTRO DE ESCUELAS
# =====================================================================

def _solo_digitos_sge(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _normalizar_cuil_usuario_sge(user):
    if not user or not getattr(user, "is_authenticated", False):
        return ""

    cuil = _solo_digitos_sge(getattr(user, "username", ""))
    return cuil if len(cuil) == 11 else ""


def _normalizar_cueanexo_sge(valor):
    return _solo_digitos_sge(valor)


def _opciones_cueanexo_sge(user):
    cuil = _normalizar_cuil_usuario_sge(user)
    if not cuil:
        return []

    queryset = (
        PadronRegional.objects
        .annotate(
            responsable_cuil_limpio=Func(
                Cast("resploc_cuitcuil", CharField()),
                Value(r"\D"),
                Value(""),
                Value("g"),
                function="REGEXP_REPLACE",
                output_field=CharField(),
            )
        )
        .filter(responsable_cuil_limpio=cuil)
        .order_by("cueanexo", "nom_est")
        .values(
            "padron_cueanexo",
            "cueanexo",
            "nom_est",
            "etiqueta",
            "region_loc",
        )
    )

    opciones = []
    cueanexos_vistos = set()
    for fila in queryset:
        cueanexo = _normalizar_cueanexo_sge(
            fila.get("padron_cueanexo") or fila.get("cueanexo")
        )
        if not cueanexo or cueanexo in cueanexos_vistos:
            continue
        cueanexos_vistos.add(cueanexo)
        nombre = str(fila.get("etiqueta") or "").strip()
        if not nombre:
            nombre = str(fila.get("nom_est") or "").split(" - ", 1)[0].strip()
        nombre = nombre or "Establecimiento sin nombre"
        opciones.append({
            "cueanexo": cueanexo,
            "nombre": nombre,
            "region": str(fila.get("region_loc") or "").strip(),
        })
    return opciones


def _resolver_cueanexo_sge(request, opciones):
    session = getattr(request, "session", None)
    raw = (
        request.GET.get(PARAM_SGE_CUEANEXO)
        or request.POST.get(PARAM_SGE_CUEANEXO)
        or ""
    )
    cueanexos_permitidos = {opcion["cueanexo"] for opcion in opciones}

    if raw:
        cueanexo = _normalizar_cueanexo_sge(raw)
        if not cueanexo or cueanexo not in cueanexos_permitidos:
            raise PermissionDenied("No podés acceder al CUE-Anexo solicitado.")
        if session is not None and session.get(SESSION_SGE_CUEANEXO_KEY) != cueanexo:
            session[SESSION_SGE_CUEANEXO_KEY] = cueanexo
        return cueanexo

    cueanexo_sesion = _normalizar_cueanexo_sge(
        session.get(SESSION_SGE_CUEANEXO_KEY, "") if session is not None else ""
    )
    if cueanexo_sesion in cueanexos_permitidos:
        return cueanexo_sesion

    if session is not None and cueanexo_sesion:
        session.pop(SESSION_SGE_CUEANEXO_KEY, None)

    cueanexo = opciones[0]["cueanexo"] if opciones else ""
    if cueanexo and session is not None:
        session[SESSION_SGE_CUEANEXO_KEY] = cueanexo
    return cueanexo


def resolver_contexto_sge(request):
    contexto_cacheado = getattr(request, "_sge_contexto_operativo", None)
    if contexto_cacheado is not None:
        return contexto_cacheado

    cargo = obtener_cargo_usuario(request.user)
    opciones_cueanexo = []
    cueanexo_actual = ""

    if cargo in ROLES_GLOBALES_SGE:
        alcance = "global"
        regiones_permitidas = "TODAS"

    elif cargo == "Director":
        alcance = "cue"
        opciones_cueanexo = _opciones_cueanexo_sge(request.user)
        regiones_permitidas = sorted({
            opcion["region"]
            for opcion in opciones_cueanexo
            if opcion["region"]
        })

    elif cargo in ROLES_REGIONALES_SGE:
        alcance = "regional"
        regiones = obtener_regiones_permitidas(request.user)
        regiones_permitidas = sorted(regiones or [])

    elif cargo in ROLES_GESTORES_SGE:
        regiones = obtener_regiones_permitidas(request.user)
        if regiones == "TODAS":
            alcance = "global"
            regiones_permitidas = "TODAS"
        else:
            alcance = "regional"
            regiones_permitidas = sorted(regiones or [])

    else:
        alcance = "sin_acceso"
        regiones_permitidas = []

    contexto = {
        "cargo": cargo,
        "alcance": alcance,
        "es_global": alcance == "global",
        "regiones_permitidas": regiones_permitidas,
        "cueanexos_permitidos": (
            [opcion["cueanexo"] for opcion in opciones_cueanexo]
            if alcance == "cue" else None
        ),
        "cueanexo_opciones": opciones_cueanexo,
        "cueanexo_actual": cueanexo_actual,
        "mostrar_selector_cueanexo": alcance == "cue" and cargo != "Director",
    }
    request._sge_contexto_operativo = contexto
    return contexto


def filtrar_queryset_sge(queryset, contexto, campo_region, campo_cueanexo):
    if contexto["alcance"] == "global":
        return queryset

    if contexto["alcance"] == "regional":
        regiones = contexto["regiones_permitidas"]
        if not regiones:
            return queryset.none()
        return queryset.filter(**{f"{campo_region}__in": regiones})

    if contexto["alcance"] == "cue":
        cueanexos = contexto.get("cueanexos_permitidos") or []
        if not cueanexos:
            return queryset.none()
        return queryset.filter(**{f"{campo_cueanexo}__in": cueanexos})

    if contexto["alcance"] == "sin_acceso":
        return queryset.none()

    return queryset.none()

def get_escuelas_autorizadas(request):
    contexto = resolver_contexto_sge(request)
    return filtrar_queryset_sge(
        InformeSGE.objects.all(),
        contexto,
        campo_region="regional",
        campo_cueanexo="cueanexo",
    )

# =====================================================================
# VISTAS
# =====================================================================

def normalizar_region_grafico(region_raw):
    if not region_raw or str(region_raw).strip() == '' or str(region_raw).lower() == 'nan':
        return None  
    r = str(region_raw).strip().upper()
    if r.startswith('REGION '): return r.replace('REGION ', 'R.E. ')
    if r.startswith('SUBSEDE '): return r.replace('SUBSEDE ', 'SUB. R.E. ')
    return r

def ordenar_region_grafico(region):
    coincidencia = re.search(r'\d+', region)
    if coincidencia:
        return (int(coincidencia.group()), 0 if region.startswith('R.E.') else 1, region)
    return (float('inf'), 0, region)

@method_decorator(login_required, name='dispatch')
class DashboardSeguimientoSIE2025View(TemplateView):
    template_name = 'indicadoresie/seguimiento/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        escuelas = get_escuelas_autorizadas(self.request)
        regiones_raw = escuelas.values_list('regional', flat=True).distinct()
        regiones_limpias = set()
        for r in regiones_raw:
            norm = normalizar_region_grafico(r)
            if norm: regiones_limpias.add(norm)
        
        context['regions'] = sorted(regiones_limpias, key=ordenar_region_grafico)
        context['sge_context'] = resolver_contexto_sge(self.request)
        context['cargo_usuario'] = context['sge_context']['cargo']
        context['active_menu'] = 'graficos'
        return context

@login_required
def seguimiento_sie_json(request):     
    escuelas = get_escuelas_autorizadas(request)
    datos_agrupados = {}
    for esc in escuelas:
        region = normalizar_region_grafico(esc.regional)
        if not region: continue
        if region not in datos_agrupados:
            datos_agrupados[region] = {"region": region, "total_ant": 0, "total_act": 0}
        
        # Uso de campos correctos: inscriptos_2025 e inscriptos_2026
        try: datos_agrupados[region]["total_ant"] += int(float(esc.inscriptos_2025))
        except: pass 
        try: datos_agrupados[region]["total_act"] += int(float(esc.inscriptos_2026))
        except: pass

    chart_data = []
    for data in sorted(datos_agrupados.values(), key=lambda item: ordenar_region_grafico(item["region"])):
        meta = data["total_ant"]
        prog = data["total_act"]
        pct = round((prog / meta) * 100, 2) if meta > 0 else 0
        data["regulares"] = pct if pct <= 100 else 100
        data["preinscriptos"] = 100 - data["regulares"]
        chart_data.append(data)
    return JsonResponse({"data": chart_data}, safe=False)

@login_required
def seguimiento_sie_niveles_json(request):
    requested_region = request.GET.get('region')
    escuelas = get_escuelas_autorizadas(request)
    datos_agrupados = {}
    for esc in escuelas:
        if normalizar_region_grafico(esc.regional) != requested_region: continue
        nivel = getattr(esc, 'tipo_oferta', "Sin Nivel")
        if nivel not in datos_agrupados:
            datos_agrupados[nivel] = {"nivel": nivel, "total_ant": 0, "total_act": 0}
        
        try: datos_agrupados[nivel]["total_ant"] += int(float(esc.inscriptos_2025))
        except: pass
        try: datos_agrupados[nivel]["total_act"] += int(float(esc.inscriptos_2026))
        except: pass

    chart_data = []
    for data in datos_agrupados.values():
        meta = data["total_ant"]
        prog = data["total_act"]
        pct = round((prog / meta) * 100, 2) if meta > 0 else 0
        data["regulares"] = pct if pct <= 100 else 100
        data["preinscriptos"] = 100 - data["regulares"]
        chart_data.append(data)
    return JsonResponse({"niveles": chart_data}, safe=False)
