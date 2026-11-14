-- =============================================================================
-- 01_crear_tablas.sql
-- Modelo físico: 30 tablas (29 del MER + feminicidio_agregado como tabla auxiliar)
-- Proyecto: Feminicidio Bogotá — Base de Datos Espacial
-- Motor: PostgreSQL 16 + PostGIS 3.4 · SRID 4326 (WGS84) en todas las geometrías
--
-- Fuente de verdad: "Modelo Físico" y "Diccionario de Datos" v1.0 (abril 2026).
-- Decisiones clave reflejadas aquí:
--   * UPL ↔ Localidad es N:M y se resuelve con ST_Intersects (upl NO tiene
--     columna id_localidad ni FK física hacia localidad).
--   * feminicidio_agregado almacena los conteos públicos por localidad/año/fuente.
--   * Reglas ON DELETE según la tabla de integridad referencial del Modelo Físico.
--
-- ADVERTENCIA: este script BORRA y recrea todas las tablas. Úsalo solo para una
-- instalación nueva. Para actualizar una BD existente sin perder datos, usa
-- sql/migraciones/001_alinear_modelo_fisico.sql
-- =============================================================================

BEGIN;

DROP TABLE IF EXISTS actuacion_judicial CASCADE;
DROP TABLE IF EXISTS proceso_penal CASCADE;
DROP TABLE IF EXISTS contraorden CASCADE;
DROP TABLE IF EXISTS seguimiento CASCADE;
DROP TABLE IF EXISTS medida_proteccion CASCADE;
DROP TABLE IF EXISTS valoracion_riesgo CASCADE;
DROP TABLE IF EXISTS denuncia CASCADE;
DROP TABLE IF EXISTS reporte_inicial CASCADE;
DROP TABLE IF EXISTS reincidencia CASCADE;
DROP TABLE IF EXISTS violencia_previa CASCADE;
DROP TABLE IF EXISTS red_apoyo CASCADE;
DROP TABLE IF EXISTS victima_indirecta CASCADE;
DROP TABLE IF EXISTS feminicidio CASCADE;
DROP TABLE IF EXISTS feminicidio_agregado CASCADE;
DROP TABLE IF EXISTS agresor CASCADE;
DROP TABLE IF EXISTS victima CASCADE;
DROP TABLE IF EXISTS servicio_psicologico CASCADE;
DROP TABLE IF EXISTS institucion_ruta CASCADE;
DROP TABLE IF EXISTS ruta_atencion CASCADE;
DROP TABLE IF EXISTS institucion CASCADE;
DROP TABLE IF EXISTS lugar_hecho CASCADE;
DROP TABLE IF EXISTS condiciones_territoriales CASCADE;
DROP TABLE IF EXISTS condicion_vida CASCADE;
DROP TABLE IF EXISTS manzana CASCADE;
DROP TABLE IF EXISTS barrio CASCADE;
DROP TABLE IF EXISTS upl CASCADE;
DROP TABLE IF EXISTS localidad CASCADE;
DROP TABLE IF EXISTS tiempo CASCADE;
DROP TABLE IF EXISTS estrato CASCADE;
DROP TABLE IF EXISTS zona CASCADE;

CREATE EXTENSION IF NOT EXISTS postgis;

-- =============================================================================
-- MÓDULO TERRITORIO
-- =============================================================================

-- 1. ZONA
CREATE TABLE zona (
    id_zona     SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    geom        GEOMETRY(MULTIPOLYGON, 4326)
);

-- 2. ESTRATO (catálogo estático de 6 niveles)
CREATE TABLE estrato (
    id_estrato  SERIAL PRIMARY KEY,
    nivel       INTEGER NOT NULL CHECK (nivel BETWEEN 1 AND 6),
    descripcion VARCHAR(100),
    CONSTRAINT estrato_nivel_key UNIQUE (nivel)
);

