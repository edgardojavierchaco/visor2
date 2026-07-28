-- Ejecutar manualmente en la base visualizador despues de una nueva bajada de datos en Padron.
-- Este archivo refresca solo vistas materializadas definitivas ya existentes.
-- No usa dblink directo, no contiene credenciales y no debe ejecutarse dentro de una transaccion explicita.
--
-- Requisitos:
--   - padroninterno.mv_localizaciones existe y tiene indice unico sobre id_localizacion.
--   - padroninterno.mv_establecimientos existe y tiene indice unico sobre id_establecimiento.
--   - padroninterno.mv_ofertaslocales existe y tiene indice unico sobre id_oferta_local.
--   - padroninterno.mv_responsables existe y tiene indice unico sobre id_responsable.
--   - padroninterno.mv_localizacion_domicilios existe y tiene indice unico sobre id_localizacion, id_domicilio, c_tipo_dom.
--   - padroninterno.mv_localizacion_historial existe y tiene indice unico sobre id_localizacion, id_movimiento, estado_nuevo, fecha_vigencia, fecha_inst_legal, nro_instr_legal, motivo, observacion.
--   - padroninterno.mv_establecimiento_historial existe y tiene indice unico sobre id_establecimiento, id_movimiento, estado_nuevo, fecha_vigencia, fecha_inst_legal, nro_instr_legal, motivo, observacion.
--   - padroninterno.mv_oferta_historial existe y tiene indice unico sobre id_oferta_local, id_movimiento, estado_nuevo, c_oferta, fecha_vigencia, fecha_instr_legal, motivo, observacion.
--   - padroninterno.mv_oferta_titulos existe y tiene indice unico sobre id_oferta_local, id_plan_estudio_local.

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_localizaciones;
ANALYZE padroninterno.mv_localizaciones;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_establecimientos;
ANALYZE padroninterno.mv_establecimientos;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_ofertaslocales;
ANALYZE padroninterno.mv_ofertaslocales;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_responsables;
ANALYZE padroninterno.mv_responsables;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_localizacion_domicilios;
ANALYZE padroninterno.mv_localizacion_domicilios;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_localizacion_historial;
ANALYZE padroninterno.mv_localizacion_historial;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_establecimiento_historial;
ANALYZE padroninterno.mv_establecimiento_historial;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_oferta_historial;
ANALYZE padroninterno.mv_oferta_historial;

REFRESH MATERIALIZED VIEW CONCURRENTLY padroninterno.mv_oferta_titulos;
ANALYZE padroninterno.mv_oferta_titulos;

-- Totales posteriores al refresh.
SELECT 'mv_localizaciones' AS vista, COUNT(*) AS total
FROM padroninterno.mv_localizaciones
UNION ALL
SELECT 'mv_establecimientos', COUNT(*)
FROM padroninterno.mv_establecimientos
UNION ALL
SELECT 'mv_ofertaslocales', COUNT(*)
FROM padroninterno.mv_ofertaslocales
UNION ALL
SELECT 'mv_responsables', COUNT(*)
FROM padroninterno.mv_responsables
UNION ALL
SELECT 'mv_localizacion_domicilios', COUNT(*)
FROM padroninterno.mv_localizacion_domicilios
UNION ALL
SELECT 'mv_localizacion_historial', COUNT(*)
FROM padroninterno.mv_localizacion_historial
UNION ALL
SELECT 'mv_establecimiento_historial', COUNT(*)
FROM padroninterno.mv_establecimiento_historial
UNION ALL
SELECT 'mv_oferta_historial', COUNT(*)
FROM padroninterno.mv_oferta_historial
UNION ALL
SELECT 'mv_oferta_titulos', COUNT(*)
FROM padroninterno.mv_oferta_titulos
ORDER BY vista;

-- IDs originales nulos.
SELECT 'mv_localizaciones' AS vista, COUNT(*) AS ids_nulos
FROM padroninterno.mv_localizaciones
WHERE id_localizacion IS NULL
UNION ALL
SELECT 'mv_establecimientos', COUNT(*)
FROM padroninterno.mv_establecimientos
WHERE id_establecimiento IS NULL
UNION ALL
SELECT 'mv_ofertaslocales', COUNT(*)
FROM padroninterno.mv_ofertaslocales
WHERE id_oferta_local IS NULL
UNION ALL
SELECT 'mv_responsables', COUNT(*)
FROM padroninterno.mv_responsables
WHERE id_responsable IS NULL
UNION ALL
SELECT 'mv_localizacion_domicilios', COUNT(*)
FROM padroninterno.mv_localizacion_domicilios
WHERE id_localizacion IS NULL
UNION ALL
SELECT 'mv_localizacion_historial', COUNT(*)
FROM padroninterno.mv_localizacion_historial
WHERE id_localizacion IS NULL
UNION ALL
SELECT 'mv_establecimiento_historial', COUNT(*)
FROM padroninterno.mv_establecimiento_historial
WHERE id_establecimiento IS NULL
UNION ALL
SELECT 'mv_oferta_historial', COUNT(*)
FROM padroninterno.mv_oferta_historial
WHERE id_oferta_local IS NULL
UNION ALL
SELECT 'mv_oferta_titulos', COUNT(*)
FROM padroninterno.mv_oferta_titulos
WHERE id_oferta_local IS NULL
ORDER BY vista;

