SELECT count(*) AS escuelas_bii_geo,
 count(*) FILTER (WHERE lat BETWEEN -90 AND 90 AND long BETWEEN -180 AND 180) AS georreferenciadas,
 count(*) FILTER (WHERE lat IS NULL OR long IS NULL) AS sin_coordenadas
FROM public.v_escuelas_bilingues_geo;
SELECT cueanexo, count(*) FROM public.v_escuelas_bilingues_geo GROUP BY cueanexo HAVING count(*)>1;
SELECT cueanexo,nom_est,region_loc,lat,long FROM public.v_escuelas_bilingues_geo ORDER BY cueanexo LIMIT 20;
