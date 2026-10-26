-- VISOR EDUCATIVO CHACO: SOLO OFERTA 'Común - SNU ' (espacio final incluido en origen).
-- No modifica tablas de origen. Si la vista anterior cambia su estructura, verificar dependencias.
-- Mantiene una fila del padrón por CUEANEXO y TODAS las filas académicas activas de esos CUEANEXO.
-- La cláusula INNER JOIN excluye completamente los 418 CUEANEXO sin coincidencia SNU.
CREATE OR REPLACE VIEW public.v_carreras_titulos_integrada AS
WITH padron_snu AS (
 SELECT DISTINCT ON (p.cueanexo)
   p.cueanexo, p.nom_est, p.region_loc, p.departamento,
   p.localidad, p.ambito, p.sector, p.calle, p.numero,
   p.lat, p.long, p.jornada, p.estado_loc, p.estado_est
 FROM public.v_capa_unica_ofertas_ant p
 WHERE p.cueanexo IS NOT NULL
   AND BTRIM(p.oferta) = 'Común - SNU'
 ORDER BY p.cueanexo,
   CASE WHEN p.lat BETWEEN -90 AND 90 AND p.long BETWEEN -180 AND 180
              AND p.lat <> 0 AND p.long <> 0 THEN 0 ELSE 1 END,
   p.id
)
SELECT
 BTRIM(c.cueanexo) AS cueanexo,
 COALESCE(NULLIF(BTRIM(c.nom_est), ''), p.nom_est) AS establecimiento,
 c.carrera, c.titulo, c.niveltitulotipo AS nivel,
 c.c_oferta, c.est_oferta,
 COALESCE(NULLIF(BTRIM(c.sector), ''), p.sector) AS sector,
 p.region_loc AS region, p.departamento,
 COALESCE(NULLIF(BTRIM(c.localidad), ''), p.localidad) AS localidad,
 p.ambito,
 COALESCE(NULLIF(BTRIM(c.calle), ''), p.calle) AS calle,
 COALESCE(NULLIF(BTRIM(c.numero), ''), p.numero) AS numero,
 c.telefono_loc AS telefono, c.email_loc AS email,
 p.lat AS latitud, p.long AS longitud, p.jornada,
 p.estado_loc, p.estado_est,
 TRUE AS existe_en_padron,
 COALESCE(p.lat BETWEEN -90 AND 90 AND p.long BETWEEN -180 AND 180
  AND p.lat <> 0 AND p.long <> 0, FALSE) AS georreferenciado
FROM public.carreras_titulos c
INNER JOIN padron_snu p ON BTRIM(c.cueanexo) = p.cueanexo::text
WHERE BTRIM(c.est_oferta) = 'Activo';
