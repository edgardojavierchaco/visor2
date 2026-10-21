#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comparación de CUEANEXO autorizados.

Compara:
1. Consulta antigua mediante v_capa_unica_ofertas_ant.
2. Consulta optimizada directamente a Padron.

Ejecutar:
    python3 comparar_cueanexos.py

Por defecto utiliza config.settings.local.
"""

import os
import django
import time

# ==========================================
# CONFIGURACIÓN DJANGO
# ==========================================

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.local"
)

django.setup()

# ==========================================
# IMPORTACIONES
# ==========================================

from apps.usuarios.models import UsuariosVisualizador
from apps.bnhpersonas_old.utils import get_ofertas_usuario
from apps.core.security.padron_access import user_cueanexos

# ==========================================
# USUARIO A VERIFICAR
# ==========================================

CUIL_PRUEBA = os.environ.get(
    "CUIL_PRUEBA",
    "27303807891"
).strip()

print("=" * 65)
print("COMPARACIÓN DE CUEANEXO - VISOR EDUCATIVO")
print("=" * 65)

print(f"CUIL: {CUIL_PRUEBA}")

# ==========================================
# BUSCAR USUARIO
# ==========================================

try:
    user = UsuariosVisualizador.objects.get(
        username=CUIL_PRUEBA
    )

except UsuariosVisualizador.DoesNotExist:
    print("ERROR: El usuario no existe.")
    raise SystemExit(1)

# ==========================================
# CONSULTA ANTIGUA
# ==========================================

print("\nConsultando mecanismo antiguo...")

inicio = time.perf_counter()

antiguos = {
    str(x).strip()
    for x in get_ofertas_usuario(user).values_list(
        "cueanexo",
        flat=True
    )
    if x is not None
}

tiempo_antiguo = time.perf_counter() - inicio

# ==========================================
# CONSULTA OPTIMIZADA
# ==========================================

print("Consultando mecanismo optimizado...")

inicio = time.perf_counter()

nuevos = set(user_cueanexos(user))

tiempo_nuevo = time.perf_counter() - inicio

# ==========================================
# RESULTADOS
# ==========================================

print("\n" + "=" * 65)
print("RESULTADOS")
print("=" * 65)

print(f"\nCoinciden: {antiguos == nuevos}")

print("\nCUEANEXO ANTIGUOS:")
for cue in sorted(antiguos):
    print(f"  {cue}")

print("\nCUEANEXO NUEVOS:")
for cue in sorted(nuevos):
    print(f"  {cue}")

print("\nSOLO ANTIGUOS:")
print(sorted(antiguos - nuevos))

print("\nSOLO NUEVOS:")
print(sorted(nuevos - antiguos))

print("\n" + "=" * 65)
print("RENDIMIENTO")
print("=" * 65)

print(f"Consulta antigua: {tiempo_antiguo:.4f} segundos")
print(f"Consulta nueva:   {tiempo_nuevo:.4f} segundos")

print(f"\nTotal antiguos: {len(antiguos)}")
print(f"Total nuevos:   {len(nuevos)}")

if antiguos == nuevos:
    print("\nOK: Los resultados coinciden para este usuario.")
else:
    print("\nATENCIÓN: Existen diferencias entre ambos mecanismos.")

print("=" * 65)
