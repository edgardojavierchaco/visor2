-- Ejecutar manualmente en la base visualizador.
-- Objetivo: construir padroninterno.mv_oferta_titulos desde la fuente Padron via dblink.
-- Reemplaza titulos/planes del ojito de oferta local y el detalle de titulo actual.
-- Reemplazar solamente estos placeholders antes de ejecutar:
--   COMPLETAR_HOST
--   COMPLETAR_PORT
--   COMPLETAR_USUARIO
--   COMPLETAR_PASSWORD
-- Si la base fuente no se llama Padron, ajustar dbname=Padron en la cadena dblink.

CREATE EXTENSION IF NOT EXISTS dblink;
CREATE SCHEMA IF NOT EXISTS padroninterno;

DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_titulos_build;

CREATE MATERIALIZED VIEW padroninterno.mv_oferta_titulos_build AS
SELECT *
FROM dblink(
    'host=COMPLETAR_HOST port=COMPLETAR_PORT dbname=Padron user=COMPLETAR_USUARIO password=COMPLETAR_PASSWORD',
    $sql$
    SELECT
        vpe.id_oferta_local::bigint AS id_oferta_local,
        vpe.id_plan_estudio_local::bigint AS id_plan_estudio_local,
        vpe.id_plan_estudio_local::bigint AS id_titulo,
        t.c_titulo::bigint AS c_titulo,
        COALESCE(BTRIM(vpe.titulo), '') AS titulo,
        CASE
            WHEN COALESCE(vpe.c_orientacion::text, '') <> ''
             AND COALESCE(vpe.orientacion, '') <> ''
             AND COALESCE(vpe.titulo, '') <> '' THEN
                vpe.c_orientacion::text || ' - ' || vpe.orientacion || ' - ' || vpe.titulo
            WHEN COALESCE(vpe.c_orientacion::text, '') <> ''
             AND COALESCE(vpe.titulo, '') <> '' THEN
                vpe.c_orientacion::text || ' - ' || vpe.titulo
            ELSE
                COALESCE(vpe.titulo, '')
        END AS titulo_completo,
        CASE
            WHEN COALESCE(vpe.c_orientacion::text, '') <> ''
             AND COALESCE(vpe.orientacion, '') <> ''
             AND COALESCE(vpe.titulo, '') <> '' THEN
                vpe.c_orientacion::text || ' - ' || vpe.orientacion || ' - ' || vpe.titulo
            WHEN COALESCE(vpe.c_orientacion::text, '') <> ''
             AND COALESCE(vpe.titulo, '') <> '' THEN
                vpe.c_orientacion::text || ' - ' || vpe.titulo
            ELSE
                COALESCE(vpe.titulo, '')
        END AS titulo_completo_plan,
        COALESCE(t.cod_titulo::text, '') || ' - ' || COALESCE(BTRIM(t.descripcion), '') AS titulo_completo_detalle,
        CASE
            WHEN COALESCE(pl.duracion::text, '') = '' THEN ''
            WHEN NULLIF(COALESCE(BTRIM(de.descripcion), ''), '') IS NOT NULL THEN
                pl.duracion::text || ' ' || COALESCE(BTRIM(de.descripcion), '')
            ELSE pl.duracion::text
        END AS duracion,
        TRIM(
            BOTH ' ' FROM
            CONCAT_WS(
                ' ',
                NULLIF(COALESCE(BTRIM(inl.descripcion), ''), ''),
                CASE
                    WHEN COALESCE(pl.norma_nro::text, '') <> '' THEN 'nro'
                    ELSE NULL
                END,
                NULLIF(COALESCE(pl.norma_nro::text, ''), '')
            )
        ) ||
        CASE
            WHEN COALESCE(pl.norma_anio::text, '') <> '' THEN ' (' || pl.norma_anio::text || ')'
            ELSE ''
        END AS norma,
        COALESCE(BTRIM(dt.descripcion), '') AS dictado,
        COALESCE(BTRIM(req.descripcion), COALESCE(pl.c_requisito::text, '')) AS requisito,
        COALESCE(BTRIM(cond.descripcion), COALESCE(pl.c_condicion::text, '')) AS condicion_ingreso,
        COALESCE(BTRIM(c.descripcion), '') AS carrera,
        COALESCE(BTRIM(nt.descripcion), COALESCE(t.c_nivel_titulo::text, '')) AS nivel,
        COALESCE(BTRIM(d.descripcion), '') AS disciplina,
        COALESCE(BTRIM(r.descripcion), '') AS rama,
        CASE
            WHEN COALESCE(pel_sec.c_orientacion::text, '') <> ''
             AND COALESCE(BTRIM(ori.descripcion), '') <> '' THEN
                pel_sec.c_orientacion::text || ' - ' || BTRIM(ori.descripcion)
            WHEN COALESCE(BTRIM(ori.descripcion), '') <> '' THEN
                BTRIM(ori.descripcion)
            ELSE
                COALESCE(pel_sec.c_orientacion::text, '')
        END AS orientacion,
        COALESCE(t.cod_titulo::text, '') AS cod_titulo,
        COALESCE(BTRIM(t.descripcion), '') AS titulo_descripcion
    FROM v_planes_estudio vpe
    JOIN plan_estudio_local pl ON pl.id_plan_estudio_local = vpe.id_plan_estudio_local
    LEFT JOIN titulo_oferta_tipo tot ON pl.c_titulo_oferta = tot.c_titulo_oferta
    LEFT JOIN titulo_tipo t ON tot.c_titulo = t.c_titulo
    LEFT JOIN carrera_tipo c ON t.c_carrera = c.c_carrera
    LEFT JOIN nivel_titulo_tipo nt ON t.c_nivel_titulo = nt.c_nivel_titulo
    LEFT JOIN disciplina_tipo d ON c.c_disciplina = d.c_disciplina
    LEFT JOIN rama_tipo r ON t.cod_rama = r.c_rama
    LEFT JOIN plan_estudio_local_secundaria pel_sec ON pl.id_plan_estudio_local = pel_sec.id_plan_estudio_local
    LEFT JOIN orientacion_tipo ori ON pel_sec.c_orientacion = ori.c_orientacion
    LEFT JOIN dictado_tipo dt ON pl.c_dictado = dt.c_dictado
    LEFT JOIN requisito_tipo req ON pl.c_requisito = req.c_requisito
    LEFT JOIN condicion_tipo cond ON pl.c_condicion = cond.c_condicion
    LEFT JOIN duracion_en_tipo de ON pl.c_duracion_en = de.c_duracion_en
    LEFT JOIN instr_legal_tipo inl ON pl.c_norma = inl.c_instr_legal
    $sql$
) AS src(
    id_oferta_local bigint,
    id_plan_estudio_local bigint,
    id_titulo bigint,
    c_titulo bigint,
    titulo text,
    titulo_completo text,
    titulo_completo_plan text,
    titulo_completo_detalle text,
    duracion text,
    norma text,
    dictado text,
    requisito text,
    condicion_ingreso text,
    carrera text,
    nivel text,
    disciplina text,
    rama text,
    orientacion text,
    cod_titulo text,
    titulo_descripcion text
);

