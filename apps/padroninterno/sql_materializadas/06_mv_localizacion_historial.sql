-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_localizacion_historial desde la fuente Padron via dblink.
-- Reemplaza el historial del ojito de localizacion.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_historial_build;

CREATE MATERIALIZED VIEW padroninterno.mv_localizacion_historial_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        cl.id_localizacion::bigint AS id_localizacion,
        m.id_movimiento::bigint AS id_movimiento,
        COALESCE(l.anexo::text, '') AS anexo,
        COALESCE(e.cue::text, '') AS cue,
        COALESCE(BTRIM(tm.cod_tipo_mov::text), '') AS cod_tipo_mov,
        COALESCE(BTRIM(tm.descripcion), '') AS tipo_movimiento,
        COALESCE(BTRIM(est.descripcion), '') AS estado,
        COALESCE(BTRIM(est.descripcion), '') AS estado_nuevo,
        COALESCE(m.nro_instr_legal::text, '') AS nro_instr_legal,
        COALESCE(BTRIM(il.descripcion), '') AS instr_legal,
        COALESCE(BTRIM(mot.descripcion), '') AS motivo,
        COALESCE(m.fecha_inst_legal::text, '') AS fecha_inst_legal,
        COALESCE(m.fecha_vigencia::text, '') AS fecha_vigencia,
        m.fecha_vigencia AS fecha_vigencia_orden,
        COALESCE(BTRIM(m.observacion), '') AS observacion,
        COALESCE(NULLIF(BTRIM(u.nombre), ''), '') AS usuario
    FROM cambio_estado_localizacion cl
    JOIN localizacion l ON l.id_localizacion = cl.id_localizacion
    JOIN establecimiento e ON e.id_establecimiento = l.id_establecimiento
    JOIN movimiento m ON m.id_movimiento = cl.id_movimiento
    LEFT JOIN tipo_mov_tipo tm ON tm.c_tipo_mov = m.c_tipo_mov
    LEFT JOIN estado_tipo est ON est.c_estado = cl.c_estado
    LEFT JOIN instr_legal_tipo il ON il.c_instr_legal = m.c_instr_legal
    LEFT JOIN motivo_tipo mot ON mot.c_motivo = m.c_motivo
    LEFT JOIN usuario u ON u.id_usuario = m.id_usuario
    $sql$
) AS src(
    id_localizacion bigint,
    id_movimiento bigint,
    anexo text,
    cue text,
    cod_tipo_mov text,
    tipo_movimiento text,
    estado text,
    estado_nuevo text,
    nro_instr_legal text,
    instr_legal text,
    motivo text,
    fecha_inst_legal text,
    fecha_vigencia text,
    fecha_vigencia_orden timestamp without time zone,
    observacion text,
    usuario text
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_localizacion_historial_build IS
'Historial tabular de localizaciones para PadronInterno: una fila por combinacion real de localizacion, movimiento, estado y datos de cambio.';

CREATE UNIQUE INDEX mv_localizacion_historial_build_uidx
    ON padroninterno.mv_localizacion_historial_build (
        id_localizacion,
        id_movimiento,
        estado_nuevo,
        fecha_vigencia,
        fecha_inst_legal,
        nro_instr_legal,
        motivo,
        observacion
    );
CREATE INDEX mv_localizacion_historial_build_localizacion_idx
    ON padroninterno.mv_localizacion_historial_build (id_localizacion);
CREATE INDEX mv_localizacion_historial_build_orden_idx
    ON padroninterno.mv_localizacion_historial_build (id_localizacion, fecha_vigencia_orden DESC, id_movimiento DESC);

-- Validaciones de contenido y estructura.
SELECT 'mv_localizacion_historial_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizacion_historial_build;

SELECT 'mv_localizacion_historial_build_ids_padre_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizacion_historial_build
WHERE id_localizacion IS NULL;

SELECT 'mv_localizacion_historial_build_movimientos_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizacion_historial_build
WHERE id_movimiento IS NULL;

SELECT
    id_localizacion,
    id_movimiento,
    estado_nuevo,
    fecha_vigencia,
    fecha_inst_legal,
    nro_instr_legal,
    motivo,
    observacion,
    COUNT(*) AS repetidos
FROM padroninterno.mv_localizacion_historial_build
GROUP BY
    id_localizacion,
    id_movimiento,
    estado_nuevo,
    fecha_vigencia,
    fecha_inst_legal,
    nro_instr_legal,
    motivo,
    observacion
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_localizacion, id_movimiento, estado_nuevo, fecha_vigencia;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_localizacion_historial_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_localizacion_historial_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_localizacion_historial_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_localizacion_historial_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizacion_historial_build
WHERE id_localizacion = 1
ORDER BY fecha_vigencia_orden DESC, id_movimiento DESC;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_historial_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_historial RENAME TO mv_localizacion_historial_old;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_historial_uidx RENAME TO mv_localizacion_historial_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_historial_localizacion_idx RENAME TO mv_localizacion_historial_old_localizacion_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_historial_orden_idx RENAME TO mv_localizacion_historial_old_orden_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_localizacion_historial_build RENAME TO mv_localizacion_historial;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_historial_build_uidx RENAME TO mv_localizacion_historial_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_historial_build_localizacion_idx RENAME TO mv_localizacion_historial_localizacion_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_historial_build_orden_idx RENAME TO mv_localizacion_historial_orden_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_localizacion_historial IS
'Historial tabular de localizaciones para PadronInterno: una fila por combinacion real de localizacion, movimiento, estado y datos de cambio.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_historial_old;
*/