-- Alias contractual id contra ID original.
SELECT 'mv_localizaciones' AS vista, COUNT(*) AS alias_id_distinto
FROM padroninterno.mv_localizaciones
WHERE id IS DISTINCT FROM id_localizacion
UNION ALL
SELECT 'mv_establecimientos', COUNT(*)
FROM padroninterno.mv_establecimientos
WHERE id IS DISTINCT FROM id_establecimiento
UNION ALL
SELECT 'mv_ofertaslocales', COUNT(*)
FROM padroninterno.mv_ofertaslocales
WHERE id IS DISTINCT FROM id_oferta_local
UNION ALL
SELECT 'mv_responsables', COUNT(*)
FROM padroninterno.mv_responsables
WHERE id IS DISTINCT FROM id_responsable
ORDER BY vista;

-- IDs originales duplicados. Debe devolver cero filas.
SELECT 'mv_localizaciones' AS vista, id_localizacion::text AS id, COUNT(*) AS repetidos
FROM padroninterno.mv_localizaciones
GROUP BY id_localizacion
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_establecimientos', id_establecimiento::text, COUNT(*)
FROM padroninterno.mv_establecimientos
GROUP BY id_establecimiento
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_ofertaslocales', id_oferta_local::text, COUNT(*)
FROM padroninterno.mv_ofertaslocales
GROUP BY id_oferta_local
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_responsables', id_responsable::text, COUNT(*)
FROM padroninterno.mv_responsables
GROUP BY id_responsable
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_localizacion_domicilios',
       id_localizacion::text || '|' || id_domicilio::text || '|' || c_tipo_dom::text,
       COUNT(*)
FROM padroninterno.mv_localizacion_domicilios
GROUP BY id_localizacion, id_domicilio, c_tipo_dom
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_localizacion_historial',
       id_localizacion::text || '|' || id_movimiento::text || '|' || estado_nuevo || '|' ||
       fecha_vigencia || '|' || fecha_inst_legal || '|' || nro_instr_legal || '|' ||
       motivo || '|' || observacion,
       COUNT(*)
FROM padroninterno.mv_localizacion_historial
GROUP BY id_localizacion, id_movimiento, estado_nuevo, fecha_vigencia, fecha_inst_legal, nro_instr_legal, motivo, observacion
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_establecimiento_historial',
       id_establecimiento::text || '|' || id_movimiento::text || '|' || estado_nuevo || '|' ||
       fecha_vigencia || '|' || fecha_inst_legal || '|' || nro_instr_legal || '|' ||
       motivo || '|' || observacion,
       COUNT(*)
FROM padroninterno.mv_establecimiento_historial
GROUP BY id_establecimiento, id_movimiento, estado_nuevo, fecha_vigencia, fecha_inst_legal, nro_instr_legal, motivo, observacion
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_oferta_historial',
       id_oferta_local::text || '|' || id_movimiento::text || '|' || estado_nuevo || '|' ||
       c_oferta || '|' || fecha_vigencia || '|' || fecha_instr_legal || '|' ||
       motivo || '|' || observacion,
       COUNT(*)
FROM padroninterno.mv_oferta_historial
GROUP BY id_oferta_local, id_movimiento, estado_nuevo, c_oferta, fecha_vigencia, fecha_instr_legal, motivo, observacion
HAVING COUNT(*) > 1
UNION ALL
SELECT 'mv_oferta_titulos',
       id_oferta_local::text || '|' || id_plan_estudio_local::text,
       COUNT(*)
FROM padroninterno.mv_oferta_titulos
GROUP BY id_oferta_local, id_plan_estudio_local
HAVING COUNT(*) > 1
ORDER BY vista, repetidos DESC, id;

-- Tamanio de datos, indices y total.
SELECT
    relname AS vista,
    pg_size_pretty(pg_relation_size(c.oid)) AS datos,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indices,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'padroninterno'
  AND relname IN (
      'mv_localizaciones',
      'mv_establecimientos',
      'mv_ofertaslocales',
      'mv_responsables',
      'mv_localizacion_domicilios',
      'mv_localizacion_historial',
      'mv_establecimiento_historial',
      'mv_oferta_historial',
      'mv_oferta_titulos'
  )
ORDER BY relname;

-- Integridad de auxiliares contra las 4 vistas principales.
SELECT 'domicilios_con_localizacion_inexistente' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizacion_domicilios d
LEFT JOIN padroninterno.mv_localizaciones l
  ON l.id_localizacion = d.id_localizacion
WHERE d.id_localizacion IS NOT NULL
  AND l.id_localizacion IS NULL
