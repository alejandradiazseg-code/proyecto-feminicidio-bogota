-- =============================================================================
-- Migración 001 — Alinear una BD existente con el Modelo Físico v1.0
-- Proyecto: Feminicidio Bogotá — Base de Datos Espacial
--
-- Lleva una BD creada con la versión anterior de los scripts al mismo estado
-- que produce hoy 01_crear_tablas.sql + 02_crear_indices.sql, SIN perder datos.
-- Es idempotente: puede ejecutarse varias veces.
--
-- Uso:  psql -h HOST -U USUARIO -d feminicidio_bogota \
--            -v ON_ERROR_STOP=1 -f sql/migraciones/001_alinear_modelo_fisico.sql
-- Recomendado: hacer pg_dump antes de ejecutarla.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. ESTRATO: eliminar duplicados (el ETL se ejecutó varias veces) y garantizar
--    unicidad del nivel. manzana está vacía, así que no hay referencias que mover.
-- -----------------------------------------------------------------------------
DELETE FROM estrato e
 USING estrato d
 WHERE e.nivel = d.nivel
   AND e.id_estrato > d.id_estrato;

ALTER TABLE estrato DROP CONSTRAINT IF EXISTS estrato_nivel_check;
ALTER TABLE estrato ADD  CONSTRAINT estrato_nivel_check CHECK (nivel BETWEEN 1 AND 6);
ALTER TABLE estrato DROP CONSTRAINT IF EXISTS estrato_nivel_key;
ALTER TABLE estrato ADD  CONSTRAINT estrato_nivel_key UNIQUE (nivel);

-- -----------------------------------------------------------------------------
-- 2. UPL: sin id_localidad (relación N:M por ST_Intersects) y geometría
--    MULTIPOLYGON según el Modelo Físico.
-- -----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_upl_id_localidad;
ALTER TABLE upl DROP COLUMN IF EXISTS id_localidad;
ALTER TABLE upl
    ALTER COLUMN geom TYPE GEOMETRY(MULTIPOLYGON, 4326) USING ST_Multi(geom);

-- -----------------------------------------------------------------------------
-- 3. Restricciones CHECK documentadas en el Modelo Físico / Diccionario
-- -----------------------------------------------------------------------------
ALTER TABLE tiempo DROP CONSTRAINT IF EXISTS tiempo_anio_check;
ALTER TABLE tiempo ADD  CONSTRAINT tiempo_anio_check CHECK (anio BETWEEN 2010 AND 2030);

ALTER TABLE condicion_vida DROP CONSTRAINT IF EXISTS condicion_vida_ipm_check;
ALTER TABLE condicion_vida ADD  CONSTRAINT condicion_vida_ipm_check CHECK (ipm BETWEEN 0 AND 1);
ALTER TABLE condicion_vida DROP CONSTRAINT IF EXISTS condicion_vida_desempleo_fem_check;
ALTER TABLE condicion_vida ADD  CONSTRAINT condicion_vida_desempleo_fem_check CHECK (desempleo_fem BETWEEN 0 AND 1);

ALTER TABLE condiciones_territoriales DROP CONSTRAINT IF EXISTS condiciones_territoriales_anio_medicion_check;
ALTER TABLE condiciones_territoriales ADD  CONSTRAINT condiciones_territoriales_anio_medicion_check
    CHECK (anio_medicion >= 2010);
ALTER TABLE condiciones_territoriales DROP CONSTRAINT IF EXISTS condiciones_territoriales_indice_seguridad_nocturna_check;
ALTER TABLE condiciones_territoriales ADD  CONSTRAINT condiciones_territoriales_indice_seguridad_nocturna_check
    CHECK (indice_seguridad_nocturna BETWEEN 1 AND 5);
ALTER TABLE condiciones_territoriales DROP CONSTRAINT IF EXISTS condiciones_territoriales_cobertura_iluminacion_check;
ALTER TABLE condiciones_territoriales ADD  CONSTRAINT condiciones_territoriales_cobertura_iluminacion_check
    CHECK (cobertura_iluminacion BETWEEN 0 AND 1);
