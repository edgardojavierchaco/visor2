-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_localizaciones desde la fuente Padron via dblink.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizaciones_build;

CREATE MATERIALIZED VIEW padroninterno.mv_localizaciones_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        vl.id_localizacion::bigint AS id,
        vl.id_localizacion::bigint AS id_localizacion,
        vl.id_establecimiento::bigint AS id_establecimiento,
        vl.id_responsable::bigint AS id_responsable,
        dom.id_domicilio::bigint AS id_domicilio_principal,
        COALESCE(dom_ids.ids, '') AS domicilios_ids,
        COALESCE(BTRIM(vl.cue::text), '') AS cue,
        COALESCE(BTRIM(vl.anexo::text), '') AS anexo,
        COALESCE(BTRIM(vl.cue::text), '') ||
            CASE
                WHEN COALESCE(BTRIM(vl.anexo::text), '') <> '' THEN '-' || LPAD(BTRIM(vl.anexo::text), 2, '0')
                ELSE ''
            END AS cue_anexo,
        COALESCE(BTRIM(vl.codigo_jurisdiccional), '') AS codigo_jurisdiccional,
        COALESCE(BTRIM(vl.ambito), '') AS ambito,
        COALESCE(vl.sede, false)::boolean AS sede,
        COALESCE(vl.sede_administrativa, false)::boolean AS sede_adm,
        COALESCE(vl.sede_administrativa, false)::boolean AS sede_administrativa,
        COALESCE(BTRIM(vl.periodo_funcionamiento), '') AS periodo_funcionamiento,
        COALESCE(BTRIM(vl.nombre), '') AS nombre,
        COALESCE(BTRIM(ve.nombre), '') AS establecimiento,
        COALESCE(BTRIM(ve.nombre), '') AS establecimiento_nombre,
        COALESCE(BTRIM(vl.estado_localizacion), '') AS estado,
        COALESCE(BTRIM(vl.estado_localizacion), '') AS estado_localizacion,
        COALESCE(BTRIM(vl.sector), '') AS sector,
        COALESCE(BTRIM(vl.dependencia), '') AS dependencia,
        COALESCE(BTRIM(vl.responsable_apellido), '') AS responsable_apellido,
        COALESCE(BTRIM(vl.responsable_nombre), '') AS responsable_nombre,
        COALESCE(vl.documento_responsable::text, '') AS documento_responsable,
        BTRIM(
            CONCAT(
                COALESCE(vl.responsable_apellido, ''),
                CASE
                    WHEN COALESCE(vl.responsable_nombre, '') <> ''
                     AND COALESCE(vl.responsable_apellido, '') <> ''
                        THEN ', ' || vl.responsable_nombre
                    ELSE COALESCE(vl.responsable_nombre, '')
                END,
                CASE
                    WHEN vl.documento_responsable IS NOT NULL
                        THEN '(' || vl.documento_responsable::text || ')'
                    ELSE ''
                END
            )
        ) AS responsable,
        COALESCE(BTRIM(otipos.tipo_ofertas), '') AS tipo_oferta,
        COALESCE(BTRIM(otipos.tipo_ofertas), '') AS ofertas_resumen,
        COALESCE(BTRIM(mods.modalidades), '') AS modalidades_complementarias,
        COALESCE(BTRIM(vl.localidad_nombre), '') AS localidad,
        COALESCE(BTRIM(vl.localidad_nombre), '') AS localidad_nombre,
        COALESCE(BTRIM(vl.departamento_nombre), '') AS departamento,
        COALESCE(BTRIM(vl.departamento_nombre), '') AS departamento_nombre,
        COALESCE(BTRIM(dom.calle), COALESCE(BTRIM(vl.calle), '')) AS calle,
        COALESCE(BTRIM(dom.nro), COALESCE(BTRIM(vl.nro), '')) AS nro,
        COALESCE(BTRIM(dom.barrio), '') AS barrio,
        COALESCE(BTRIM(dom.referencia), '') AS referencia,
        COALESCE(BTRIM(dom.cod_postal), COALESCE(BTRIM(vl.cod_postal), '')) AS cod_postal,
        COALESCE(BTRIM(dom.cui), '') AS domicilio_cui,
        COALESCE(
            NULLIF(
                TRIM(
                    CONCAT(
                        COALESCE(NULLIF(BTRIM(dom.calle), ''), ''),
                        CASE WHEN COALESCE(NULLIF(BTRIM(dom.nro), ''), '') <> '' THEN ' ' || BTRIM(dom.nro) ELSE '' END,
                        CASE WHEN COALESCE(NULLIF(BTRIM(dom.barrio), ''), '') <> '' THEN ', ' || BTRIM(dom.barrio) ELSE '' END,
                        CASE WHEN COALESCE(NULLIF(BTRIM(dom.cod_postal), ''), '') <> '' THEN ' (' || BTRIM(dom.cod_postal) || ')' ELSE '' END
                    )
                ),
                ''
            ),
            CONCAT_WS(
                ' ',
                COALESCE(vl.calle, ''),
                COALESCE(vl.nro, ''),
                COALESCE(vl.cod_postal, ''),
                COALESCE(vl.localidad_nombre, ''),
                COALESCE(vl.departamento_nombre, '')
            )
        ) AS domicilio_ppal,
        COALESCE(BTRIM(vl.telefono_cod_area), '') AS cod_area_tel,
        COALESCE(BTRIM(vl.telefono_cod_area), '') AS telefono_cod_area,
        COALESCE(BTRIM(vl.telefono), '') AS telefono,
        COALESCE(BTRIM(vl.email), '') AS email,
        COALESCE(BTRIM(vl.sitio_web), '') AS sitio_web,
        COALESCE(BTRIM(vl.alternancia), '') AS alternancia,
        COALESCE(BTRIM(vl.cooperadora), '') AS cooperadora,
        COALESCE(BTRIM(vl.permanencia), '') AS permanencia,
        COALESCE(BTRIM(vl.observaciones), '') AS observaciones,
        COALESCE(l.fecha_creacion::text, '') AS fecha_creacion,
        COALESCE(l.fecha_alta::text, '') AS fecha_alta,
        COALESCE(l.fecha_baja::text, '') AS fecha_baja,
        COALESCE(l.fecha_actualizacion::text, '') AS fecha_actualizacion,
        COALESCE(BTRIM(vl.cp_tedirregional), '') AS tel_director_regional,
        COALESCE(BTRIM(vl.cp_tedirregional), '') AS cp_tedirregional,
        COALESCE(BTRIM(vl.cp_emaildirregional), '') AS email_dir_regional,
        COALESCE(BTRIM(vl.cp_emaildirregional), '') AS cp_emaildirregional,
        COALESCE(BTRIM(vl.cp_supervisortecnico), '') AS supervisor_tecnico,
        COALESCE(BTRIM(vl.cp_supervisortecnico), '') AS cp_supervisortecnico,
        COALESCE(BTRIM(vl.cp_esvat4), '') AS microregion,
        COALESCE(BTRIM(vl.cp_esvat4), '') AS cp_esvat4,
        COALESCE(BTRIM(vl.cp_esvat6), '') AS udt,
        COALESCE(BTRIM(vl.cp_esvat6), '') AS cp_esvat6,
        COALESCE(BTRIM(vl.cp_esvat5), '') AS regional_actual,
        COALESCE(BTRIM(vl.cp_esvat5), '') AS cp_esvat5,
        COALESCE(BTRIM(vl.cp_zonaprovincial), '') AS zona_provincial,
        COALESCE(BTRIM(vl.cp_zonaprovincial), '') AS cp_zonaprovincial,
        COALESCE(BTRIM(vl.cp_esvat3), '') AS anterior_regional,
        COALESCE(BTRIM(vl.cp_esvat3), '') AS cp_esvat3,
        COALESCE(
            CASE
                WHEN COALESCE(BTRIM(vl.cp_directorregional), '') = cpc_directorregional.codigo
                    THEN NULLIF(BTRIM(cpc_directorregional.descripcion), '')
                WHEN COALESCE(BTRIM(vl.cp_directorregional), '') LIKE cpc_directorregional.codigo || '-%'
                    THEN NULLIF(
                        BTRIM(
                            SUBSTRING(
                                COALESCE(BTRIM(vl.cp_directorregional), '')
                                FROM LENGTH(cpc_directorregional.codigo) + 2
                            )
                        ),
                        ''
                    )
                ELSE NULLIF(BTRIM(vl.cp_directorregional), '')
            END,
            ''
        ) AS director_regional,
        COALESCE(
            CASE
                WHEN COALESCE(BTRIM(vl.cp_directorregional), '') = cpc_directorregional.codigo
                    THEN NULLIF(
                        BTRIM(
                            CONCAT_WS(
                                ', ',
                                NULLIF(BTRIM(cpc_directorregional.descripcion), ''),
                                cpc_directorregional.codigo
                            )
                        ),
                        ''
                    )
                WHEN COALESCE(BTRIM(vl.cp_directorregional), '') LIKE cpc_directorregional.codigo || '-%'
                    THEN NULLIF(
                        BTRIM(
                            CONCAT_WS(
                                ', ',
                                NULLIF(
                                    BTRIM(
                                        SUBSTRING(
                                            COALESCE(BTRIM(vl.cp_directorregional), '')
                                            FROM LENGTH(cpc_directorregional.codigo) + 2
                                        )
                                    ),
                                    ''
                                ),
                                cpc_directorregional.codigo
                            )
                        ),
                        ''
                    )
                ELSE NULLIF(BTRIM(vl.cp_directorregional), '')
            END,
            ''
        ) AS director_regional_detalle,
        COALESCE(BTRIM(vl.cp_directorregional), '') AS cp_directorregional,
        COALESCE(BTRIM(vl.cp_plandeobra), '') AS plan_de_obra,
        COALESCE(BTRIM(vl.cp_plandeobra), '') AS cp_plandeobra,
        COALESCE(BTRIM(vl.cp_patrimonioedilicio), '') AS patrimonio_edilicio,
        COALESCE(BTRIM(vl.cp_patrimonioedilicio), '') AS cp_patrimonioedilicio,
        COALESCE(BTRIM(vl.cp_estfechacreacionedificio), '') AS fecha_creacion_edificio,
        COALESCE(BTRIM(vl.cp_estfechacreacionedificio), '') AS cp_estfechacreacionedificio,
        COALESCE(BTRIM(vl.cp_esvar1), '') AS nro_biblioteca,
        COALESCE(BTRIM(vl.cp_esvar1), '') AS cp_esvar1,
        COALESCE(BTRIM(vl.cp_esvar4), '') AS cuof,
        COALESCE(BTRIM(vl.cp_esvar4), '') AS cp_esvar4,
        COALESCE(BTRIM(vl.cp_esvar2), '') AS cui,
        COALESCE(BTRIM(vl.cp_esvar2), '') AS cp_esvar2,
        COALESCE(BTRIM(vl.cp_esvar3), '') AS cua,
        COALESCE(BTRIM(vl.cp_esvar3), '') AS cp_esvar3,
        COALESCE(BTRIM(vl.cp_esvat1), '') AS tipo_albergue,
        COALESCE(BTRIM(vl.cp_esvat1), '') AS cp_esvat1,
        COALESCE(BTRIM(vl.cp_p8104_localizacion_1019638033), '') AS regional_hasta_2015,
        COALESCE(BTRIM(vl.cp_p8104_localizacion_1019638033), '') AS cp_p8104_localizacion_1019638033,
        COALESCE(BTRIM(vl.cp_edif_instlegal_creaciondeestablecimiento), '') AS inst_legal_edificio,
        COALESCE(BTRIM(vl.cp_edif_instlegal_creaciondeestablecimiento), '') AS cp_edif_instlegal_creaciondeestablecimiento,
        COALESCE(BTRIM(loc_tel_sup.valor), '') AS tel_supervisor,
        COALESCE(BTRIM(loc_email_sup.valor), '') AS email_supervisor,
        COALESCE(BTRIM(vl.cp_reg_hasta_2020), '') AS regional_hasta_2020,
        COALESCE(BTRIM(vl.cp_reg_hasta_2020), '') AS cp_reg_hasta_2020,
        LOWER(
            CONCAT_WS(
                ' ',
                vl.cue::text,
                vl.anexo::text,
                vl.codigo_jurisdiccional,
                vl.nombre,
                ve.nombre,
                vl.estado_localizacion,
                vl.sector,
                vl.dependencia,
                vl.localidad_nombre,
                vl.departamento_nombre,
                otipos.tipo_ofertas,
                mods.modalidades,
                vl.responsable_apellido,
                vl.responsable_nombre,
                vl.documento_responsable::text
            )
        ) AS search_text
    FROM vp_localizaciones vl
    JOIN localizacion l
      ON l.id_localizacion = vl.id_localizacion
    LEFT JOIN vp_establecimientos ve
      ON ve.id_establecimiento = vl.id_establecimiento
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(id_domicilio::text, ',' ORDER BY id_domicilio) AS ids
        FROM localizacion_domicilio
        WHERE id_localizacion = vl.id_localizacion
    ) dom_ids ON TRUE
    LEFT JOIN LATERAL (
        SELECT
            ld.id_domicilio,
            ld.c_tipo_dom,
            d.calle,
            d.nro,
            d.barrio,
            d.referencia,
            d.cod_postal,
            d.cui
        FROM localizacion_domicilio ld
        JOIN domicilio d ON d.id_domicilio = ld.id_domicilio
        WHERE ld.id_localizacion = vl.id_localizacion
        ORDER BY CASE WHEN ld.c_tipo_dom = 1 THEN 0 ELSE 1 END, ld.c_tipo_dom, ld.id_domicilio
        LIMIT 1
    ) dom ON TRUE
    LEFT JOIN loc_campo_prov_valor loc_tel_sup
      ON loc_tel_sup.id_localizacion = vl.id_localizacion
     AND loc_tel_sup.id_campo_prov = 1019638042
    LEFT JOIN loc_campo_prov_valor loc_email_sup
      ON loc_email_sup.id_localizacion = vl.id_localizacion
     AND loc_email_sup.id_campo_prov = 1019638043
    LEFT JOIN LATERAL (
        SELECT
            cpc.codigo::text AS codigo,
            COALESCE(BTRIM(cpc.descripcion), '') AS descripcion
        FROM campo_prov_codigo cpc
        WHERE cpc.id_campo_prov = 1019638045
          AND COALESCE(BTRIM(cpc.codigo::text), '') <> ''
          AND (
              COALESCE(BTRIM(vl.cp_directorregional), '') = cpc.codigo::text
              OR COALESCE(BTRIM(vl.cp_directorregional), '') LIKE cpc.codigo::text || '-%'
          )
        ORDER BY LENGTH(cpc.codigo::text) DESC, cpc.codigo::text
        LIMIT 1
    ) cpc_directorregional ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(BTRIM(ot.descripcion), ', ' ORDER BY ot.c_oferta, ol.id_oferta_local) AS tipo_ofertas
        FROM oferta_local ol
        JOIN oferta_tipo ot ON ot.c_oferta = ol.c_oferta
        WHERE ol.id_localizacion = vl.id_localizacion
    ) otipos ON TRUE
    LEFT JOIN LATERAL (
        SELECT STRING_AGG(BTRIM(m2.descripcion), ', ' ORDER BY m2.orden, m2.descripcion) AS modalidades
        FROM localizacion_modalidad2_assn lm2
        JOIN modalidad2_tipo m2 ON m2.c_modalidad2 = lm2.c_modalidad2
        WHERE lm2.id_localizacion = vl.id_localizacion
    ) mods ON TRUE
    $sql$
) AS src(
    id bigint,
    id_localizacion bigint,
    id_establecimiento bigint,
    id_responsable bigint,
    id_domicilio_principal bigint,
    domicilios_ids text,
    cue text,
    anexo text,
    cue_anexo text,
    codigo_jurisdiccional text,
    ambito text,
    sede boolean,
    sede_adm boolean,
    sede_administrativa boolean,
    periodo_funcionamiento text,
    nombre text,
    establecimiento text,
    establecimiento_nombre text,
    estado text,
    estado_localizacion text,
    sector text,
    dependencia text,
    responsable_apellido text,
    responsable_nombre text,
    documento_responsable text,
    responsable text,
    tipo_oferta text,
    ofertas_resumen text,
    modalidades_complementarias text,
    localidad text,
    localidad_nombre text,
    departamento text,
    departamento_nombre text,
    calle text,
    nro text,
    barrio text,
    referencia text,
    cod_postal text,
    domicilio_cui text,
    domicilio_ppal text,
    cod_area_tel text,
    telefono_cod_area text,
    telefono text,
    email text,
    sitio_web text,
    alternancia text,
    cooperadora text,
    permanencia text,
    observaciones text,
    fecha_creacion text,
    fecha_alta text,
    fecha_baja text,
    fecha_actualizacion text,
    tel_director_regional text,
    cp_tedirregional text,
    email_dir_regional text,
    cp_emaildirregional text,
    supervisor_tecnico text,
    cp_supervisortecnico text,
    microregion text,
    cp_esvat4 text,
    udt text,
    cp_esvat6 text,
    regional_actual text,
    cp_esvat5 text,
    zona_provincial text,
    cp_zonaprovincial text,
    anterior_regional text,
    cp_esvat3 text,
    director_regional text,
    director_regional_detalle text,
    cp_directorregional text,
    plan_de_obra text,
    cp_plandeobra text,
    patrimonio_edilicio text,
    cp_patrimonioedilicio text,
    fecha_creacion_edificio text,
    cp_estfechacreacionedificio text,
    nro_biblioteca text,
    cp_esvar1 text,
    cuof text,
    cp_esvar4 text,
    cui text,
    cp_esvar2 text,
    cua text,
    cp_esvar3 text,
    tipo_albergue text,
    cp_esvat1 text,
    regional_hasta_2015 text,
    cp_p8104_localizacion_1019638033 text,
    inst_legal_edificio text,
    cp_edif_instlegal_creaciondeestablecimiento text,
    tel_supervisor text,
    email_supervisor text,
    regional_hasta_2020 text,
    cp_reg_hasta_2020 text,
    search_text text
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_localizaciones_build IS
'Base de localizaciones para PadronInterno: una fila por id_localizacion, con columnas de listado, detalle propio, filtros, Excel y claves hacia establecimientos, responsables, domicilios y ofertas.';

CREATE UNIQUE INDEX mv_localizaciones_build_uidx
    ON padroninterno.mv_localizaciones_build (id_localizacion);
CREATE INDEX mv_localizaciones_build_establecimiento_idx
    ON padroninterno.mv_localizaciones_build (id_establecimiento);
CREATE INDEX mv_localizaciones_build_responsable_idx
    ON padroninterno.mv_localizaciones_build (id_responsable);
CREATE INDEX mv_localizaciones_build_domicilio_idx
    ON padroninterno.mv_localizaciones_build (id_domicilio_principal);
CREATE INDEX mv_localizaciones_build_cue_anexo_idx
    ON padroninterno.mv_localizaciones_build (cue, anexo);
CREATE INDEX mv_localizaciones_build_codigo_jur_idx
    ON padroninterno.mv_localizaciones_build (codigo_jurisdiccional);
CREATE INDEX mv_localizaciones_build_estado_idx
    ON padroninterno.mv_localizaciones_build (estado);
CREATE INDEX mv_localizaciones_build_geo_idx
    ON padroninterno.mv_localizaciones_build (departamento, localidad);
CREATE INDEX mv_localizaciones_build_nombre_lower_idx
    ON padroninterno.mv_localizaciones_build ((LOWER(nombre)));

-- Validaciones de contenido y estructura.
SELECT 'mv_localizaciones_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizaciones_build;

SELECT 'mv_localizaciones_build_ids_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_localizaciones_build
WHERE id_localizacion IS NULL;

SELECT id_localizacion, COUNT(*) AS repetidos
FROM padroninterno.mv_localizaciones_build
GROUP BY id_localizacion
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_localizacion;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_localizaciones_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_localizaciones_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_localizaciones_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_localizaciones_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizaciones_build
ORDER BY cue, anexo DESC, id_localizacion
LIMIT 10;

EXPLAIN
SELECT COUNT(*)
FROM padroninterno.mv_localizaciones_build
WHERE estado = 'Activo';

EXPLAIN
SELECT *
FROM padroninterno.mv_localizaciones_build
WHERE id_establecimiento = 1
ORDER BY cue, anexo DESC, id_localizacion;

EXPLAIN
SELECT *
FROM padroninterno.mv_localizaciones_build
WHERE id_responsable = 1
ORDER BY cue, anexo DESC, id_localizacion;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizaciones_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizaciones RENAME TO mv_localizaciones_old;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_uidx RENAME TO mv_localizaciones_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_establecimiento_idx RENAME TO mv_localizaciones_old_establecimiento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_responsable_idx RENAME TO mv_localizaciones_old_responsable_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_domicilio_idx RENAME TO mv_localizaciones_old_domicilio_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_cue_anexo_idx RENAME TO mv_localizaciones_old_cue_anexo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_codigo_jur_idx RENAME TO mv_localizaciones_old_codigo_jur_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_estado_idx RENAME TO mv_localizaciones_old_estado_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_geo_idx RENAME TO mv_localizaciones_old_geo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_nombre_lower_idx RENAME TO mv_localizaciones_old_nombre_lower_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_localizaciones_build RENAME TO mv_localizaciones;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_uidx RENAME TO mv_localizaciones_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_establecimiento_idx RENAME TO mv_localizaciones_establecimiento_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_responsable_idx RENAME TO mv_localizaciones_responsable_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_domicilio_idx RENAME TO mv_localizaciones_domicilio_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_cue_anexo_idx RENAME TO mv_localizaciones_cue_anexo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_codigo_jur_idx RENAME TO mv_localizaciones_codigo_jur_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_estado_idx RENAME TO mv_localizaciones_estado_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_geo_idx RENAME TO mv_localizaciones_geo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_localizaciones_build_nombre_lower_idx RENAME TO mv_localizaciones_nombre_lower_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_localizaciones IS
'Base de localizaciones para PadronInterno: una fila por id_localizacion, con columnas de listado, detalle propio, filtros, Excel y claves hacia establecimientos, responsables, domicilios y ofertas.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_localizaciones_old;
*/
