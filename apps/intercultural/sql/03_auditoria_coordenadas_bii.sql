-- Solo lectura: comprueba latitud/longitud y CUEANEXO de la vista geográfica.
SELECT cueanexo, nom_est, region_loc, lat, long,
 CASE WHEN lat IS NULL OR long IS NULL THEN 'SIN COORDENADAS'
      WHEN lat NOT BETWEEN -90 AND 90 OR long NOT BETWEEN -180 AND 180 THEN 'INVALIDAS'
      WHEN lat NOT BETWEEN -28.5 AND -24.0 OR long NOT BETWEEN -63.8 AND -58.1 THEN 'FUERA DEL AREA APROXIMADA DE CHACO'
      ELSE 'EN AREA APROXIMADA DE CHACO' END AS diagnostico
FROM public.v_escuelas_bilingues_geo
ORDER BY diagnostico, cueanexo;

-- Contrasta contra geometría original y SRID del registro de localización.
SELECT p.cueanexo, ST_SRID(t.geom) AS srid_original,
 ST_Y(ST_Transform(t.geom,4326)) AS lat_calculada,
 ST_X(ST_Transform(t.geom,4326)) AS long_calculada
FROM public.v_escuelas_bilingues_geo p
LEFT JOIN public.t_localizacionesold t ON t.cueanexo::text = p.cueanexo::text
ORDER BY p.cueanexo;
