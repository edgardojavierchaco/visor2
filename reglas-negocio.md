# Reglas de negocio — Módulo Educación Especial

Este documento resume las reglas funcionales que deben respetar los agentes al
modificar el módulo `apps/especial/`. Si una tarea contradice una regla, se
debe pedir confirmación antes de cambiarla.

## Alcance y conceptos

- El módulo administra establecimientos, ciclos lectivos, secciones,
  alumnos, docentes, bancos e inscripciones de Educación Especial.
- El establecimiento se identifica mediante un CUE-Anexo normalizado de nueve
  dígitos.
- La unidad funcional se llama **sección**, no grupo ni actividad.
- El ciclo lectivo forma parte del alcance de casi todas las operaciones.
- Los datos del Padrón son una fuente externa de consulta; no deben asumirse
  como datos locales editables.

## Permisos y alcance

- Toda operación debe respetar el CUE-Anexo y el ciclo autorizados para el
  usuario.
- No confiar únicamente en valores enviados por el navegador: validar otra vez
  en la vista, servicio y/o consulta segura del servidor.
- Las vistas operativas deben usar `@especial_required` y `contexto_base()`.
- Un ciclo cerrado sólo permite consulta; no permite altas, bajas, edición,
  reinscripción ni cambios de asignación.

## Secciones

- Una sección pertenece a un CUE-Anexo y a un ciclo lectivo.
- Una sección tiene tipo de sección, estructura especial, nombre, oferta,
  capacidad, turno, rango etario, modalidad, lugar de dictado y estado.
- Los estados de sección son: `borrador`, `activo`, `inactivo` y `cerrado`.
- Sólo las secciones `activo` pueden recibir nuevas inscripciones o nuevas
  asignaciones operativas.
- La oferta de la sección se selecciona desde las ofertas disponibles del
  CUE-Anexo en el Padrón y se persiste en `SeccionEspecial.oferta`.
- La oferta permite distinguir, por ejemplo, una sección de Integración de
  otra oferta del mismo establecimiento.
- La unicidad de una sección contempla CUE-Anexo, ciclo, nombre, tipo de
  sección y oferta.
- Las secciones sin docentes activos deben mostrar la alerta de falta de
  docentes; los estados `inactivo` y `baja` no cuentan como activos.
- Las secciones sin alumnos activos deben mostrar la alerta correspondiente.

## Ofertas de Integración y matrícula compartida

- Una oferta se considera de Integración cuando su texto contiene el término
  normalizado `integracion`, sin depender de mayúsculas, acentos o separadores.
- Agregar un alumno al banco no debe exigir todavía la matrícula compartida.
- La matrícula compartida puede quedar vacía en el banco.
- Al intentar inscribir al alumno en una sección cuya oferta sea Integración,
  debe abrirse un modal y exigirse un CUE-Anexo de Educación Común.
- El CUE-Anexo elegido debe existir en Padrón y tener al menos una oferta
  Común; no puede ser igual al CUE-Anexo actual.
- La selección realizada en el modal debe guardarse en
  `EspecialAlumnoBanco.matricula_compartida` antes o junto con la inscripción.
- Si el alumno se da de baja del banco, `matricula_compartida` debe quedar en
  `NULL`.
- Si posteriormente se lo carga en otro CUE-Anexo de Integración, puede volver
  a utilizar el mismo CUE-Anexo común que tenía antes.
- Dos bancos activos de Integración pueden compartir el mismo CUE-Anexo
  común. No se debe exigir que la matrícula compartida apunte al otro CUE de
  Integración.
- Las consultas que busquen ofertas del Padrón deben contemplar tanto
  `cueanexo` como `padron_cueanexo`, porque la fuente puede usar cualquiera de
  esas columnas.

## Banco de alumnos e inscripciones

- Un alumno puede tener como máximo dos bancos activos en el mismo ciclo.
- No puede haber dos bancos activos del mismo alumno para el mismo CUE-Anexo,
  ciclo y alumno.
