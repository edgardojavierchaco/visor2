-- EIB / Visor Educativo Chaco. Ejecutar en la BASE QUE CONTIENE las tablas de Padrón.
-- NO modifica ni elimina v_capa_unica_ofertas_old, padron_ofertas_old ni v_escuelas_bilingues.
-- Revisar primero 00_diagnostico.sql. Transacción para un despliegue controlado.
BEGIN;
CREATE OR REPLACE VIEW public.v_escuelas_bilingues_geo AS
SELECT DISTINCT ON (v.cueanexo)
 v.cueanexo::text AS cueanexo, v.nom_est::text AS nom_est,
 v.acronimo::text AS acronimo, v.oferta::text AS oferta,
 v.ambito::text AS ambito, v.sector::text AS sector,
 v.region_loc::text AS region_loc, v.departamento::text AS departamento,
 v.localidad::text AS localidad, v.lat::double precision AS lat,
 v.long::double precision AS long
FROM public.v_capa_unica_ofertas_old v
WHERE EXISTS (
 SELECT 1 FROM public.padron_ofertas_old p
 WHERE p.cueanexo = v.cueanexo
   AND trim(p.acronimo_oferta::text) ILIKE 'BII'
   AND p.est_oferta::text ILIKE '%Activo%'
)
ORDER BY v.cueanexo, (v.lat IS NULL), v.nom_est NULLS LAST, v.oferta NULLS LAST;
COMMENT ON VIEW public.v_escuelas_bilingues_geo IS
 'Establecimientos con oferta BII activa; una fila por CUEANEXO, coords WGS84 cuando están disponibles.';
COMMIT;
-- Privilegios: conceder SELECT al rol de Django SOLO si corresponde.
-- GRANT SELECT ON public.v_escuelas_bilingues_geo TO visualizador;
