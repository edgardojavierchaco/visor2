-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_responsables desde la fuente Padron via dblink.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_responsables_build;

CREATE MATERIALIZED VIEW padroninterno.mv_responsables_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        r.id_responsable::bigint AS id,
        r.id_responsable::bigint AS id_responsable,
        COALESCE(est_ids.ids, '') AS establecimientos_ids,
        COALESCE(loc_ids.ids, '') AS localizaciones_ids,
        -- Campo extra no contractual para navegacion futura; views_responsables.py no lo consume hoy.
        COALESCE(oferta_ids.ids, '') AS ofertas_ids,
        COALESCE(BTRIM(r.apellido), '') AS apellido,
        COALESCE(BTRIM(r.nombre), '') AS nombre,
        COALESCE(BTRIM(tdt.descripcion), '') AS tipo_documento,
        COALESCE(r.nro_documento::text, '') AS nro_documento,
        COALESCE(BTRIM(ot.descripcion), '') AS nacionalidad,
        COALESCE(r.fecha_nacimiento::text, '') AS fecha_nacimiento,
        COALESCE(BTRIM(st.descripcion), '') AS sexo,
        COALESCE(BTRIM(r.telefono), '') AS telefono,
        COALESCE(BTRIM(r.email), '') AS email,
        COALESCE(BTRIM(r.cuil_cuit), '') AS cuil_cuit,
        COALESCE(r.fecha_actualizacion::text, '') AS fecha_actualizacion,
        COALESCE(BTRIM(locs.cueanexo), '') AS cueanexo,
        COALESCE(BTRIM(locs.codigo_jurisdiccional), '') AS codigo_jurisdiccional,
        LOWER(
            CONCAT_WS(
                ' ',
                r.apellido,
                r.nombre,
                tdt.descripcion,
                r.nro_documento::text,
                r.telefono,
                st.descripcion,
                r.email,
                r.cuil_cuit,
                locs.cueanexo,
                locs.codigo_jurisdiccional
            )
        ) AS search_text
    FROM responsable r
    LEFT JOIN tipo_documento_tipo tdt
      ON tdt.c_tipo_documento = r.c_tipo_documento
    LEFT JOIN sexo_tipo st
      ON st.c_sexo = r.c_sexo
    LEFT JOIN origen_tipo ot
      ON ot.c_origen = r.c_nacionalidad
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(e.id_establecimiento::text, ',' ORDER BY e.cue::text, e.id_establecimiento) AS ids
        FROM establecimiento e
        WHERE e.id_responsable = r.id_responsable
    ) est_ids ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(l.id_localizacion::text, ',' ORDER BY e.cue::text, COALESCE(l.anexo::text, '') DESC, l.id_localizacion) AS ids
        FROM localizacion l
        JOIN establecimiento e ON e.id_establecimiento = l.id_establecimiento
        WHERE l.id_responsable = r.id_responsable
    ) loc_ids ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(id_oferta_local::text, ',' ORDER BY cue, anexo DESC, id_oferta_local) AS ids
        FROM (
            SELECT DISTINCT
                ol.id_oferta_local,
                e.cue::text AS cue,
                COALESCE(l.anexo::text, '') AS anexo
            FROM localizacion l
            JOIN establecimiento e ON e.id_establecimiento = l.id_establecimiento
            JOIN oferta_local ol ON ol.id_localizacion = l.id_localizacion
            WHERE l.id_responsable = r.id_responsable
               OR ol.id_responsable = r.id_responsable
        ) ofertas_responsable
    ) oferta_ids ON TRUE
    LEFT JOIN LATERAL (
        SELECT
            STRING_AGG(
                e.cue::text || LPAD(COALESCE(l.anexo::text, ''), 2, '0'),
                ', '
                ORDER BY e.cue::text ASC, COALESCE(l.anexo::text, '') DESC
            ) AS cueanexo,
            STRING_AGG(
                NULLIF(BTRIM(l.codigo_jurisdiccional), ''),
                ', '
                ORDER BY e.cue::text ASC, COALESCE(l.anexo::text, '') DESC
            ) AS codigo_jurisdiccional
        FROM localizacion l
        JOIN establecimiento e
          ON e.id_establecimiento = l.id_establecimiento
        WHERE l.id_responsable = r.id_responsable
    ) locs ON TRUE
    $sql$
) AS src(
    id bigint,
    id_responsable bigint,
    establecimientos_ids text,
    localizaciones_ids text,
    ofertas_ids text,
    apellido text,
    nombre text,
    tipo_documento text,
    nro_documento text,
    nacionalidad text,
    fecha_nacimiento text,
    sexo text,
    telefono text,
    email text,
    cuil_cuit text,
    fecha_actualizacion text,
    cueanexo text,
    codigo_jurisdiccional text,
    search_text text
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_responsables_build IS
'Base de responsables para PadronInterno: una fila por id_responsable, con columnas de listado, detalle propio, filtros, Excel y claves hacia establecimientos, localizaciones y ofertas.';

CREATE UNIQUE INDEX mv_responsables_build_uidx
    ON padroninterno.mv_responsables_build (id_responsable);
CREATE INDEX mv_responsables_build_documento_idx
    ON padroninterno.mv_responsables_build (nro_documento);
CREATE INDEX mv_responsables_build_cuil_idx
    ON padroninterno.mv_responsables_build (cuil_cuit);
CREATE INDEX mv_responsables_build_tipo_documento_idx
    ON padroninterno.mv_responsables_build (tipo_documento);
CREATE INDEX mv_responsables_build_sexo_idx
    ON padroninterno.mv_responsables_build (sexo);
CREATE INDEX mv_responsables_build_apellido_nombre_idx
    ON padroninterno.mv_responsables_build ((LOWER(apellido)), (LOWER(nombre)));

-- Validaciones de contenido y estructura.
SELECT 'mv_responsables_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_responsables_build;

SELECT 'mv_responsables_build_ids_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_responsables_build
WHERE id_responsable IS NULL;

SELECT id_responsable, COUNT(*) AS repetidos
FROM padroninterno.mv_responsables_build
GROUP BY id_responsable
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_responsable;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_responsables_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_responsables_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_responsables_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_responsables_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_responsables_build
ORDER BY apellido, nombre, id_responsable
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_responsables_build
WHERE tipo_documento <> '';

EXPLAIN
SELECT *
FROM padroninterno.mv_responsables_build
WHERE nro_documento = '1'
ORDER BY apellido, nombre, id_responsable;

EXPLAIN
SELECT *
FROM padroninterno.mv_responsables_build
WHERE LOWER(apellido) LIKE '%gonzalez%'
ORDER BY apellido, nombre, id_responsable
LIMIT 20;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_responsables_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_responsables RENAME TO mv_responsables_old;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_uidx RENAME TO mv_responsables_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_documento_idx RENAME TO mv_responsables_old_documento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_cuil_idx RENAME TO mv_responsables_old_cuil_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_tipo_documento_idx RENAME TO mv_responsables_old_tipo_documento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_sexo_idx RENAME TO mv_responsables_old_sexo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_apellido_nombre_idx RENAME TO mv_responsables_old_apellido_nombre_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_responsables_build RENAME TO mv_responsables;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_build_uidx RENAME TO mv_responsables_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_build_documento_idx RENAME TO mv_responsables_documento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_build_cuil_idx RENAME TO mv_responsables_cuil_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_build_tipo_documento_idx RENAME TO mv_responsables_tipo_documento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_build_sexo_idx RENAME TO mv_responsables_sexo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_responsables_build_apellido_nombre_idx RENAME TO mv_responsables_apellido_nombre_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_responsables IS
'Base de responsables para PadronInterno: una fila por id_responsable, con columnas de listado, detalle propio, filtros, Excel y claves hacia establecimientos, localizaciones y ofertas.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_responsables_old;
*/