ALTER TABLE condiciones_territoriales DROP CONSTRAINT IF EXISTS condiciones_territoriales_accesibilidad_transporte_check;
ALTER TABLE condiciones_territoriales ADD  CONSTRAINT condiciones_territoriales_accesibilidad_transporte_check
    CHECK (accesibilidad_transporte BETWEEN 0 AND 1);

ALTER TABLE victima DROP CONSTRAINT IF EXISTS victima_edad_al_hecho_check;
ALTER TABLE victima ADD  CONSTRAINT victima_edad_al_hecho_check CHECK (edad_al_hecho >= 0);
ALTER TABLE victima DROP CONSTRAINT IF EXISTS victima_numero_hijos_check;
ALTER TABLE victima ADD  CONSTRAINT victima_numero_hijos_check CHECK (numero_hijos >= 0);

ALTER TABLE feminicidio_agregado DROP CONSTRAINT IF EXISTS feminicidio_agregado_anio_check;
ALTER TABLE feminicidio_agregado ADD  CONSTRAINT feminicidio_agregado_anio_check
    CHECK (anio BETWEEN 2010 AND 2030);
ALTER TABLE feminicidio_agregado DROP CONSTRAINT IF EXISTS feminicidio_agregado_conteo_casos_check;
ALTER TABLE feminicidio_agregado ADD  CONSTRAINT feminicidio_agregado_conteo_casos_check
    CHECK (conteo_casos >= 0);

ALTER TABLE institucion DROP CONSTRAINT IF EXISTS institucion_tipo_check;
ALTER TABLE institucion ADD  CONSTRAINT institucion_tipo_check
    CHECK (tipo IN ('COMISARIA_FAMILIA', 'CAI', 'CASA_IGUALDAD', 'CASA_JUSTICIA'));

ALTER TABLE valoracion_riesgo DROP CONSTRAINT IF EXISTS valoracion_riesgo_nivel_riesgo_check;
ALTER TABLE valoracion_riesgo ADD  CONSTRAINT valoracion_riesgo_nivel_riesgo_check
    CHECK (nivel_riesgo IN ('Bajo', 'Medio', 'Alto', 'Extremo'));

ALTER TABLE proceso_penal DROP CONSTRAINT IF EXISTS proceso_penal_estado_actual_check;
ALTER TABLE proceso_penal ADD  CONSTRAINT proceso_penal_estado_actual_check
    CHECK (estado_actual IN ('Indagación', 'Investigación', 'Juicio', 'Ejecución de penas',
                             'Terminación anticipada', 'Precluido'));

-- -----------------------------------------------------------------------------
-- 4. Claves foráneas con la regla ON DELETE del Modelo Físico (sección 2)
--    Se recrean con el mismo nombre que asigna PostgreSQL por defecto.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION pg_temp.recrear_fk(
    tabla text, columna text, ref_tabla text, ref_columna text, regla text
) RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    nombre text := format('%s_%s_fkey', tabla, columna);
BEGIN
    EXECUTE format('ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I', tabla, nombre);
    EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (%I) REFERENCES %I(%I) ON DELETE %s',
                   tabla, nombre, columna, ref_tabla, ref_columna, regla);
END $$;

