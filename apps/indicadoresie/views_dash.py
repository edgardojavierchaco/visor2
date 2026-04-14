from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
import psycopg2
import os

from .models import InformeSGE, UsuarioPerfil

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
            cursor.execute("SELECT 1 FROM public.usuarios_regionalusuariosagentes WHERE usuario = %s LIMIT 1", [cuil])
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
    
    # Extraemos el CUIL para las consultas SQL
    if hasattr(user_or_cuil, 'username'):
        username = user_or_cuil.username
    else:
        username = str(user_or_cuil)

    # 1. LISTA VIP (Solo estos ven TODAS las regiones)
    ROLES_BYPASS = [
        "Ministro", 
        "Subsecretario", 
        "Director General", 
        "Administrador",
        "Director de Nivel Inicial", 
        "Director de Nivel Primario", 
        "Director de Nivel Secundario", 
        "Director de Nivel Superior",
        "Director de Modalidad Adultos", 
        "Director de Modalidad Rural",
        "Director de Modalidad Especial", 
        "Director de Modalidad Contexto",
        "Director de Servicios Complementarios"
    ]

    if cargo in ROLES_BYPASS:
        return "TODAS"
    
    # 2. LÓGICA PARA REGIONALES Y GESTORES (SQL Original)
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
        
        # Regionales
        cursor.execute("SELECT region_loc FROM public.usuarios_regionalusuarios WHERE usuario = %s AND activo = true", [username])
        for fila in cursor.fetchall():
            if fila[0]: regiones.add(fila[0].strip())
                
        # Gestores / Agentes
        cursor.execute("SELECT region_loc FROM public.usuarios_regionalusuariosagentes WHERE usuario = %s", [username])
        for fila in cursor.fetchall():
            if fila[0]: regiones.add(fila[0].strip())
                
    except Exception as e:
        print(f"Error BD Permisos: {e}")
    finally:
        if connection: connection.close()

    return list(regiones)

# =====================================================================
# FILTRO MAESTRO DE ESCUELAS
# =====================================================================

def get_escuelas_autorizadas(request):
    user = request.user
    cargo = obtener_cargo_usuario(user)
    
    escuelas = InformeSGE.objects.all()
    
    # --- FILTRO 1: REGIONES ---
    regiones_asignadas = obtener_regiones_permitidas(user)
    
    if regiones_asignadas != "TODAS":
        if not regiones_asignadas:
            return InformeSGE.objects.none()
        escuelas = escuelas.filter(regional__in=regiones_asignadas)

    # --- FILTRO 2: NIVEL/MODALIDAD (Solo para los Directores) ---
    MAPA_OFERTAS = {
        "Director de Nivel Inicial": ["Inicial - Común"],
        "Director de Nivel Primario": ["Primario - Común"],
        "Director de Nivel Secundario": ["Secundario - Común"],
        "Director de Modalidad Adultos": ["Primario - Adultos", "Secundario - Adultos"],
        "Director de Modalidad Especial": ["Inicial - Especial", "Primario - Especial"],
    }

    if cargo in MAPA_OFERTAS:
        escuelas = escuelas.filter(tipo_oferta__in=MAPA_OFERTAS[cargo])

    return escuelas

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
        
        context['regions'] = sorted(list(regiones_limpias))
        context['cargo_usuario'] = obtener_cargo_usuario(self.request.user)
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
        
        # Uso de campos correctos: inscriptos_2025 y sge_2026
        try: datos_agrupados[region]["total_ant"] += int(float(esc.inscriptos_2025))
        except: pass 
        try: datos_agrupados[region]["total_act"] += int(float(esc.sge_2026))
        except: pass

    chart_data = []
    for data in datos_agrupados.values():
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
        try: datos_agrupados[nivel]["total_act"] += int(float(esc.sge_2026))
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