- Dar de baja el banco no debe borrar inscripciones históricas.
- Una inscripción activa requiere que el alumno esté activo en el banco del
  mismo CUE-Anexo y ciclo.
- Una sección no debe superar su capacidad total de alumnos activos.
- Reinscribir debe actualizar/reactivar la relación correspondiente sin crear
  inscripciones activas duplicadas.
- Las bajas de banco e inscripciones deben validar el motivo/fecha cuando la
  regla del formulario los exige y deben ejecutarse dentro de una transacción.

## Docentes y asignaciones

- Los roles válidos son `titular`, `suplente` e `interino`. No usar `apoyo`.
- Los estados de una asignación son `activo`, `inactivo` y `baja`.
- Un docente sólo puede tener una relación con una misma sección, por CUIL,
  independientemente del estado. Los cambios de estado o rol deben actualizar
  la relación existente, no crear otra fila.
- Una asignación `activo` ocupa el rol correspondiente; no puede haber dos
  docentes activos con el mismo rol en una sección.
- `inactivo` y `baja` no cuentan como docentes activos para las alertas de la
  sección.
- Un docente `inactivo` o `activo` no debe aparecer como disponible para
  asignarlo nuevamente a la misma sección.
- Una asignación `baja` puede reactivarse mediante el flujo previsto, sujeto a
  las validaciones de rol y banco.
- No presentar registros históricos duplicados como si fueran docentes
  distintos en la gestión de una sección.
- Todavía no existe un historial formal de cambios de asignación. Si se
  implementa, debe ser una entidad de historial/eventos separada de la relación
  vigente única.

## Visualizadores

- El visualizador de alumnos parte del banco de alumnos y debe respetar sus
  filtros de estado, CUE-Anexo y ciclo.
- El visualizador debe incluir establecimientos y ofertas de las asignaciones
  docentes, incluso cuando el estado sea `inactivo` o `baja`, si el filtro lo
  solicita.
- El visualizador global de directores debe tener una entrada por director,
  agrupando sus vínculos por CUE-Anexo y oferta.
- No mostrar `—` cuando el establecimiento puede resolverse desde Padrón:
  normalizar y buscar por CUE-Anexo y, si hace falta, por
  `padron_cueanexo`.

## Persistencia y migraciones

- Los modelos principales usan el esquema PostgreSQL `especial`.
- Las migraciones deben declarar claramente si agregan restricciones, cambian
  estados o eliminan datos duplicados.
- Antes de aplicar una restricción única, diagnosticar y limpiar duplicados de
  forma explícita y determinista.
- Las eliminaciones de datos históricos no deben ejecutarse automáticamente sin
  explicar qué se conserva y qué se elimina.
- No usar `dbshell` dentro del contenedor `django` si no tiene `psql`; para
  consultas puntuales usar `manage.py shell` o el contenedor de PostgreSQL.

## Frontend y navegación

- Los formularios deben usar clases Bootstrap mediante
  `_aplicar_clases_bootstrap()`.
- Los modales y formularios AJAX deben mostrar errores del servidor y no
  quedarse en estado de carga permanente.
- Al reemplazar un partial, reinicializar Select2, tablas, dropdowns y modales.
- Los botones de acción deben tener una única finalidad clara; evitar botones
  “Volver” duplicados.
- Las alertas “Sin profesores” y “Sin alumnos” deben conservar el formato de
  badge/burbuja utilizado por el turno y mantener contraste suficiente.

## Verificación mínima

Después de un cambio relevante:

1. Ejecutar `git diff --check`.
2. Ejecutar las pruebas acotadas del módulo si están disponibles.
3. Si hay Docker, ejecutar `python manage.py check` y la migración pendiente
   desde el servicio `django`.
4. Probar tanto la carga normal como la respuesta de error, especialmente en
   operaciones AJAX y modales.
5. Confirmar que los cambios respetan CUE-Anexo, ciclo, permisos y estados.