-- 3. LOCALIDAD
CREATE TABLE localidad (
    id_localidad     SERIAL PRIMARY KEY,
    id_zona          INTEGER NOT NULL
                     REFERENCES zona(id_zona) ON DELETE RESTRICT,
    codigo_localidad VARCHAR(10) NOT NULL UNIQUE,
    nombre           VARCHAR(100) NOT NULL,
    area_km2         NUMERIC(10, 2),
    poblacion_fem    INTEGER,
    geom             GEOMETRY(MULTIPOLYGON, 4326)
);

-- 4. UPL (Unidades de Planeamiento Local, POT Decreto 555 de 2021)
--    Relación N:M con localidad resuelta por ST_Intersects (sin FK física).
CREATE TABLE upl (
    id_upl     SERIAL PRIMARY KEY,
    codigo_upl VARCHAR(10) NOT NULL UNIQUE,
    nombre     VARCHAR(100) NOT NULL,
    tipo_upl   VARCHAR(50),
    geom       GEOMETRY(MULTIPOLYGON, 4326)
);

-- 5. BARRIO
CREATE TABLE barrio (
    id_barrio SERIAL PRIMARY KEY,
    id_upl    INTEGER NOT NULL
              REFERENCES upl(id_upl) ON DELETE RESTRICT,
    nombre    VARCHAR(100) NOT NULL,
    geom      GEOMETRY(POLYGON, 4326)
);

-- 6. MANZANA
CREATE TABLE manzana (
    id_manzana     SERIAL PRIMARY KEY,
    id_upl         INTEGER NOT NULL
                   REFERENCES upl(id_upl) ON DELETE RESTRICT,
    id_estrato     INTEGER NOT NULL
                   REFERENCES estrato(id_estrato) ON DELETE RESTRICT,
    codigo_manzana VARCHAR(30),
    geom           GEOMETRY(POLYGON, 4326)
);

-- 7. CONDICION_VIDA
CREATE TABLE condicion_vida (
    id_condicion        SERIAL PRIMARY KEY,
    id_upl              INTEGER NOT NULL
                        REFERENCES upl(id_upl) ON DELETE RESTRICT,
    anio_medicion       INTEGER NOT NULL,
    ipm                 NUMERIC(5, 4) CHECK (ipm BETWEEN 0 AND 1),
    desempleo_fem       NUMERIC(5, 4) CHECK (desempleo_fem BETWEEN 0 AND 1),
    cobertura_educacion NUMERIC(5, 4),
    acceso_salud        NUMERIC(5, 4)
);

-- 8. CONDICIONES_TERRITORIALES (índice de seguridad nocturna SDMujer)
CREATE TABLE condiciones_territoriales (
    id_cond_terr              SERIAL PRIMARY KEY,
    id_upl                    INTEGER NOT NULL
                              REFERENCES upl(id_upl) ON DELETE RESTRICT,
    anio_medicion             INTEGER NOT NULL CHECK (anio_medicion >= 2010),
    indice_seguridad_nocturna NUMERIC(5, 4)
                              CHECK (indice_seguridad_nocturna BETWEEN 1 AND 5),
    cobertura_iluminacion     NUMERIC(5, 4)
                              CHECK (cobertura_iluminacion BETWEEN 0 AND 1),
    accesibilidad_transporte  NUMERIC(5, 4)
                              CHECK (accesibilidad_transporte BETWEEN 0 AND 1),
    densidad_institucional    NUMERIC(5, 4),
    tipo_entorno_urbano       VARCHAR(50)
);

-- 9. LUGAR_HECHO
CREATE TABLE lugar_hecho (
    id_lugar        SERIAL PRIMARY KEY,
    id_barrio       INTEGER NOT NULL
                    REFERENCES barrio(id_barrio) ON DELETE RESTRICT,
    direccion_aprox VARCHAR(200),
    tipo_lugar      VARCHAR(80),
    geom            GEOMETRY(POINT, 4326)
);

-- =============================================================================
-- MÓDULO TIEMPO
-- =============================================================================

