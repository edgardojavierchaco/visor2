-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_localizacion_domicilios desde la fuente Padron via dblink.
-- Reemplaza los domicilios completos del ojito de localizacion.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_domicilios_build;

CREATE MATERIALIZED VIEW padroninterno.mv_localizacion_domicilios_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        ld.id_localizacion::bigint AS id_localizacion,
        ld.id_domicilio::bigint AS id_domicilio,
        ld.c_tipo_dom::integer AS c_tipo_dom,
        COALESCE(BTRIM(dt.descripcion), '') AS tipo_domicilio,
        COALESCE(BTRIM(d.calle), '') AS calle,
        COALESCE(BTRIM(d.nro), '') AS nro,
        COALESCE(BTRIM(d.barrio), '') AS barrio,
        COALESCE(BTRIM(d.referencia), '') AS referencia,
        COALESCE(BTRIM(d.cod_postal), '') AS cod_postal,
        COALESCE(BTRIM(d.cui), '') AS cui,
        COALESCE(BTRIM(d.calle_fondo), '') AS calle_fondo,
        COALESCE(BTRIM(d.calle_derecha), '') AS calle_derecha,
        COALESCE(BTRIM(d.calle_izquierda), '') AS calle_izquierda,
        COALESCE(d.fecha_actualizacion::text, '') AS fecha_actualizacion,
        COALESCE(BTRIM(lt.nombre), '') AS localidad_nombre,
        COALESCE(BTRIM(dept.nombre), '') AS departamento_nombre,
        CASE WHEN ld.c_tipo_dom = 1 THEN true ELSE false END AS es_principal,
        CASE WHEN ld.c_tipo_dom = 1 THEN 0 ELSE 1 END::integer AS orden
    FROM localizacion_domicilio ld
    JOIN domicilio d ON d.id_domicilio = ld.id_domicilio
    LEFT JOIN domicilio_tipo dt ON dt.c_tipo_dom = ld.c_tipo_dom
    LEFT JOIN localidad_tipo lt ON lt.c_localidad = d.c_localidad
    LEFT JOIN departamento_tipo dept ON dept.c_departamento = lt.c_departamento
    $sql$
) AS src(
    id_localizacion bigint,
    id_domicilio bigint,
    c_tipo_dom integer,
    tipo_domicilio text,
    calle text,
    nro text,
    barrio text,
    referencia text,
    cod_postal text,
    cui text,
    calle_fondo text,
    calle_derecha text,
    calle_izquierda text,
    fecha_actualizacion text,
    localidad_nombre text,
    departamento_nombre text,
    es_principal boolean,
    orden integer
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_localizacion_domicilios_build IS
'Domicilios tabulares de localizaciones para PadronInterno: una fila por relacion real id_localizacion, id_domicilio y c_tipo_dom.';

CREATE UNIQUE INDEX mv_localizacion_domicilios_build_uidx
    ON padroninterno.mv_localizacion_domicilios_build (id_localizacion, id_domicilio, c_tipo_dom);
CREATE INDEX mv_localizacion_domicilios_build_localizacion_idx
    ON padroninterno.mv_localizacion_domicilios_build (id_localizacion);
CREATE INDEX mv_localizacion_domicilios_build_domicilio_idx
    ON padroninterno.mv_localizacion_domicilios_build (id_domicilio);
CREATE INDEX mv_localizacion_domicilios_build_orden_idx
    ON padroninterno.mv_localizacion_domicilios_build (id_localizacion, orden, c_tipo_dom, id_domicilio);

-- Validaciones de contenido y estructura.
SELECT 'mv_localizacion_domicilios_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizacion_domicilios_build;

SELECT 'mv_localizacion_domicilios_build_ids_padre_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizacion_domicilios_build
WHERE id_localizacion IS NULL;

SELECT 'mv_localizacion_domicilios_build_ids_domicilio_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizacion_domicilios_build
WHERE id_domicilio IS NULL;

SELECT id_localizacion, id_domicilio, c_tipo_dom, COUNT(*) AS repetidos
FROM padroninterno.mv_localizacion_domicilios_build
GROUP BY id_localizacion, id_domicilio, c_tipo_dom
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_localizacion, id_domicilio, c_tipo_dom;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_localizacion_domicilios_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_localizacion_domicilios_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_localizacion_domicilios_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_localizacion_domicilios_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizacion_domicilios_build
WHERE id_localizacion = 1
ORDER BY orden, c_tipo_dom, id_domicilio;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizacion_domicilios_build
WHERE id_domicilio = 1
ORDER BY id_localizacion, orden, c_tipo_dom;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_domicilios_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_domicilios RENAME TO mv_localizacion_domicilios_old;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_uidx RENAME TO mv_localizacion_domicilios_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_localizacion_idx RENAME TO mv_localizacion_domicilios_old_localizacion_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_domicilio_idx RENAME TO mv_localizacion_domicilios_old_domicilio_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_orden_idx RENAME TO mv_localizacion_domicilios_old_orden_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_localizacion_domicilios_build RENAME TO mv_localizacion_domicilios;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_build_uidx RENAME TO mv_localizacion_domicilios_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_build_localizacion_idx RENAME TO mv_localizacion_domicilios_localizacion_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_build_domicilio_idx RENAME TO mv_localizacion_domicilios_domicilio_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizacion_domicilios_build_orden_idx RENAME TO mv_localizacion_domicilios_orden_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_localizacion_domicilios IS
'Domicilios tabulares de localizaciones para PadronInterno: una fila por relacion real id_localizacion, id_domicilio y c_tipo_dom.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizacion_domicilios_old;
*/
