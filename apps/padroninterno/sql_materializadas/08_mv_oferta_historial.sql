-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_oferta_historial desde la fuente Padron via dblink.
-- Reemplaza el historial del ojito de oferta local.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_historial_build;

CREATE MATERIALIZED VIEW padroninterno.mv_oferta_historial_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        ce.id_oferta_local::bigint AS id_oferta_local,
        m.id_movimiento::bigint AS id_movimiento,
        COALESCE(BTRIM(est.descripcion), '') AS estado_movimiento,
        COALESCE(BTRIM(est.descripcion), '') AS estado,
        COALESCE(BTRIM(est.descripcion), '') AS estado_nuevo,
        COALESCE(ol.c_oferta::text, '') AS c_oferta,
        COALESCE(BTRIM(ot.descripcion), '') AS carrera,
        COALESCE(BTRIM(ot.descripcion), '') AS oferta_local,
        COALESCE(BTRIM(ot.descripcion), '') AS oferta_nueva,
        COALESCE(m.fecha_inst_legal::text, '') AS fecha_instr_legal,
        COALESCE(m.fecha_vigencia::text, '') AS fecha_vigencia,
        m.fecha_vigencia AS fecha_vigencia_orden,
        COALESCE(BTRIM(m.observacion), '') AS observacion,
        CASE
            WHEN COALESCE(m.nro_instr_legal::text, '') <> ''
             AND COALESCE(BTRIM(il.descripcion), '') <> '' THEN
                '(' || m.nro_instr_legal::text || ') ' || BTRIM(il.descripcion)
            WHEN COALESCE(m.nro_instr_legal::text, '') <> '' THEN
                m.nro_instr_legal::text
            ELSE
                COALESCE(BTRIM(il.descripcion), '')
        END AS instr_legal,
        COALESCE(BTRIM(mot.descripcion), '') AS motivo,
        COALESCE(
            NULLIF(
                CONCAT_WS(
                    ' - ',
                    NULLIF(m.id_movimiento::text, ''),
                    COALESCE(
                        NULLIF(BTRIM(tm.cod_tipo_mov::text), ''),
                        NULLIF(m.c_tipo_mov::text, '')
                    ),
                    NULLIF(COALESCE(BTRIM(tm.descripcion), ''), '')
                ),
                ''
            ),
            COALESCE(m.id_movimiento::text, '')
        ) AS movimiento,
        COALESCE(NULLIF(BTRIM(u.nombre), ''), COALESCE(m.id_usuario::text, '')) AS usuario
    FROM cambio_estado_oferta_local ce
    JOIN movimiento m ON ce.id_movimiento = m.id_movimiento
    JOIN oferta_local ol ON ce.id_oferta_local = ol.id_oferta_local
    JOIN oferta_tipo ot ON ol.c_oferta = ot.c_oferta
    LEFT JOIN estado_tipo est ON ce.c_estado = est.c_estado
    LEFT JOIN tipo_mov_tipo tm ON m.c_tipo_mov = tm.c_tipo_mov
    LEFT JOIN instr_legal_tipo il ON m.c_instr_legal = il.c_instr_legal
    LEFT JOIN motivo_tipo mot ON m.c_motivo = mot.c_motivo
    LEFT JOIN usuario u ON u.id_usuario = m.id_usuario
    $sql$
) AS src(
    id_oferta_local bigint,
    id_movimiento bigint,
    estado_movimiento text,
    estado text,
    estado_nuevo text,
    c_oferta text,
    carrera text,
    oferta_local text,
    oferta_nueva text,
    fecha_instr_legal text,
    fecha_vigencia text,
    fecha_vigencia_orden timestamp without time zone,
    observacion text,
    instr_legal text,
    motivo text,
    movimiento text,
    usuario text
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_oferta_historial_build IS
'Historial tabular de ofertas locales para PadronInterno: una fila por combinacion real de oferta local, movimiento, estado, oferta y datos de cambio.';

CREATE UNIQUE INDEX mv_oferta_historial_build_uidx
    ON padroninterno.mv_oferta_historial_build (
        id_oferta_local,
        id_movimiento,
        estado_nuevo,
        c_oferta,
        fecha_vigencia,
        fecha_instr_legal,
        motivo,
        observacion
    );
CREATE INDEX mv_oferta_historial_build_oferta_idx
    ON padroninterno.mv_oferta_historial_build (id_oferta_local);
CREATE INDEX mv_oferta_historial_build_orden_idx
    ON padroninterno.mv_oferta_historial_build (id_oferta_local, fecha_vigencia_orden DESC, id_movimiento DESC);

-- Validaciones de contenido y estructura.
SELECT 'mv_oferta_historial_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_oferta_historial_build;

SELECT 'mv_oferta_historial_build_ids_padre_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_oferta_historial_build
WHERE id_oferta_local IS NULL;

SELECT 'mv_oferta_historial_build_movimientos_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_oferta_historial_build
WHERE id_movimiento IS NULL;

SELECT
    id_oferta_local,
    id_movimiento,
    estado_nuevo,
    c_oferta,
    fecha_vigencia,
    fecha_instr_legal,
    motivo,
    observacion,
    COUNT(*) AS repetidos
FROM padroninterno.mv_oferta_historial_build
GROUP BY
    id_oferta_local,
    id_movimiento,
    estado_nuevo,
    c_oferta,
    fecha_vigencia,
    fecha_instr_legal,
    motivo,
    observacion
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_oferta_local, id_movimiento, estado_nuevo, fecha_vigencia;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_oferta_historial_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_oferta_historial_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_oferta_historial_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_oferta_historial_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_oferta_historial_build
WHERE id_oferta_local = 1
ORDER BY fecha_vigencia_orden DESC, id_movimiento DESC;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_historial_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_historial RENAME TO mv_oferta_historial_old;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_historial_uidx RENAME TO mv_oferta_historial_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_historial_oferta_idx RENAME TO mv_oferta_historial_old_oferta_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_historial_orden_idx RENAME TO mv_oferta_historial_old_orden_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_oferta_historial_build RENAME TO mv_oferta_historial;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_historial_build_uidx RENAME TO mv_oferta_historial_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_historial_build_oferta_idx RENAME TO mv_oferta_historial_oferta_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_historial_build_orden_idx RENAME TO mv_oferta_historial_orden_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_oferta_historial IS
'Historial tabular de ofertas locales para PadronInterno: una fila por combinacion real de oferta local, movimiento, estado, oferta y datos de cambio.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_historial_old;
*/