-- 10. TIEMPO (PK natural: fecha)
CREATE TABLE tiempo (
    fecha            DATE PRIMARY KEY,
    anio             INTEGER NOT NULL CHECK (anio BETWEEN 2010 AND 2030),
    mes              INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    trimestre        INTEGER NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    dia_semana       VARCHAR(15) NOT NULL,
    es_fin_de_semana BOOLEAN NOT NULL DEFAULT FALSE
);

-- =============================================================================
-- MÓDULO PERSONA
-- =============================================================================

-- 11. VICTIMA
CREATE TABLE victima (
    id_victima           SERIAL PRIMARY KEY,
    id_barrio_res        INTEGER
                         REFERENCES barrio(id_barrio) ON DELETE SET NULL,
    edad_al_hecho        INTEGER CHECK (edad_al_hecho >= 0),
    nivel_educativo      VARCHAR(80),
    ocupacion            VARCHAR(100),
    etnia                VARCHAR(80),
    condicion_migratoria VARCHAR(80),
    tiene_discapacidad   BOOLEAN DEFAULT FALSE,
    tiene_hijos          BOOLEAN DEFAULT FALSE,
    numero_hijos         INTEGER DEFAULT 0 CHECK (numero_hijos >= 0)
);

-- 12. AGRESOR
CREATE TABLE agresor (
    id_agresor             SERIAL PRIMARY KEY,
    edad_al_hecho          INTEGER,
    ocupacion              VARCHAR(100),
    antecedentes_violencia BOOLEAN DEFAULT FALSE,
    porta_arma             BOOLEAN DEFAULT FALSE,
    condicion_especial     VARCHAR(100),
    estado_actual          VARCHAR(80)
);

-- 13. RED_APOYO
CREATE TABLE red_apoyo (
    id_red                 SERIAL PRIMARY KEY,
    id_victima             INTEGER NOT NULL
                           REFERENCES victima(id_victima) ON DELETE CASCADE,
    tipo_red               VARCHAR(80),
    conocimiento_violencia BOOLEAN DEFAULT FALSE,
    intento_proteccion     BOOLEAN DEFAULT FALSE
);

-- =============================================================================
-- MÓDULO HECHO
-- =============================================================================

-- 14. FEMINICIDIO (registro individual; vacía hasta tener datos individuales)
CREATE TABLE feminicidio (
    id_feminicidio      SERIAL PRIMARY KEY,
    id_victima          INTEGER NOT NULL
                        REFERENCES victima(id_victima) ON DELETE RESTRICT,
    id_agresor          INTEGER NOT NULL
                        REFERENCES agresor(id_agresor) ON DELETE RESTRICT,
    id_lugar            INTEGER NOT NULL
                        REFERENCES lugar_hecho(id_lugar) ON DELETE RESTRICT,
    fecha_hecho         DATE NOT NULL
                        REFERENCES tiempo(fecha) ON DELETE RESTRICT,
    hora_hecho          TIME,
    tipo                VARCHAR(80),
    modalidad           VARCHAR(80),
    tipificado_fiscalia BOOLEAN DEFAULT FALSE
);

-- 15. FEMINICIDIO_AGREGADO (tabla auxiliar: conteos públicos por localidad/año/fuente)
CREATE TABLE feminicidio_agregado (
    id_agregado   SERIAL PRIMARY KEY,
    id_localidad  INTEGER NOT NULL
                  REFERENCES localidad(id_localidad) ON DELETE RESTRICT,
    anio          INTEGER NOT NULL CHECK (anio BETWEEN 2010 AND 2030),
    conteo_casos  INTEGER NOT NULL DEFAULT 0 CHECK (conteo_casos >= 0),
    fuente        VARCHAR(50) NOT NULL,
    tasa_por_100k NUMERIC(8, 4),
    fecha_corte   DATE,
    observaciones TEXT,
    CONSTRAINT feminicidio_agregado_id_localidad_anio_fuente_key
        UNIQUE (id_localidad, anio, fuente)
);