SELECT pg_temp.recrear_fk(t, c, rt, rc, r) FROM (VALUES
    ('localidad',                 'id_zona',         'zona',              'id_zona',        'RESTRICT'),
    ('barrio',                    'id_upl',          'upl',               'id_upl',         'RESTRICT'),
    ('manzana',                   'id_upl',          'upl',               'id_upl',         'RESTRICT'),
    ('manzana',                   'id_estrato',      'estrato',           'id_estrato',     'RESTRICT'),
    ('condicion_vida',            'id_upl',          'upl',               'id_upl',         'RESTRICT'),
    ('condiciones_territoriales', 'id_upl',          'upl',               'id_upl',         'RESTRICT'),
    ('lugar_hecho',               'id_barrio',       'barrio',            'id_barrio',      'RESTRICT'),
    ('victima',                   'id_barrio_res',   'barrio',            'id_barrio',      'SET NULL'),
    ('victima_indirecta',         'id_feminicidio',  'feminicidio',       'id_feminicidio', 'CASCADE'),
    ('red_apoyo',                 'id_victima',      'victima',           'id_victima',     'CASCADE'),
    ('feminicidio',               'id_victima',      'victima',           'id_victima',     'RESTRICT'),
    ('feminicidio',               'id_agresor',      'agresor',           'id_agresor',     'RESTRICT'),
    ('feminicidio',               'id_lugar',        'lugar_hecho',       'id_lugar',       'RESTRICT'),
    ('feminicidio',               'fecha_hecho',     'tiempo',            'fecha',          'RESTRICT'),
    ('feminicidio_agregado',      'id_localidad',    'localidad',         'id_localidad',   'RESTRICT'),
    ('violencia_previa',          'id_victima',      'victima',           'id_victima',     'CASCADE'),
    ('violencia_previa',          'id_agresor',      'agresor',           'id_agresor',     'CASCADE'),
    ('reincidencia',              'id_agresor',      'agresor',           'id_agresor',     'CASCADE'),
    ('institucion',               'id_localidad',    'localidad',         'id_localidad',   'RESTRICT'),
    ('servicio_psicologico',      'id_institucion',  'institucion',       'id_institucion', 'CASCADE'),
    ('institucion_ruta',          'id_institucion',  'institucion',       'id_institucion', 'CASCADE'),
    ('institucion_ruta',          'id_ruta',         'ruta_atencion',     'id_ruta',        'CASCADE'),
    ('reporte_inicial',           'id_victima',      'victima',           'id_victima',     'CASCADE'),
    ('reporte_inicial',           'fecha_reporte',   'tiempo',            'fecha',          'RESTRICT'),
    ('denuncia',                  'id_victima',      'victima',           'id_victima',     'RESTRICT'),
    ('denuncia',                  'id_institucion',  'institucion',       'id_institucion', 'RESTRICT'),
    ('denuncia',                  'fecha_denuncia',  'tiempo',            'fecha',          'RESTRICT'),
    ('valoracion_riesgo',         'id_denuncia',     'denuncia',          'id_denuncia',    'CASCADE'),
    ('valoracion_riesgo',         'id_institucion',  'institucion',       'id_institucion', 'RESTRICT'),
    ('medida_proteccion',         'id_denuncia',     'denuncia',          'id_denuncia',    'CASCADE'),
    ('medida_proteccion',         'id_institucion',  'institucion',       'id_institucion', 'RESTRICT'),
    ('medida_proteccion',         'fecha_solicitud', 'tiempo',            'fecha',          'RESTRICT'),
    ('seguimiento',               'id_medida',       'medida_proteccion', 'id_medida',      'CASCADE'),
    ('contraorden',               'id_medida',       'medida_proteccion', 'id_medida',      'CASCADE'),
    ('proceso_penal',             'id_denuncia',     'denuncia',          'id_denuncia',    'RESTRICT'),
    ('proceso_penal',             'id_institucion',  'institucion',       'id_institucion', 'RESTRICT'),
    ('actuacion_judicial',        'id_proceso',      'proceso_penal',     'id_proceso',     'CASCADE')
) AS fk(t, c, rt, rc, r);

-- -----------------------------------------------------------------------------
-- 5. Índices de feminicidio_agregado (por si la BD no los tuviera)
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fem_agregado_localidad_anio ON feminicidio_agregado (id_localidad, anio);
CREATE INDEX IF NOT EXISTS idx_fem_agregado_fuente        ON feminicidio_agregado (fuente);

COMMIT;

-- Después de esta migración, ejecutar sql/03_comentarios.sql y
-- sql/99_verificacion.sql para comprobar el resultado.