UNION ALL
SELECT 'historial_localizacion_con_localizacion_inexistente', COUNT(*)
FROM padroninterno.mv_localizacion_historial h
LEFT JOIN padroninterno.mv_localizaciones l
  ON l.id_localizacion = h.id_localizacion
WHERE h.id_localizacion IS NOT NULL
  AND l.id_localizacion IS NULL
UNION ALL
SELECT 'historial_establecimiento_con_establecimiento_inexistente', COUNT(*)
FROM padroninterno.mv_establecimiento_historial h
LEFT JOIN padroninterno.mv_establecimientos e
  ON e.id_establecimiento = h.id_establecimiento
WHERE h.id_establecimiento IS NOT NULL
  AND e.id_establecimiento IS NULL
UNION ALL
SELECT 'historial_oferta_con_oferta_inexistente', COUNT(*)
FROM padroninterno.mv_oferta_historial h
LEFT JOIN padroninterno.mv_ofertaslocales o
  ON o.id_oferta_local = h.id_oferta_local
WHERE h.id_oferta_local IS NOT NULL
  AND o.id_oferta_local IS NULL
UNION ALL
SELECT 'titulos_con_oferta_inexistente', COUNT(*)
FROM padroninterno.mv_oferta_titulos t
LEFT JOIN padroninterno.mv_ofertaslocales o
  ON o.id_oferta_local = t.id_oferta_local
WHERE t.id_oferta_local IS NOT NULL
  AND o.id_oferta_local IS NULL;

-- Integridad minima para navegacion cruzada.
SELECT 'localizaciones_sin_establecimiento_mv' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizaciones l
LEFT JOIN padroninterno.mv_establecimientos e
  ON e.id_establecimiento = l.id_establecimiento
WHERE l.id_establecimiento IS NOT NULL
  AND e.id_establecimiento IS NULL
UNION ALL
SELECT 'localizaciones_sin_responsable_mv', COUNT(*)
FROM padroninterno.mv_localizaciones l
LEFT JOIN padroninterno.mv_responsables r
  ON r.id_responsable = l.id_responsable
WHERE l.id_responsable IS NOT NULL
  AND l.id_responsable <> -2
  AND r.id_responsable IS NULL
UNION ALL
SELECT 'ofertas_sin_localizacion_mv', COUNT(*)
FROM padroninterno.mv_ofertaslocales o
LEFT JOIN padroninterno.mv_localizaciones l
  ON l.id_localizacion = o.id_localizacion
WHERE o.id_localizacion IS NOT NULL
  AND l.id_localizacion IS NULL
UNION ALL
SELECT 'ofertas_sin_establecimiento_mv', COUNT(*)
FROM padroninterno.mv_ofertaslocales o
LEFT JOIN padroninterno.mv_establecimientos e
  ON e.id_establecimiento = o.id_establecimiento
WHERE o.id_establecimiento IS NOT NULL
  AND e.id_establecimiento IS NULL
UNION ALL
SELECT 'ofertas_sin_responsable_mv', COUNT(*)
FROM padroninterno.mv_ofertaslocales o
LEFT JOIN padroninterno.mv_responsables r
  ON r.id_responsable = o.id_responsable
WHERE o.id_responsable IS NOT NULL
  AND o.id_responsable <> -2
  AND r.id_responsable IS NULL;

-- Consultas simples de navegacion cruzada.
SELECT
    e.id_establecimiento,
    e.cue,
    e.nombre AS establecimiento,
    l.id_localizacion,
    l.anexo,
    l.nombre AS localizacion
FROM padroninterno.mv_establecimientos e
JOIN padroninterno.mv_localizaciones l
  ON l.id_establecimiento = e.id_establecimiento
ORDER BY e.cue, l.anexo DESC, l.id_localizacion
LIMIT 20;

SELECT
    l.id_localizacion,
    l.cue,
    l.anexo,
    l.nombre AS localizacion,
    o.id_oferta_local,
    o.tipo_oferta,
    o.estado
FROM padroninterno.mv_localizaciones l
JOIN padroninterno.mv_ofertaslocales o
  ON o.id_localizacion = l.id_localizacion
ORDER BY l.cue, l.anexo DESC, o.c_oferta, o.id_oferta_local
LIMIT 20;

SELECT
    r.id_responsable,
    r.apellido,
    r.nombre,
    COUNT(DISTINCT l.id_localizacion) AS localizaciones,
    COUNT(DISTINCT e.id_establecimiento) AS establecimientos
FROM padroninterno.mv_responsables r
LEFT JOIN padroninterno.mv_localizaciones l
  ON l.id_responsable = r.id_responsable
LEFT JOIN padroninterno.mv_establecimientos e
  ON e.id_responsable = r.id_responsable
GROUP BY r.id_responsable, r.apellido, r.nombre
HAVING COUNT(DISTINCT l.id_localizacion) > 0
    OR COUNT(DISTINCT e.id_establecimiento) > 0
ORDER BY localizaciones DESC, establecimientos DESC, r.apellido, r.nombre
LIMIT 20;