-- 16. VICTIMA_INDIRECTA
CREATE TABLE victima_indirecta (
    id_vi           SERIAL PRIMARY KEY,
    id_feminicidio  INTEGER NOT NULL
                    REFERENCES feminicidio(id_feminicidio) ON DELETE CASCADE,
    edad_al_hecho   INTEGER,
    parentesco      VARCHAR(80),
    era_menor       BOOLEAN DEFAULT FALSE,
    presencio_hecho BOOLEAN DEFAULT FALSE
);

-- 17. VIOLENCIA_PREVIA
CREATE TABLE violencia_previa (
    id_violencia         SERIAL PRIMARY KEY,
    id_victima           INTEGER NOT NULL
                         REFERENCES victima(id_victima) ON DELETE CASCADE,
    id_agresor           INTEGER NOT NULL
                         REFERENCES agresor(id_agresor) ON DELETE CASCADE,
    tipo                 VARCHAR(80),
    frecuencia           VARCHAR(50),
    duracion_aprox_meses INTEGER
);

-- 18. REINCIDENCIA
CREATE TABLE reincidencia (
    id_reincidencia        SERIAL PRIMARY KEY,
    id_agresor             INTEGER NOT NULL
                           REFERENCES agresor(id_agresor) ON DELETE CASCADE,
    conteo_denuncias       INTEGER DEFAULT 0,
    ventana_temporal_meses INTEGER,
    fecha_ultima_agresion  DATE
);

-- =============================================================================
-- MÓDULO INSTITUCIONAL
-- =============================================================================

-- 19. INSTITUCION
CREATE TABLE institucion (
    id_institucion   SERIAL PRIMARY KEY,
    id_localidad     INTEGER NOT NULL
                     REFERENCES localidad(id_localidad) ON DELETE RESTRICT,
    tipo             VARCHAR(80) NOT NULL
                     CHECK (tipo IN ('COMISARIA_FAMILIA', 'CAI',
                                     'CASA_IGUALDAD', 'CASA_JUSTICIA')),
    nombre           VARCHAR(200) NOT NULL,
    direccion        VARCHAR(200),
    telefono         VARCHAR(30),
    horario_atencion VARCHAR(100),
    geom             GEOMETRY(POINT, 4326)
);

-- 20. SERVICIO_PSICOLOGICO
CREATE TABLE servicio_psicologico (
    id_servicio    SERIAL PRIMARY KEY,
    id_institucion INTEGER NOT NULL
                   REFERENCES institucion(id_institucion) ON DELETE CASCADE,
    tipo_atencion  VARCHAR(100),
    modalidad      VARCHAR(80)
);

-- 21. RUTA_ATENCION
CREATE TABLE ruta_atencion (
    id_ruta                  SERIAL PRIMARY KEY,
    nombre_ruta              VARCHAR(150) NOT NULL,
    tipo_violencia_aplicable VARCHAR(100),
    entidad_coordinadora     VARCHAR(150)
);

-- 22. INSTITUCION_RUTA (puente N:M)
CREATE TABLE institucion_ruta (
    id_institucion INTEGER NOT NULL
                   REFERENCES institucion(id_institucion) ON DELETE CASCADE,
    id_ruta        INTEGER NOT NULL
                   REFERENCES ruta_atencion(id_ruta) ON DELETE CASCADE,
    PRIMARY KEY (id_institucion, id_ruta)
);

-- 23. REPORTE_INICIAL
CREATE TABLE reporte_inicial (
    id_reporte           SERIAL PRIMARY KEY,
    id_victima           INTEGER NOT NULL
                         REFERENCES victima(id_victima) ON DELETE CASCADE,
    fecha_reporte        DATE
                         REFERENCES tiempo(fecha) ON DELETE RESTRICT,
    canal                VARCHAR(80),
    tipo_hecho_reportado VARCHAR(100),
    resultado            VARCHAR(100)
);

