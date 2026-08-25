# Contexto de onboarding para agentes

## 1. Qué es este proyecto

Visor Educativo es un monolito Django utilizado por el Ministerio de Educación
para consultar y administrar información educativa. Este repositorio contiene
múltiples módulos; el alcance habitual de los cambios de este equipo es
Educación Especial, ubicado principalmente en `apps/especial/`.

El módulo administra, entre otros conceptos:

- establecimientos identificados por CUE-Anexo;
- ciclos lectivos y ofertas educativas;
- secciones y turnos;
- alumnos, bancos de alumnos e inscripciones;
- docentes y sus asignaciones a secciones;
- visualizadores globales de alumnos, docentes y directores.

Educación Especial no debe interpretarse como una copia directa de otros
módulos. Puede compartir integraciones o patrones con `apps/cef`,
`apps/bnhalumnos` y `apps.bnhpersonas`, pero sus reglas propias deben verificarse
antes de reutilizar una solución. En particular, el concepto operativo es
“sección”, no “grupo”.

## 2. Cómo orientarse al comenzar

Leer los documentos en este orden:

1. `AGENTS.md`: límites técnicos, convenciones y forma de trabajo.
2. `contexto.md`: este mapa general del sistema y del flujo de investigación.
3. `reglas-negocio.md`: comportamiento funcional que no debe romperse.
4. `contexto.txt`: contexto histórico y expectativas de comunicación.

Después, revisar el estado del repositorio y localizar el flujo concreto antes
de editar:

```powershell
git status --short
rg -n "termino|nombre_de_vista|nombre_del_modelo" apps/especial templates/especial
```

No asumir que un dato mostrado en pantalla proviene de una tabla propia. Puede
provenir de Padrón, BNH de personas, `apps.bnhalumnos` o de una vista de base
de datos. Confirmar siempre el origen en el modelo, la consulta y el template.

## 3. Mapa rápido del código

- `apps/especial/models.py`: entidades, estados, propiedades y restricciones.
- `apps/especial/forms.py`: formularios y clases Bootstrap.
- `apps/especial/services/`: operaciones de dominio que requieren consistencia
  o transacciones.
- `apps/especial/views_*.py`: vistas funcionales separadas por dominio.
- `apps/especial/migrations/`: cambios de esquema y migraciones de datos.
- `templates/especial/`: páginas, formularios y partials.
- `apps/especial/static/especial/js/`: comportamiento de modales, búsquedas y
  navegación parcial.
- `apps/especial/static/especial/css/`: estilos específicos del módulo.

En los flujos de frontend, comprobar siempre la interacción entre vista,
partial, JavaScript y URL. Un partial puede reemplazar el contenido sin una
recarga completa, por lo que un componente Bootstrap o un handler puede
necesitar reinicialización.

## 4. Integraciones y permisos

El módulo se integra con:

- Padrón, para establecimientos, CUE-Anexos y ofertas;
- BNH de personas, para datos de personas y docentes;
- `apps.bnhalumnos`, para información de alumnos.

El acceso se limita por rol y por CUE-Anexo. Los filtros recibidos desde el
navegador no son una frontera de seguridad: toda vista, servicio y operación de
escritura debe validar nuevamente el alcance permitido en el servidor.

## 5. Flujo seguro para implementar cambios

1. Identificar el caso de uso y la regla funcional involucrada.
2. Buscar modelos, servicios, vistas, templates y JavaScript que participen.
3. Revisar datos existentes y migraciones pendientes antes de cambiar el
   esquema.
4. Implementar la validación en servidor; agregar validación visual sólo como
   ayuda para el usuario.
5. Usar transacciones y bloqueos cuando se modifiquen estados, inscripciones o
   asignaciones relacionadas.
6. Ejecutar la comprobación más acotada posible.
7. Revisar el diff y confirmar que no se tocaron cambios ajenos.

Comando habitual dentro del entorno Docker:

```powershell
docker compose -f local.yml exec -T django python manage.py <comando>
```

Ejemplos de comprobaciones útiles:

```powershell
docker compose -f local.yml exec -T django python manage.py check
docker compose -f local.yml exec -T django python manage.py showmigrations especial
git diff --check
```

Si el contenedor no está disponible, informar la limitación y separar las
comprobaciones realizadas localmente de las que requieren PostgreSQL.

## 6. Riesgos frecuentes

- Confundir una sección con un grupo o suponer que dos módulos comparten la
  misma semántica.
- Resolver un problema sólo ocultando una opción en el navegador.
- Consultar un nombre de establecimiento desde una fuente que no contiene ese
  dato, especialmente en los visualizadores.
- Crear una migración de esquema sin contemplar los datos duplicados o
  incompatibles que ya existen.
- Cambiar un estado sin actualizar fechas, relaciones o campos derivados.
- Agregar una restricción de unicidad sin revisar primero los duplicados
  actuales.
- Modificar directamente la base de datos sin autorización explícita,
  diagnóstico previo y copia o procedimiento de recuperación.
- Reutilizar un partial o JavaScript sin tener en cuenta la navegación parcial.

## 7. Criterio de entrega

Una tarea se considera lista cuando el cambio solicitado está implementado,
las reglas existentes siguen siendo respetadas, la comprobación disponible fue
ejecutada y se informa cualquier limitación de entorno. La respuesta final debe
indicar qué se modificó, qué se verificó y si hace falta ejecutar una migración,
reiniciar un contenedor o recargar archivos estáticos.

