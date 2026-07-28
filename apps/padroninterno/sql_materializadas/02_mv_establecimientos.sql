-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_establecimientos desde la fuente Padron via dblink.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_establecimientos_build;

CREATE MATERIALIZED VIEW padroninterno.mv_establecimientos_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        ve.id_establecimiento::bigint AS id,
        ve.id_establecimiento::bigint AS id_establecimiento,
        ve.id_responsable::bigint AS id_responsable,
        COALESCE(loc_ids.ids, '') AS localizaciones_ids,
        COALESCE(oferta_ids.ids, '') AS ofertas_ids,
        COALESCE(BTRIM(ve.cue::text), '') AS cue,
        COALESCE(ve.cantidad_localizaciones, 0)::integer AS cantidad_localizaciones,
        COALESCE(BTRIM(ve.codigo_jurisdiccional_sede), '') AS codigo_jurisdiccional,
        COALESCE(BTRIM(ve.codigo_jurisdiccional_sede), '') AS codigo_jurisdiccional_sede,
        COALESCE(BTRIM(ve.nombre), '') AS nombre,
        COALESCE(BTRIM(ve.sector), '') AS sector,
        COALESCE(BTRIM(ve.dependencia), '') AS dependencia,
        COALESCE(BTRIM(ve.confesional), '') AS confesional,
        COALESCE(BTRIM(ve.arancelado), '') AS arancelado,
        COALESCE(BTRIM(ve.categoria), '') AS categoria,
        COALESCE(BTRIM(ve.estado), '') AS estado,
        COALESCE(BTRIM(ve.localidad_sede), '') AS localidad,
        COALESCE(BTRIM(ve.localidad_sede), '') AS localidad_sede,
        COALESCE(BTRIM(ve.departamento_sede), '') AS departamento,
        COALESCE(BTRIM(ve.departamento_sede), '') AS departamento_sede,
        COALESCE(BTRIM(ve.calle_sede), '') AS calle_sede,
        COALESCE(BTRIM(ve.nro_sede), '') AS nro_sede,
        COALESCE(BTRIM(ve.referencia_sede), '') AS referencia_sede,
        COALESCE(BTRIM(ve.cod_postal_sede), '') AS cod_postal_sede,
        COALESCE(ve.fecha_creacion::text, '') AS fecha_creacion,
        COALESCE(ve.fecha_alta::text, '') AS fecha_alta,
        COALESCE(ve.fecha_baja::text, '') AS fecha_baja,
        COALESCE(ve.fecha_actualizacion::text, '') AS fecha_actualizacion,
        COALESCE(BTRIM(ve.responsable_apellido), '') AS responsable_apellido,
        COALESCE(BTRIM(ve.responsable_nombre), '') AS responsable_nombre,
        COALESCE(ve.documento_responsable::text, '') AS documento_responsable,
        BTRIM(
            CONCAT(
                COALESCE(ve.responsable_apellido, ''),
                CASE
                    WHEN COALESCE(ve.responsable_nombre, '') <> ''
                     AND COALESCE(ve.responsable_apellido, '') <> ''
                        THEN ', ' || ve.responsable_nombre
                    ELSE COALESCE(ve.responsable_nombre, '')
                END,
                CASE
                    WHEN ve.documento_responsable IS NOT NULL
                        THEN '(' || ve.documento_responsable::text || ')'
                    ELSE ''
                END
            )
        ) AS director,
        COALESCE(BTRIM(otipos.tipo_ofertas), '') AS tipo_ofertas,
        COALESCE(BTRIM(est_obs.valor), '') AS observaciones,
        COALESCE(BTRIM(ve.cp_numeroestablecimiento), '') AS nro_establecimiento,
        COALESCE(BTRIM(ve.cp_numeroestablecimiento), '') AS cp_numeroestablecimiento,
        COALESCE(BTRIM(CASE
            WHEN POSITION('-' IN ve.cp_est_tipo_ed) > 0
                THEN SUBSTRING(ve.cp_est_tipo_ed FROM POSITION('-' IN ve.cp_est_tipo_ed) + 1)
            ELSE ve.cp_est_tipo_ed
        END), '') AS tipo_educacion,
        COALESCE(BTRIM(ve.cp_est_tipo_ed), '') AS cp_est_tipo_ed,
        COALESCE(BTRIM(CASE
            WHEN POSITION('-' IN ve.cp_est_nivel) > 0
                THEN SUBSTRING(ve.cp_est_nivel FROM POSITION('-' IN ve.cp_est_nivel) + 1)
            ELSE ve.cp_est_nivel
        END), '') AS nivel,
        COALESCE(BTRIM(ve.cp_est_nivel), '') AS cp_est_nivel,
        COALESCE(BTRIM(CASE
            WHEN POSITION('-' IN ve.cp_est_cargo_director) > 0
                THEN SUBSTRING(ve.cp_est_cargo_director FROM POSITION('-' IN ve.cp_est_cargo_director) + 1)
            ELSE ve.cp_est_cargo_director
        END), '') AS cargo_director,
        COALESCE(BTRIM(ve.cp_est_cargo_director), '') AS cp_est_cargo_director,
        COALESCE(BTRIM(ve.cp_est_fecha_inst_legal), '') AS fecha_inst_legal,
        COALESCE(BTRIM(ve.cp_est_fecha_inst_legal), '') AS cp_est_fecha_inst_legal,
        COALESCE(BTRIM(ve.cp_est_nro_inst_legal), '') AS nro_inst_legal,
        COALESCE(BTRIM(ve.cp_est_nro_inst_legal), '') AS cp_est_nro_inst_legal,
        COALESCE(BTRIM(ve.cp_est_anio_inst_legal), '') AS anio_creacion,
        COALESCE(BTRIM(ve.cp_est_anio_inst_legal), '') AS cp_est_anio_inst_legal,
        COALESCE(BTRIM(CASE
            WHEN POSITION('-' IN ve.cp_est_descrip_inst_legal) > 0
                THEN SUBSTRING(ve.cp_est_descrip_inst_legal FROM 1 FOR POSITION('-' IN ve.cp_est_descrip_inst_legal) - 1)
            ELSE ve.cp_est_descrip_inst_legal
        END), '') AS descrip_inst_legal,
        COALESCE(BTRIM(ve.cp_est_descrip_inst_legal), '') AS cp_est_descrip_inst_legal,
        LOWER(
            CONCAT_WS(
                ' ',
                ve.cue::text,
                ve.codigo_jurisdiccional_sede,
                ve.nombre,
                ve.sector,
                ve.dependencia,
                ve.confesional,
                ve.arancelado,
                ve.categoria,
                ve.estado,
                ve.localidad_sede,
                ve.departamento_sede,
                ve.responsable_apellido,
                ve.responsable_nombre,
                ve.documento_responsable::text,
                otipos.tipo_ofertas,
                est_obs.valor
            )
        ) AS search_text
    FROM (
        SELECT
            e.id_establecimiento,
            e.id_responsable,
            COALESCE(vpe.cue::text, e.cue::text) AS cue,
            COALESCE(ltot.cant_total, vpe.cantidad_localizaciones, 0) AS cantidad_localizaciones,
            COALESCE(vpe.codigo_jurisdiccional_sede::text, l.codigo_jurisdiccional::text) AS codigo_jurisdiccional_sede,
            COALESCE(vpe.nombre, e.nombre) AS nombre,
            COALESCE(vpe.sector, st.descripcion) AS sector,
            COALESCE(vpe.dependencia, dep.descripcion) AS dependencia,
            COALESCE(vpe.confesional, conf.descripcion) AS confesional,
            COALESCE(vpe.arancelado, aran.descripcion) AS arancelado,
            COALESCE(vpe.categoria, cat.descripcion) AS categoria,
            COALESCE(vpe.estado, est.descripcion) AS estado,
            COALESCE(vpe.localidad_sede, l.localidad_nombre) AS localidad_sede,
            COALESCE(vpe.departamento_sede, l.departamento_nombre) AS departamento_sede,
            COALESCE(vpe.calle_sede, l.calle) AS calle_sede,
            COALESCE(vpe.nro_sede::text, l.nro::text) AS nro_sede,
            COALESCE(vpe.referencia_sede, l.referencia) AS referencia_sede,
            COALESCE(vpe.cod_postal_sede::text, l.cod_postal::text) AS cod_postal_sede,
            COALESCE(vpe.fecha_creacion::text, e.fecha_creacion::text) AS fecha_creacion,
            COALESCE(vpe.fecha_alta::text, e.fecha_alta::text) AS fecha_alta,
            COALESCE(vpe.fecha_baja::text, e.fecha_baja::text) AS fecha_baja,
            COALESCE(vpe.fecha_actualizacion::text, e.fecha_actualizacion::text) AS fecha_actualizacion,
            COALESCE(vpe.responsable_apellido, r.apellido) AS responsable_apellido,
            COALESCE(vpe.responsable_nombre, r.nombre) AS responsable_nombre,
            COALESCE(vpe.documento_responsable::text, r.nro_documento::text) AS documento_responsable,
            COALESCE(vpe.cp_numeroestablecimiento, cp.cp_numeroestablecimiento) AS cp_numeroestablecimiento,
            COALESCE(vpe.cp_est_tipo_ed, cp.cp_est_tipo_ed) AS cp_est_tipo_ed,
            COALESCE(vpe.cp_est_nivel, cp.cp_est_nivel) AS cp_est_nivel,
            COALESCE(vpe.cp_est_cargo_director, cp.cp_est_cargo_director) AS cp_est_cargo_director,
            COALESCE(vpe.cp_est_fecha_inst_legal, cp.cp_est_fecha_inst_legal) AS cp_est_fecha_inst_legal,
            COALESCE(vpe.cp_est_nro_inst_legal, cp.cp_est_nro_inst_legal) AS cp_est_nro_inst_legal,
            COALESCE(vpe.cp_est_anio_inst_legal, cp.cp_est_anio_inst_legal) AS cp_est_anio_inst_legal,
            COALESCE(vpe.cp_est_descrip_inst_legal, cp.cp_est_descrip_inst_legal) AS cp_est_descrip_inst_legal
        FROM establecimiento e
        LEFT JOIN vp_establecimientos vpe
          ON vpe.id_establecimiento = e.id_establecimiento
        LEFT JOIN LATERAL (
            SELECT vl.*
            FROM v_localizaciones vl
            WHERE vl.id_establecimiento = e.id_establecimiento
            ORDER BY
                CASE WHEN vl.sede = true THEN 0 ELSE 1 END,
                vl.id_localizacion
            LIMIT 1
        ) l ON true
        LEFT JOIN (
            SELECT
                vl.id_establecimiento,
                SUM(vl.cantidad) AS cant_total
            FROM v_localizaciones vl
            GROUP BY vl.id_establecimiento
        ) ltot
          ON ltot.id_establecimiento = e.id_establecimiento
        LEFT JOIN LATERAL (
            SELECT
                (
                    SELECT MAX(ecpv.valor::text)
                    FROM est_campo_prov_valor ecpv
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638047
                ) AS cp_numeroestablecimiento,
                (
                    SELECT MAX((cpc.codigo::text || '-'::text) || cpc.descripcion::text)
                    FROM est_campo_prov_valor ecpv
                    JOIN campo_prov_codigo cpc
                      ON ecpv.valor::text = cpc.codigo::text
                     AND ecpv.id_campo_prov = cpc.id_campo_prov
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638074
                ) AS cp_est_tipo_ed,
                (
                    SELECT MAX((cpc.codigo::text || '-'::text) || cpc.descripcion::text)
                    FROM est_campo_prov_valor ecpv
                    JOIN campo_prov_codigo cpc
                      ON ecpv.valor::text = cpc.codigo::text
                     AND ecpv.id_campo_prov = cpc.id_campo_prov
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638075
                ) AS cp_est_nivel,
                (
                    SELECT MAX((cpc.codigo::text || '-'::text) || cpc.descripcion::text)
                    FROM est_campo_prov_valor ecpv
                    JOIN campo_prov_codigo cpc
                      ON ecpv.valor::text = cpc.codigo::text
                     AND ecpv.id_campo_prov = cpc.id_campo_prov
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638076
                ) AS cp_est_cargo_director,
                (
                    SELECT MAX(ecpv.valor::text)
                    FROM est_campo_prov_valor ecpv
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638052
                ) AS cp_est_fecha_inst_legal,
                (
                    SELECT MAX(ecpv.valor::text)
                    FROM est_campo_prov_valor ecpv
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638060
                ) AS cp_est_nro_inst_legal,
                (
                    SELECT MAX(ecpv.valor::text)
                    FROM est_campo_prov_valor ecpv
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638059
                ) AS cp_est_anio_inst_legal,
                (
                    SELECT MAX((cpc.codigo::text || '-'::text) || cpc.descripcion::text)
                    FROM est_campo_prov_valor ecpv
                    JOIN campo_prov_codigo cpc
                      ON ecpv.valor::text = cpc.codigo::text
                     AND ecpv.id_campo_prov = cpc.id_campo_prov
                    WHERE ecpv.id_establecimiento = e.id_establecimiento
                      AND ecpv.id_campo_prov = 1019638057
                ) AS cp_est_descrip_inst_legal
        ) cp ON true
        LEFT JOIN responsable r
          ON r.id_responsable = e.id_responsable
        LEFT JOIN sector_tipo st
          ON st.c_sector = e.c_sector
        LEFT JOIN dependencia_tipo dep
          ON dep.c_dependencia = e.c_dependencia
        LEFT JOIN sino_tipo conf
          ON conf.c_sino = e.c_confesional
        LEFT JOIN sino_tipo aran
          ON aran.c_sino = e.c_arancelado
        LEFT JOIN categoria_tipo cat
          ON cat.c_categoria = e.c_categoria
        LEFT JOIN estado_tipo est
          ON est.c_estado = e.c_estado
    ) ve
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(id_localizacion::text, ',' ORDER BY id_localizacion) AS ids
        FROM localizacion
        WHERE id_establecimiento = ve.id_establecimiento
    ) loc_ids ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(ol.id_oferta_local::text, ',' ORDER BY ol.id_oferta_local) AS ids
        FROM localizacion l
        JOIN oferta_local ol ON ol.id_localizacion = l.id_localizacion
        WHERE l.id_establecimiento = ve.id_establecimiento
    ) oferta_ids ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(valor_limpio, ', ' ORDER BY orden_obs) AS valor
        FROM (
            SELECT
                BTRIM(valor) AS valor_limpio,
                MIN(id_est_campo_prov_valor) AS orden_obs
            FROM est_campo_prov_valor
            WHERE id_establecimiento = ve.id_establecimiento
              AND id_campo_prov = 1019638050
              AND COALESCE(BTRIM(valor), '') <> ''
            GROUP BY BTRIM(valor)
        ) obs
    ) est_obs ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(BTRIM(ot.descripcion), ', ' ORDER BY ot.c_oferta, l.anexo, ol.id_oferta_local) AS tipo_ofertas
        FROM localizacion l
        JOIN oferta_local ol ON ol.id_localizacion = l.id_localizacion
        JOIN oferta_tipo ot ON ot.c_oferta = ol.c_oferta
        WHERE l.id_establecimiento = ve.id_establecimiento
    ) otipos ON TRUE
    $sql$
) AS src(
    id bigint,
    id_establecimiento bigint,
    id_responsable bigint,
    localizaciones_ids text,
    ofertas_ids text,
    cue text,
    cantidad_localizaciones integer,
    codigo_jurisdiccional text,
    codigo_jurisdiccional_sede text,
    nombre text,
    sector text,
    dependencia text,
    confesional text,
    arancelado text,
    categoria text,
    estado text,
    localidad text,
    localidad_sede text,
    departamento text,
    departamento_sede text,
    calle_sede text,
    nro_sede text,
    referencia_sede text,
    cod_postal_sede text,
    fecha_creacion text,
    fecha_alta text,
    fecha_baja text,
    fecha_actualizacion text,
    responsable_apellido text,
    responsable_nombre text,
    documento_responsable text,
    director text,
    tipo_ofertas text,
    observaciones text,
    nro_establecimiento text,
    cp_numeroestablecimiento text,
    tipo_educacion text,
    cp_est_tipo_ed text,
    nivel text,
    cp_est_nivel text,
    cargo_director text,
    cp_est_cargo_director text,
    fecha_inst_legal text,
    cp_est_fecha_inst_legal text,
    nro_inst_legal text,
    cp_est_nro_inst_legal text,
    anio_creacion text,
    cp_est_anio_inst_legal text,
    descrip_inst_legal text,
    cp_est_descrip_inst_legal text,
    search_text text
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_establecimientos_build IS
'Base de establecimientos para PadronInterno: una fila por id_establecimiento, con columnas de listado, detalle propio, filtros, Excel y claves hacia responsables, localizaciones y ofertas.';

CREATE UNIQUE INDEX mv_establecimientos_build_uidx
    ON padroninterno.mv_establecimientos_build (id_establecimiento);
CREATE INDEX mv_establecimientos_build_responsable_idx
    ON padroninterno.mv_establecimientos_build (id_responsable);
CREATE INDEX mv_establecimientos_build_cue_idx
    ON padroninterno.mv_establecimientos_build (cue);
CREATE INDEX mv_establecimientos_build_codigo_jur_idx
    ON padroninterno.mv_establecimientos_build (codigo_jurisdiccional);
CREATE INDEX mv_establecimientos_build_estado_idx
    ON padroninterno.mv_establecimientos_build (estado);
CREATE INDEX mv_establecimientos_build_sector_dependencia_idx
    ON padroninterno.mv_establecimientos_build (sector, dependencia);
CREATE INDEX mv_establecimientos_build_geo_idx
    ON padroninterno.mv_establecimientos_build (departamento, localidad);
CREATE INDEX mv_establecimientos_build_nombre_lower_idx
    ON padroninterno.mv_establecimientos_build ((LOWER(nombre)));

-- Validaciones de contenido y estructura.
SELECT 'mv_establecimientos_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_establecimientos_build;

SELECT
    'mv_establecimientos_build_cues_sin_sede_control' AS validacion,
    esperados.cue,
    COUNT(mv.id_establecimiento) AS encontrados
FROM (
    VALUES
        ('2200419'),
        ('2200438'),
        ('2200457'),
        ('2200810'),
        ('2200984')
) AS esperados(cue)
LEFT JOIN padroninterno.mv_establecimientos_build mv
  ON mv.cue = esperados.cue
GROUP BY esperados.cue
ORDER BY esperados.cue;

SELECT
    'mv_establecimientos_build_cues_sin_sede_detalle' AS validacion,
    cue,
    id_establecimiento,
    nombre,
    estado,
    localidad_sede,
    departamento_sede,
    cantidad_localizaciones,
    nro_establecimiento,
    tipo_educacion,
    nivel,
    cargo_director,
    fecha_inst_legal,
    nro_inst_legal,
    anio_creacion,
    descrip_inst_legal
FROM padroninterno.mv_establecimientos_build
WHERE cue IN ('2200419', '2200438', '2200457', '2200810', '2200984')
ORDER BY cue;

SELECT 'mv_establecimientos_build_ids_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_establecimientos_build
WHERE id_establecimiento IS NULL;

SELECT id_establecimiento, COUNT(*) AS repetidos
FROM padroninterno.mv_establecimientos_build
GROUP BY id_establecimiento
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_establecimiento;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_establecimientos_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_establecimientos_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_establecimientos_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_establecimientos_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_establecimientos_build
ORDER BY cue, id_establecimiento
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_establecimientos_build
WHERE estado = 'Activo';

EXPLAIN
SELECT *
FROM padroninterno.mv_establecimientos_build
WHERE id_responsable = 1
ORDER BY cue, id_establecimiento;

EXPLAIN
SELECT *
FROM padroninterno.mv_establecimientos_build
WHERE LOWER(nombre) LIKE '%escuela%'
ORDER BY cue, id_establecimiento
LIMIT 20;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_establecimientos_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_establecimientos RENAME TO mv_establecimientos_old;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_uidx RENAME TO mv_establecimientos_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_responsable_idx RENAME TO mv_establecimientos_old_responsable_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_cue_idx RENAME TO mv_establecimientos_old_cue_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_codigo_jur_idx RENAME TO mv_establecimientos_old_codigo_jur_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_estado_idx RENAME TO mv_establecimientos_old_estado_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_sector_dependencia_idx RENAME TO mv_establecimientos_old_sector_dependencia_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_geo_idx RENAME TO mv_establecimientos_old_geo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_nombre_lower_idx RENAME TO mv_establecimientos_old_nombre_lower_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_establecimientos_build RENAME TO mv_establecimientos;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_uidx RENAME TO mv_establecimientos_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_responsable_idx RENAME TO mv_establecimientos_responsable_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_cue_idx RENAME TO mv_establecimientos_cue_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_codigo_jur_idx RENAME TO mv_establecimientos_codigo_jur_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_estado_idx RENAME TO mv_establecimientos_estado_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_sector_dependencia_idx RENAME TO mv_establecimientos_sector_dependencia_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_geo_idx RENAME TO mv_establecimientos_geo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_establecimientos_build_nombre_lower_idx RENAME TO mv_establecimientos_nombre_lower_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_establecimientos IS
'Base de establecimientos para PadronInterno: una fila por id_establecimiento, con columnas de listado, detalle propio, filtros, Excel y claves hacia responsables, localizaciones y ofertas.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_establecimientos_old;
*/