-- 24. DENUNCIA
CREATE TABLE denuncia (
    id_denuncia       SERIAL PRIMARY KEY,
    id_victima        INTEGER NOT NULL
                      REFERENCES victima(id_victima) ON DELETE RESTRICT,
    id_institucion    INTEGER NOT NULL
                      REFERENCES institucion(id_institucion) ON DELETE RESTRICT,
    fecha_denuncia    DATE
                      REFERENCES tiempo(fecha) ON DELETE RESTRICT,
    entidad_receptora VARCHAR(150),
    tipo_delito       VARCHAR(100),
    estado            VARCHAR(80)
);

-- 25. VALORACION_RIESGO
CREATE TABLE valoracion_riesgo (
    id_valoracion      SERIAL PRIMARY KEY,
    id_denuncia        INTEGER NOT NULL
                       REFERENCES denuncia(id_denuncia) ON DELETE CASCADE,
    id_institucion     INTEGER NOT NULL
                       REFERENCES institucion(id_institucion) ON DELETE RESTRICT,
    fecha_valoracion   DATE,
    nivel_riesgo       VARCHAR(50)
                       CHECK (nivel_riesgo IN ('Bajo', 'Medio', 'Alto', 'Extremo')),
    entidad_valoradora VARCHAR(150)
);

-- 26. MEDIDA_PROTECCION
CREATE TABLE medida_proteccion (
    id_medida          SERIAL PRIMARY KEY,
    id_denuncia        INTEGER NOT NULL
                       REFERENCES denuncia(id_denuncia) ON DELETE CASCADE,
    id_institucion     INTEGER NOT NULL
                       REFERENCES institucion(id_institucion) ON DELETE RESTRICT,
    fecha_solicitud    DATE
                       REFERENCES tiempo(fecha) ON DELETE RESTRICT,
    fecha_otorgamiento DATE,
    tipo_medida        VARCHAR(100),
    estado             VARCHAR(80)
);

-- 27. SEGUIMIENTO
CREATE TABLE seguimiento (
    id_seguimiento      SERIAL PRIMARY KEY,
    id_medida           INTEGER NOT NULL
                        REFERENCES medida_proteccion(id_medida) ON DELETE CASCADE,
    fecha_seguimiento   DATE,
    resultado           VARCHAR(150),
    entidad_responsable VARCHAR(150)
);

-- 28. CONTRAORDEN
CREATE TABLE contraorden (
    id_contraorden    SERIAL PRIMARY KEY,
    id_medida         INTEGER NOT NULL
                      REFERENCES medida_proteccion(id_medida) ON DELETE CASCADE,
    fecha_contraorden DATE,
    tipo              VARCHAR(80),
    motivo            TEXT,
    entidad_emisora   VARCHAR(150)
);

-- 29. PROCESO_PENAL
CREATE TABLE proceso_penal (
    id_proceso      SERIAL PRIMARY KEY,
    id_denuncia     INTEGER NOT NULL
                    REFERENCES denuncia(id_denuncia) ON DELETE RESTRICT,
    id_institucion  INTEGER NOT NULL
                    REFERENCES institucion(id_institucion) ON DELETE RESTRICT,
    estado_actual   VARCHAR(80)
                    CHECK (estado_actual IN ('Indagación', 'Investigación', 'Juicio',
                                             'Ejecución de penas',
                                             'Terminación anticipada', 'Precluido')),
    fecha_apertura  DATE,
    fecha_sentencia DATE
);

-- 30. ACTUACION_JUDICIAL
CREATE TABLE actuacion_judicial (
    id_actuacion SERIAL PRIMARY KEY,
    id_proceso   INTEGER NOT NULL
                 REFERENCES proceso_penal(id_proceso) ON DELETE CASCADE,
    fecha        DATE,
    tipo_acto    VARCHAR(100),
    resultado    VARCHAR(150)
);

COMMIT;

-- =============================================================================
-- Fin del DDL — 30 tablas. Siguiente paso: 02_crear_indices.sql
-- =============================================================================
