-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_ofertaslocales desde la fuente Padron via dblink.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_ofertaslocales_build;

CREATE MATERIALIZED VIEW padroninterno.mv_ofertaslocales_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        ol.id_oferta_local::bigint AS id,
        ol.id_oferta_local::bigint AS id_oferta_local,
        ol.id_localizacion::bigint AS id_localizacion,
        l.id_establecimiento::bigint AS id_establecimiento,
        ol.id_responsable::bigint AS id_responsable,
        COALESCE(ol.c_oferta::text, '') AS c_oferta,
        COALESCE(v.c_oferta_base::text, ol.c_oferta::text, '') AS c_oferta_base,
        COALESCE(e.cue::text, '') AS cue,
        COALESCE(l.anexo::text, '') AS anexo,
        UPPER(COALESCE(BTRIM(ol.codigo_jurisdiccional), '')) AS codigo_jurisdiccional,
        COALESCE(v.codigo_jurisdiccional_oferta_local, '') AS codigo_jurisdiccional_oferta_local,
        COALESCE(BTRIM(l.nombre), '') AS localizacion,
        COALESCE(BTRIM(ot.descripcion), '') AS tipo_oferta,
        COALESCE(BTRIM(ot.descripcion), '') AS nombre_titulo,
        COALESCE(BTRIM(ot.descripcion), '') AS oferta,
        COALESCE(BTRIM(ot.descripcion), '') AS carrera,
        COALESCE(BTRIM(est_of.descripcion), '') AS estado,
        COALESCE(BTRIM(est_of.descripcion), '') AS estado_ofertalocal,
        COALESCE(BTRIM(st.descripcion), '') AS subvencion,
        COALESCE(BTRIM(st.descripcion), '') AS subvencion_oferta_local,
        COALESCE(BTRIM(jt.descripcion), '') AS jornada,
        COALESCE(BTRIM(jt.descripcion), '') AS jornada_ofertalocal,
        COALESCE(ol.matricula_total::text, '') AS matricula_total,
        COALESCE(ol.matricula_total::text, '') AS matricula_total_ofertalocal,
        COALESCE(BTRIM(eav_o_mod.valor), '') AS mod_compl_planes,
        COALESCE(v.modalidad_basica, '') AS modalidad_basica,
        COALESCE(BTRIM(eav_o_cab.valor), '') AS oferta_cabecera,
        COALESCE(BTRIM(eav_o_cab.valor), '') AS cabecera_anexo,
        COALESCE(v.cp_of_cab_anexo, '') AS cp_of_cab_anexo,
        COALESCE(BTRIM(SUBSTRING(eav_o_amb.descripcion FROM 1 FOR 1)), '') AS oferta_ambito,
        COALESCE(BTRIM(eav_o_amb.descripcion), '') AS ambito,
        COALESCE(v.cp_of_ambito, '') AS cp_of_ambito,
        COALESCE(BTRIM(eav_o_tipo_ed.descripcion), '') AS oferta_tipo_ed,
        COALESCE(BTRIM(eav_o_tipo_ed.descripcion), '') AS tipo_ed,
        COALESCE(v.cp_of_tipo_ed, '') AS cp_of_tipo_ed,
        COALESCE(BTRIM(eav_o_niv.descripcion), '') AS oferta_nivel,
        COALESCE(BTRIM(eav_o_niv.descripcion), '') AS nivel,
        COALESCE(v.cp_of_nivel, '') AS cp_of_nivel,
        COALESCE(BTRIM(eav_o_fecha.valor), '') AS fecha_creacion,
        COALESCE(v.fecha_creacion_ofertalocal::text, '') AS fecha_creacion_ofertalocal,
        COALESCE(v.fecha_alta_ofertalocal::text, '') AS fecha_alta,
        COALESCE(v.fecha_alta_ofertalocal::text, '') AS fecha_alta_ofertalocal,
        COALESCE(v.fecha_baja_ofertalocal::text, '') AS fecha_baja,
        COALESCE(v.fecha_baja_ofertalocal::text, '') AS fecha_baja_ofertalocal,
        COALESCE(v.fecha_actualizacion_ofertalocal::text, '') AS fecha_actualizacion,
        COALESCE(v.fecha_actualizacion_ofertalocal::text, '') AS fecha_actualizacion_ofertalocal,
        COALESCE(BTRIM(eav_o_sec.descripcion), '') AS oferta_sector,
        COALESCE(BTRIM(eav_o_sec.descripcion), '') AS sector,
        COALESCE(v.cp_of_sector, '') AS cp_of_sector,
        COALESCE(BTRIM(eav_o_acr.valor), '') AS acronimo,
        COALESCE(v.cp_acronimo, '') AS cp_acronimo,
        COALESCE(BTRIM(eav_o_cat.descripcion), '') AS oferta_categoria,
        COALESCE(BTRIM(eav_o_cat.descripcion), '') AS categoria,
        COALESCE(v.cp_of_categoria, '') AS cp_of_categoria,
        COALESCE(BTRIM(eav_o_fecha_inst.valor), '') AS fecha_inst_legal,
        COALESCE(v.cp_of_fecha_inst_legal, '') AS cp_of_fecha_inst_legal,
        COALESCE(BTRIM(eav_o_nro_inst.valor), '') AS nro_inst_legal,
        COALESCE(v.cp_of_nro_inst_legal, '') AS cp_of_nro_inst_legal,
        COALESCE(BTRIM(eav_o_anio.valor), '') AS anio_creacion,
        COALESCE(v.cp_of_anio_inst_legal, '') AS cp_of_anio_inst_legal,
        COALESCE(BTRIM(eav_o_descrip.valor), '') AS descrip_inst_legal,
        COALESCE(v.cp_of_descrip_inst_legal, '') AS cp_of_descrip_inst_legal,
        COALESCE(BTRIM(eav_o_cui.valor), '') AS cui,
        COALESCE(v.cp_efvar2, '') AS cp_efvar2,
        COALESCE(BTRIM(eav_o_cua.valor), '') AS cua,
        COALESCE(v.cp_of_cua, '') AS cp_of_cua,
        COALESCE(BTRIM(eav_o_cuof.valor), '') AS cuof,
        COALESCE(v.cp_efvar4, '') AS cp_efvar4,
        COALESCE(BTRIM(eav_o_reg.valor), '') AS regional,
        COALESCE(v.cp_efvar5, '') AS cp_efvar5,
        COALESCE(BTRIM(eav_o_udt.valor), '') AS udt,
        COALESCE(v.cp_efvar6, '') AS cp_efvar6,
        COALESCE(BTRIM(eav_o_cuofryc.valor), '') AS cuof_ryc,
        COALESCE(v.cp_cuof_ryc, '') AS cp_cuof_ryc,
        COALESCE(BTRIM(cuofryc_det.valor), BTRIM(v.cp_cuof_ryc), '') AS cuof_ryc_detalle,
        COALESCE(BTRIM(eav_o_tel.valor), '') AS tel_supervisor,
        COALESCE(v.cp_tesupervisor_oferta, '') AS cp_tesupervisor_oferta,
        COALESCE(BTRIM(eav_o_mail.valor), '') AS email_supervisor,
        COALESCE(v.cp_mailsupervisor_oferta, '') AS cp_mailsupervisor_oferta,
        COALESCE(BTRIM(eav_o_sup.valor), '') AS supervisor_tecnico,
        COALESCE(v.cp_supervisortecnico_oferta, '') AS cp_supervisortecnico_oferta,
        COALESCE(BTRIM(r.apellido), '') AS apellido_responsable,
        COALESCE(BTRIM(r.nombre), '') AS nombre_responsable,
        COALESCE(r.nro_documento::text, '') AS documento_responsable,
        LOWER(
            CONCAT_WS(
                ' ',
                e.cue::text,
                l.anexo::text,
                ol.codigo_jurisdiccional,
                l.nombre,
                ot.descripcion,
                est_of.descripcion,
                st.descripcion,
                jt.descripcion,
                ol.matricula_total::text,
                eav_o_mod.valor,
                eav_o_cab.valor,
                eav_o_amb.descripcion,
                eav_o_tipo_ed.descripcion,
                eav_o_niv.descripcion,
                eav_o_sec.descripcion,
                eav_o_cat.descripcion,
                eav_o_acr.valor,
                eav_o_cuof.valor,
                eav_o_cui.valor,
                eav_o_cua.valor,
                eav_o_reg.valor,
                eav_o_udt.valor,
                eav_o_cuofryc.valor,
                r.apellido,
                r.nombre,
                r.nro_documento::text
            )
        ) AS search_text
    FROM oferta_local ol
    JOIN localizacion l ON ol.id_localizacion = l.id_localizacion
    JOIN establecimiento e ON l.id_establecimiento = e.id_establecimiento
    JOIN oferta_tipo ot ON ol.c_oferta = ot.c_oferta
    LEFT JOIN vp_oferta_local v ON v.id_oferta_local = ol.id_oferta_local
    LEFT JOIN estado_tipo est_of ON ol.c_estado = est_of.c_estado
    LEFT JOIN subvencion_tipo st ON ol.c_subvencion = st.c_subvencion
    LEFT JOIN jornada_tipo jt ON ol.c_jornada = jt.c_jornada
    LEFT JOIN responsable r ON r.id_responsable = ol.id_responsable
    LEFT JOIN oloc_campo_prov_valor eav_o_fecha
      ON ol.id_oferta_local = eav_o_fecha.id_oferta_local
     AND eav_o_fecha.id_campo_prov = 1019638053
    LEFT JOIN oloc_campo_prov_valor eav_o_fecha_inst
      ON ol.id_oferta_local = eav_o_fecha_inst.id_oferta_local
     AND eav_o_fecha_inst.id_campo_prov = 1019638064
    LEFT JOIN oloc_campo_prov_valor eav_o_nro_inst
      ON ol.id_oferta_local = eav_o_nro_inst.id_oferta_local
     AND eav_o_nro_inst.id_campo_prov = 1019638065
    LEFT JOIN oloc_campo_prov_valor eav_o_anio
      ON ol.id_oferta_local = eav_o_anio.id_oferta_local
     AND eav_o_anio.id_campo_prov = 1019638066
    LEFT JOIN oloc_campo_prov_valor eav_o_descrip
      ON ol.id_oferta_local = eav_o_descrip.id_oferta_local
     AND eav_o_descrip.id_campo_prov = 1019638067
    LEFT JOIN oloc_campo_prov_valor eav_o_cab
      ON ol.id_oferta_local = eav_o_cab.id_oferta_local
     AND eav_o_cab.id_campo_prov = 1019638068
    LEFT JOIN oloc_campo_prov_valor eav_o_cui
      ON ol.id_oferta_local = eav_o_cui.id_oferta_local
     AND eav_o_cui.id_campo_prov = 1019638015
    LEFT JOIN oloc_campo_prov_valor eav_o_cua
      ON ol.id_oferta_local = eav_o_cua.id_oferta_local
     AND eav_o_cua.id_campo_prov = 1019638077
    LEFT JOIN oloc_campo_prov_valor eav_o_cuof
      ON ol.id_oferta_local = eav_o_cuof.id_oferta_local
     AND eav_o_cuof.id_campo_prov = 1019638017
    LEFT JOIN oloc_campo_prov_valor eav_o_reg
      ON ol.id_oferta_local = eav_o_reg.id_oferta_local
     AND eav_o_reg.id_campo_prov = 1019638018
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(valor_limpio, ' | ' ORDER BY valor_limpio) AS valor
        FROM (
            SELECT DISTINCT BTRIM(valor) AS valor_limpio
            FROM oloc_campo_prov_valor
            WHERE id_oferta_local = ol.id_oferta_local
              AND id_campo_prov = 1019638078
              AND COALESCE(BTRIM(valor), '') <> ''
        ) valores_cuofryc
    ) eav_o_cuofryc ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(valor_limpio, ', ' ORDER BY valor_limpio) AS valor
        FROM (
            SELECT DISTINCT BTRIM(valor) AS valor_limpio
            FROM oloc_campo_prov_valor
            WHERE id_oferta_local = ol.id_oferta_local
              AND id_campo_prov = 1019638078
              AND COALESCE(BTRIM(valor), '') <> ''
        ) valores_cuofryc
    ) cuofryc_det ON TRUE
    LEFT JOIN oloc_campo_prov_valor eav_o_acr
      ON ol.id_oferta_local = eav_o_acr.id_oferta_local
     AND eav_o_acr.id_campo_prov = 1019638044
    LEFT JOIN oloc_campo_prov_valor eav_o_mod
      ON ol.id_oferta_local = eav_o_mod.id_oferta_local
     AND eav_o_mod.id_campo_prov = 1019638096
    LEFT JOIN oloc_campo_prov_valor eav_o_sup
      ON ol.id_oferta_local = eav_o_sup.id_oferta_local
     AND eav_o_sup.id_campo_prov = 1019638061
    LEFT JOIN oloc_campo_prov_valor eav_o_tel
      ON ol.id_oferta_local = eav_o_tel.id_oferta_local
     AND eav_o_tel.id_campo_prov = 1019638062
    LEFT JOIN oloc_campo_prov_valor eav_o_mail
      ON ol.id_oferta_local = eav_o_mail.id_oferta_local
     AND eav_o_mail.id_campo_prov = 1019638063
    LEFT JOIN oloc_campo_prov_valor eav_o_udt
      ON ol.id_oferta_local = eav_o_udt.id_oferta_local
     AND eav_o_udt.id_campo_prov = 1019638019
    LEFT JOIN oloc_campo_prov_valor v_amb
      ON ol.id_oferta_local = v_amb.id_oferta_local
     AND v_amb.id_campo_prov = 1019638069
    LEFT JOIN campo_prov_codigo eav_o_amb
      ON v_amb.valor = eav_o_amb.codigo::text
     AND eav_o_amb.id_campo_prov = 1019638069
    LEFT JOIN oloc_campo_prov_valor v_niv
      ON ol.id_oferta_local = v_niv.id_oferta_local
     AND v_niv.id_campo_prov = 1019638071
    LEFT JOIN campo_prov_codigo eav_o_niv
      ON v_niv.valor = eav_o_niv.codigo::text
     AND eav_o_niv.id_campo_prov = 1019638071
    LEFT JOIN oloc_campo_prov_valor v_sec
      ON ol.id_oferta_local = v_sec.id_oferta_local
     AND v_sec.id_campo_prov = 1019638072
    LEFT JOIN campo_prov_codigo eav_o_sec
      ON v_sec.valor = eav_o_sec.codigo::text
     AND eav_o_sec.id_campo_prov = 1019638072
    LEFT JOIN oloc_campo_prov_valor v_cat
      ON ol.id_oferta_local = v_cat.id_oferta_local
     AND v_cat.id_campo_prov = 1019638073
    LEFT JOIN campo_prov_codigo eav_o_cat
      ON v_cat.valor = eav_o_cat.codigo::text
     AND eav_o_cat.id_campo_prov = 1019638073
    LEFT JOIN oloc_campo_prov_valor v_tipo_ed
      ON ol.id_oferta_local = v_tipo_ed.id_oferta_local
     AND v_tipo_ed.id_campo_prov = 1019638070
    LEFT JOIN campo_prov_codigo eav_o_tipo_ed
      ON v_tipo_ed.valor = eav_o_tipo_ed.codigo::text
     AND eav_o_tipo_ed.id_campo_prov = 1019638070
    $sql$
) AS src(
    id bigint,
    id_oferta_local bigint,
    id_localizacion bigint,
    id_establecimiento bigint,
    id_responsable bigint,
    c_oferta text,
    c_oferta_base text,
    cue text,
    anexo text,
    codigo_jurisdiccional text,
    codigo_jurisdiccional_oferta_local text,
    localizacion text,
    tipo_oferta text,
    nombre_titulo text,
    oferta text,
    carrera text,
    estado text,
    estado_ofertalocal text,
    subvencion text,
    subvencion_oferta_local text,
    jornada text,
    jornada_ofertalocal text,
    matricula_total text,
    matricula_total_ofertalocal text,
    mod_compl_planes text,
    modalidad_basica text,
    oferta_cabecera text,
    cabecera_anexo text,
    cp_of_cab_anexo text,
    oferta_ambito text,
    ambito text,
    cp_of_ambito text,
    oferta_tipo_ed text,
    tipo_ed text,
    cp_of_tipo_ed text,
    oferta_nivel text,
    nivel text,
    cp_of_nivel text,
    fecha_creacion text,
    fecha_creacion_ofertalocal text,
    fecha_alta text,
    fecha_alta_ofertalocal text,
    fecha_baja text,
    fecha_baja_ofertalocal text,
    fecha_actualizacion text,
    fecha_actualizacion_ofertalocal text,
    oferta_sector text,
    sector text,
    cp_of_sector text,
    acronimo text,
    cp_acronimo text,
    oferta_categoria text,
    categoria text,
    cp_of_categoria text,
    fecha_inst_legal text,
    cp_of_fecha_inst_legal text,
    nro_inst_legal text,
    cp_of_nro_inst_legal text,
    anio_creacion text,
    cp_of_anio_inst_legal text,
    descrip_inst_legal text,
    cp_of_descrip_inst_legal text,
    cui text,
    cp_efvar2 text,
    cua text,
    cp_of_cua text,
    cuof text,
    cp_efvar4 text,
    regional text,
    cp_efvar5 text,
    udt text,
    cp_efvar6 text,
    cuof_ryc text,
    cp_cuof_ryc text,
    cuof_ryc_detalle text,
    tel_supervisor text,
    cp_tesupervisor_oferta text,
    email_supervisor text,
    cp_mailsupervisor_oferta text,
    supervisor_tecnico text,
    cp_supervisortecnico_oferta text,
    apellido_responsable text,
    nombre_responsable text,
    documento_responsable text,
    search_text text
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_ofertaslocales_build IS
'Base de ofertas locales para PadronInterno: una fila por id_oferta_local, con columnas de listado, detalle propio, filtros, Excel y claves hacia localizaciones, establecimientos y responsables.';

CREATE UNIQUE INDEX mv_ofertaslocales_build_uidx
    ON padroninterno.mv_ofertaslocales_build (id_oferta_local);
CREATE INDEX mv_ofertaslocales_build_localizacion_idx
    ON padroninterno.mv_ofertaslocales_build (id_localizacion);
CREATE INDEX mv_ofertaslocales_build_establecimiento_idx
    ON padroninterno.mv_ofertaslocales_build (id_establecimiento);
CREATE INDEX mv_ofertaslocales_build_responsable_idx
    ON padroninterno.mv_ofertaslocales_build (id_responsable);
CREATE INDEX mv_ofertaslocales_build_cue_anexo_idx
    ON padroninterno.mv_ofertaslocales_build (cue, anexo);
CREATE INDEX mv_ofertaslocales_build_codigo_jur_idx
    ON padroninterno.mv_ofertaslocales_build (codigo_jurisdiccional);
CREATE INDEX mv_ofertaslocales_build_estado_idx
    ON padroninterno.mv_ofertaslocales_build (estado);
CREATE INDEX mv_ofertaslocales_build_tipo_idx
    ON padroninterno.mv_ofertaslocales_build (tipo_oferta);
CREATE INDEX mv_ofertaslocales_build_c_oferta_idx
    ON padroninterno.mv_ofertaslocales_build (c_oferta_base);

-- Validaciones de contenido y estructura.
SELECT 'mv_ofertaslocales_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_ofertaslocales_build;

SELECT 'mv_ofertaslocales_build_ids_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_ofertaslocales_build
WHERE id_oferta_local IS NULL;

SELECT id_oferta_local, COUNT(*) AS repetidos
FROM padroninterno.mv_ofertaslocales_build
GROUP BY id_oferta_local
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_oferta_local;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_ofertaslocales_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_ofertaslocales_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_ofertaslocales_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_ofertaslocales_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_ofertaslocales_build
ORDER BY cue, anexo, id_oferta_local
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_ofertaslocales_build
WHERE estado = 'Activo';

EXPLAIN
SELECT *
FROM padroninterno.mv_ofertaslocales_build
WHERE id_localizacion = 1
ORDER BY c_oferta, id_oferta_local;

EXPLAIN
SELECT *
FROM padroninterno.mv_ofertaslocales_build
WHERE id_establecimiento = 1
ORDER BY c_oferta, anexo, id_oferta_local;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_ofertaslocales_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_ofertaslocales RENAME TO mv_ofertaslocales_old;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_uidx RENAME TO mv_ofertaslocales_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_localizacion_idx RENAME TO mv_ofertaslocales_old_localizacion_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_establecimiento_idx RENAME TO mv_ofertaslocales_old_establecimiento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_responsable_idx RENAME TO mv_ofertaslocales_old_responsable_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_cue_anexo_idx RENAME TO mv_ofertaslocales_old_cue_anexo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_codigo_jur_idx RENAME TO mv_ofertaslocales_old_codigo_jur_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_estado_idx RENAME TO mv_ofertaslocales_old_estado_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_tipo_idx RENAME TO mv_ofertaslocales_old_tipo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_c_oferta_idx RENAME TO mv_ofertaslocales_old_c_oferta_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_ofertaslocales_build RENAME TO mv_ofertaslocales;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_uidx RENAME TO mv_ofertaslocales_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_localizacion_idx RENAME TO mv_ofertaslocales_localizacion_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_establecimiento_idx RENAME TO mv_ofertaslocales_establecimiento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_responsable_idx RENAME TO mv_ofertaslocales_responsable_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_cue_anexo_idx RENAME TO mv_ofertaslocales_cue_anexo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_codigo_jur_idx RENAME TO mv_ofertaslocales_codigo_jur_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_estado_idx RENAME TO mv_ofertaslocales_estado_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_tipo_idx RENAME TO mv_ofertaslocales_tipo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_ofertaslocales_build_c_oferta_idx RENAME TO mv_ofertaslocales_c_oferta_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_ofertaslocales IS
'Base de ofertas locales para PadronInterno: una fila por id_oferta_local, con columnas de listado, detalle propio, filtros, Excel y claves hacia localizaciones, establecimientos y responsables.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_ofertaslocales_old;
*/