COMMENT ON MATERIALIZED VIEW padroninterno.mv_oferta_titulos_build IS
'Titulos y planes tabulares de ofertas locales para PadronInterno: una fila por id_oferta_local e id_plan_estudio_local. id_titulo conserva la navegacion actual y equivale a id_plan_estudio_local.';

CREATE UNIQUE INDEX mv_oferta_titulos_build_uidx
    ON padroninterno.mv_oferta_titulos_build (id_oferta_local, id_plan_estudio_local);
CREATE INDEX mv_oferta_titulos_build_oferta_idx
    ON padroninterno.mv_oferta_titulos_build (id_oferta_local);
CREATE INDEX mv_oferta_titulos_build_plan_idx
    ON padroninterno.mv_oferta_titulos_build (id_plan_estudio_local);
CREATE INDEX mv_oferta_titulos_build_titulo_idx
    ON padroninterno.mv_oferta_titulos_build (id_titulo);
CREATE INDEX mv_oferta_titulos_build_c_titulo_idx
    ON padroninterno.mv_oferta_titulos_build (c_titulo);

-- Validaciones de contenido y estructura.
SELECT 'mv_oferta_titulos_build_count' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_oferta_titulos_build;

SELECT 'mv_oferta_titulos_build_ids_padre_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_oferta_titulos_build
WHERE id_oferta_local IS NULL;

