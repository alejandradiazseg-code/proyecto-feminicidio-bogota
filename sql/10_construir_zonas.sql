-- 10_construir_zonas.sql
-- Actualiza los polígonos macro (MultiPolygon) de zona
-- en base a la suma de las áreas de sus respectivas Localidades.

UPDATE zona z
SET geom = (
    SELECT ST_Multi(ST_Union(l.geom))
    FROM localidad l
    WHERE l.id_zona = z.id_zona
);

-- Verificar actualizacion
-- NOTICE: Puedes correr este script de manera segura cuantas veces requieras.
