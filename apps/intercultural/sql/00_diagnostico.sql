-- Ejecutar sin modificar información. Verificar base y esquema antes de instalar.
SELECT current_database() AS base, current_schema() AS esquema, current_user AS usuario;
SELECT to_regclass('public.v_capa_unica_ofertas_old') AS capa,
       to_regclass('public.padron_ofertas_old') AS padron,
       to_regclass('public.v_escuelas_bilingues') AS antigua,
       to_regclass('public.alumno_bilingue') AS registros;
SELECT count(*) AS escuelas_bii_actual FROM public.v_escuelas_bilingues;
SELECT cueanexo, count(*) AS filas FROM public.v_escuelas_bilingues GROUP BY cueanexo HAVING count(*)>1 ORDER BY filas DESC LIMIT 30;
SELECT count(*) AS filas_sin_geometria FROM public.v_capa_unica_ofertas_old WHERE lat IS NULL OR long IS NULL;
