-- Diagnóstico exclusivo SNU. Cifras históricas observadas: 173 filas, 172 CUE,
-- 168 CUE coincidentes con carreras activas; NO son conteos de carreras.
SELECT COUNT(*) AS registros_snu, COUNT(DISTINCT cueanexo) AS establecimientos_snu
FROM public.v_capa_unica_ofertas_ant WHERE BTRIM(oferta) = 'Común - SNU';

SELECT COUNT(*) AS registros_academicos_snu,
       COUNT(DISTINCT cueanexo) AS establecimientos_con_carreras_snu,
       COUNT(DISTINCT carrera) AS carreras_distintas,
       COUNT(DISTINCT titulo) AS titulos_distintos,
       COUNT(DISTINCT region) AS regiones,
       COUNT(DISTINCT cueanexo) FILTER (WHERE georreferenciado) AS con_coordenadas
FROM public.v_carreras_titulos_integrada;

-- Comprobación de igualdad: la vista nunca debe incluir carreras ajenas al padrón SNU.
WITH esperados AS (
 SELECT COUNT(*) AS n
 FROM public.carreras_titulos c
 WHERE BTRIM(c.est_oferta)='Activo'
 AND EXISTS (
  SELECT 1 FROM public.v_capa_unica_ofertas_ant p
  WHERE p.cueanexo::text=BTRIM(c.cueanexo) AND BTRIM(p.oferta)='Común - SNU'
 )
), obtenidos AS (
 SELECT COUNT(*) AS n FROM public.v_carreras_titulos_integrada
)
SELECT e.n AS registros_esperados, o.n AS registros_vista,
       o.n-e.n AS diferencia_debe_ser_cero
FROM esperados e CROSS JOIN obtenidos o;

-- Integridad estricta: debe devolver CERO filas.
SELECT DISTINCT v.cueanexo
FROM public.v_carreras_titulos_integrada v
WHERE NOT EXISTS (
 SELECT 1 FROM public.v_capa_unica_ofertas_ant p
 WHERE p.cueanexo::text=v.cueanexo AND BTRIM(p.oferta)='Común - SNU'
);

-- 4 establecimientos SNU sin carreras activas: quedan para control ministerial.
SELECT DISTINCT p.cueanexo, p.nom_est, p.localidad, p.region_loc
FROM public.v_capa_unica_ofertas_ant p
WHERE BTRIM(p.oferta)='Común - SNU'
AND NOT EXISTS (
 SELECT 1 FROM public.carreras_titulos c
 WHERE BTRIM(c.cueanexo)=p.cueanexo::text AND BTRIM(c.est_oferta)='Activo'
)
ORDER BY p.cueanexo;