SELECT 'mv_oferta_titulos_build_planes_nulos' AS validacion, COUNT(*) AS total
FROM padroninterno.mv_oferta_titulos_build
WHERE id_plan_estudio_local IS NULL;

SELECT id_oferta_local, id_plan_estudio_local, COUNT(*) AS repetidos
FROM padroninterno.mv_oferta_titulos_build
GROUP BY id_oferta_local, id_plan_estudio_local
HAVING COUNT(*) > 1
ORDER BY repetidos DESC, id_oferta_local, id_plan_estudio_local;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'padroninterno'
  AND table_name = 'mv_oferta_titulos_build'
ORDER BY ordinal_position;

SELECT
    pg_size_pretty(pg_relation_size('padroninterno.mv_oferta_titulos_build')) AS datos,
    pg_size_pretty(pg_indexes_size('padroninterno.mv_oferta_titulos_build')) AS indices,
    pg_size_pretty(pg_total_relation_size('padroninterno.mv_oferta_titulos_build')) AS total;

EXPLAIN
SELECT *
FROM padroninterno.mv_oferta_titulos_build
WHERE id_oferta_local = 1
ORDER BY titulo, id_plan_estudio_local;

EXPLAIN
SELECT *
FROM padroninterno.mv_oferta_titulos_build
WHERE id_plan_estudio_local = 1
LIMIT 1;

-- Promocion manual build -> definitiva. Ejecutar solo si las validaciones anteriores son correctas.
/*
BEGIN;
DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_titulos_old;
ALTER MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_titulos RENAME TO mv_oferta_titulos_old;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_uidx RENAME TO mv_oferta_titulos_old_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_oferta_idx RENAME TO mv_oferta_titulos_old_oferta_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_plan_idx RENAME TO mv_oferta_titulos_old_plan_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_titulo_idx RENAME TO mv_oferta_titulos_old_titulo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_c_titulo_idx RENAME TO mv_oferta_titulos_old_c_titulo_idx;
ALTER MATERIALIZED VIEW padroninterno.mv_oferta_titulos_build RENAME TO mv_oferta_titulos;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_build_uidx RENAME TO mv_oferta_titulos_uidx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_build_oferta_idx RENAME TO mv_oferta_titulos_oferta_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_build_plan_idx RENAME TO mv_oferta_titulos_plan_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_build_titulo_idx RENAME TO mv_oferta_titulos_titulo_idx;
ALTER INDEX IF EXISTS padroninterno.mv_oferta_titulos_build_c_titulo_idx RENAME TO mv_oferta_titulos_c_titulo_idx;
COMMENT ON MATERIALIZED VIEW padroninterno.mv_oferta_titulos IS
'Titulos y planes tabulares de ofertas locales para PadronInterno: una fila por id_oferta_local e id_plan_estudio_local. id_titulo conserva la navegacion actual y equivale a id_plan_estudio_local.';
COMMIT;

-- Opcional luego de validar la vista definitiva:
-- DROP MATERIALIZED VIEW IF EXISTS padroninterno.mv_oferta_titulos_old;
*/
