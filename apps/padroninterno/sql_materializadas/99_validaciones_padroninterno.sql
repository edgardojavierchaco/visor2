-- Ejecutar manualmente en la base visualizador despues de promover las 9 vistas definitivas.
-- Este archivo no usa dblink ni credenciales.
--
-- Vistas esperadas:
--   padroninterno.mv_localizaciones
--   padroninterno.mv_establecimientos
--   padroninterno.mv_ofertaslocales
--   padroninterno.mv_responsables
--   padroninterno.mv_localizacion_domicilios
--   padroninterno.mv_localizacion_historial
--   padroninterno.mv_establecimiento_historial
--   padroninterno.mv_oferta_historial
--   padroninterno.mv_oferta_titulos

-- Existencia de vistas materializadas esperadas.
SELECT esperada.vista,
       CASE WHEN actual.vista IS NULL THEN 'NO_EXISTE' ELSE 'EXISTE' END AS estado
FROM (
    VALUES
        ('mv_localizaciones'),
        ('mv_establecimientos'),
        ('mv_ofertaslocales'),
        ('mv_responsables'),
        ('mv_localizacion_domicilios'),
        ('mv_localizacion_historial'),
        ('mv_establecimiento_historial'),
        ('mv_oferta_historial'),
        ('mv_oferta_titulos')
) AS esperada(vista)
LEFT JOIN (
    SELECT c.relname AS vista
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'padroninterno'
) actual
  ON actual.vista = esperada.vista
ORDER BY esperada.vista;

-- Totales.
SELECT 'mv_localizaciones' AS vista, COUNT(*) AS total FROM padroninterno.mv_localizaciones
UNION ALL
SELECT 'mv_establecimientos', COUNT(*) FROM padroninterno.mv_establecimientos
UNION ALL
SELECT 'mv_ofertaslocales', COUNT(*) FROM padroninterno.mv_ofertaslocales
UNION ALL
SELECT 'mv_responsables', COUNT(*) FROM padroninterno.mv_responsables
UNION ALL
SELECT 'mv_localizacion_domicilios', COUNT(*) FROM padroninterno.mv_localizacion_domicilios
UNION ALL
SELECT 'mv_localizacion_historial', COUNT(*) FROM padroninterno.mv_localizacion_historial
UNION ALL
SELECT 'mv_establecimiento_historial', COUNT(*) FROM padroninterno.mv_establecimiento_historial
UNION ALL
SELECT 'mv_oferta_historial', COUNT(*) FROM padroninterno.mv_oferta_historial
UNION ALL
SELECT 'mv_oferta_titulos', COUNT(*) FROM padroninterno.mv_oferta_titulos
ORDER BY vista;

-- IDs nulos.
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

-- IDs duplicados.
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

-- Columnas y tipos.
SELECT table_name, ordinal_position, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name IN (
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
ORDER BY table_name, ordinal_position;

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

-- Integridad de navegacion cruzada entre las 4 vistas base.
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

-- EXPLAIN de consultas tipicas de listados.
EXPLAIN
SELECT *
FROM padroninterno.mv_establecimientos
ORDER BY cue, id_establecimiento
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_establecimientos
WHERE estado = 'Activo';

EXPLAIN
SELECT *
FROM padroninterno.mv_localizaciones
ORDER BY cue, anexo DESC, id_localizacion
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_localizaciones
WHERE estado = 'Activo';

EXPLAIN
SELECT *
FROM padroninterno.mv_ofertaslocales
ORDER BY cue, anexo, id_oferta_local
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_ofertaslocales
WHERE estado = 'Activo';

EXPLAIN
SELECT *
FROM padroninterno.mv_responsables
ORDER BY apellido, nombre, id_responsable
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_responsables
WHERE tipo_documento <> '';

-- EXPLAIN de navegacion y ojitos entre vistas.
EXPLAIN
SELECT *
FROM padroninterno.mv_localizaciones
WHERE id_establecimiento = 1
ORDER BY cue, anexo DESC, id_localizacion;

EXPLAIN
SELECT *
FROM padroninterno.mv_ofertaslocales
WHERE id_localizacion = 1
ORDER BY c_oferta, id_oferta_local;

EXPLAIN
SELECT *
FROM padroninterno.mv_ofertaslocales
WHERE id_establecimiento = 1
ORDER BY c_oferta, anexo, id_oferta_local;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizaciones
WHERE id_responsable = 1
ORDER BY cue, anexo DESC, id_localizacion;

EXPLAIN
SELECT *
FROM padroninterno.mv_establecimientos
WHERE id_responsable = 1
ORDER BY cue, id_establecimiento;

-- EXPLAIN de consultas tipicas por ID padre en auxiliares.
EXPLAIN
SELECT *
FROM padroninterno.mv_localizacion_domicilios
WHERE id_localizacion = 1
ORDER BY orden, c_tipo_dom, id_domicilio;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizacion_domicilios
WHERE id_domicilio = 1
ORDER BY id_localizacion, orden, c_tipo_dom;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizacion_historial
WHERE id_localizacion = 1
ORDER BY fecha_vigencia_orden DESC, id_movimiento DESC;

EXPLAIN
SELECT *
FROM padroninterno.mv_establecimiento_historial
WHERE id_establecimiento = 1
ORDER BY fecha_vigencia_orden DESC, id_movimiento DESC;

EXPLAIN
SELECT *
FROM padroninterno.mv_oferta_historial
WHERE id_oferta_local = 1
ORDER BY fecha_vigencia_orden DESC, id_movimiento DESC;

EXPLAIN
SELECT *
FROM padroninterno.mv_oferta_titulos
WHERE id_oferta_local = 1
ORDER BY titulo, id_plan_estudio_local;

EXPLAIN
SELECT *
FROM padroninterno.mv_oferta_titulos
WHERE id_plan_estudio_local = 1
LIMIT 1;

-- Este archivo solo valida.
-- Para futuras bajadas de datos en Padron usar:
--   10_refresh_materializadas_padroninterno.sql

-- Validacion final de indices unicos usados por REFRESH CONCURRENTLY.
SELECT esperada.vista,
       esperada.indice,
       CASE WHEN i.indexname IS NULL THEN 'NO_EXISTE' ELSE 'EXISTE' END AS estado
FROM (
    VALUES
        ('mv_localizaciones', 'mv_localizaciones_uidx'),
        ('mv_establecimientos', 'mv_establecimientos_uidx'),
        ('mv_ofertaslocales', 'mv_ofertaslocales_uidx'),
        ('mv_responsables', 'mv_responsables_uidx'),
        ('mv_localizacion_domicilios', 'mv_localizacion_domicilios_uidx'),
        ('mv_localizacion_historial', 'mv_localizacion_historial_uidx'),
        ('mv_establecimiento_historial', 'mv_establecimiento_historial_uidx'),
        ('mv_oferta_historial', 'mv_oferta_historial_uidx'),
        ('mv_oferta_titulos', 'mv_oferta_titulos_uidx')
) AS esperada(vista, indice)
LEFT JOIN pg_indexes i
  ON i.schemaname = 'padroninterno'
 AND i.tablename = esperada.vista
 AND i.indexname = esperada.indice
 AND i.indexdef LIKE 'CREATE UNIQUE INDEX%'
ORDER BY esperada.vista;

SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'padroninterno'
  AND tablename IN (
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
ORDER BY tablename, indexname;
