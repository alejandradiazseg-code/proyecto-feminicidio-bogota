-- =============================================================================
-- 01_crear_tablas.sql
-- Modelo físico: 28 entidades del MER + 1 tabla puente (institucion_ruta)
-- Proyecto: Feminicidio Bogotá — Base de Datos Espacial
-- SRID: 4326 (WGS84) para todas las geometrías
-- Nota: UPZ renombrada a UPL (Unidades de Planeamiento Local, Bogotá 2022+)
-- =============================================================================

-- =============================================================================
-- ROLLBACK BLOCK: permite re-ejecución limpia del script
-- =============================================================================
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

-- Asegurar que PostGIS esté habilitado
CREATE EXTENSION IF NOT EXISTS postgis;

-- =============================================================================
-- GRUPO 1: Catálogos sin FKs
-- =============================================================================

-- 1. ZONA
CREATE TABLE IF NOT EXISTS zona (
    id_zona     SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    descripcion TEXT,
    geom        GEOMETRY(MULTIPOLYGON, 4326)
);

-- 2. ESTRATO
CREATE TABLE IF NOT EXISTS estrato (
    id_estrato  SERIAL PRIMARY KEY,
    nivel       INTEGER NOT NULL CHECK (nivel IN (1, 2, 3, 4, 5, 6)),
    descripcion VARCHAR(100)
);

-- 3. TIEMPO (PK natural: fecha DATE)
CREATE TABLE IF NOT EXISTS tiempo (
    fecha           DATE PRIMARY KEY,
    anio            INTEGER NOT NULL,
    mes             INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    trimestre       INTEGER NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    dia_semana      VARCHAR(15) NOT NULL,
    es_fin_de_semana BOOLEAN NOT NULL DEFAULT FALSE
);

-- =============================================================================
-- GRUPO 2: Territorio jerárquico
-- =============================================================================

-- 4. LOCALIDAD
CREATE TABLE IF NOT EXISTS localidad (
    id_localidad     SERIAL PRIMARY KEY,
    id_zona          INTEGER NOT NULL REFERENCES zona(id_zona),
    codigo_localidad VARCHAR(10) NOT NULL UNIQUE,
    nombre           VARCHAR(100) NOT NULL,
    area_km2         NUMERIC(10, 2),
    poblacion_fem    INTEGER,
    geom             GEOMETRY(MULTIPOLYGON, 4326)
);

-- 5. UPL (antes UPZ — Unidades de Planeamiento Local)
CREATE TABLE IF NOT EXISTS upl (
    id_upl       SERIAL PRIMARY KEY,
    id_localidad INTEGER NOT NULL REFERENCES localidad(id_localidad),
    codigo_upl   VARCHAR(10) NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    tipo_upl     VARCHAR(50),
    geom         GEOMETRY(POLYGON, 4326)
);

-- 6. BARRIO
CREATE TABLE IF NOT EXISTS barrio (
    id_barrio SERIAL PRIMARY KEY,
    id_upl    INTEGER NOT NULL REFERENCES upl(id_upl),
    nombre    VARCHAR(100) NOT NULL,
    geom      GEOMETRY(POLYGON, 4326)
);

-- 7. MANZANA
CREATE TABLE IF NOT EXISTS manzana (
    id_manzana     SERIAL PRIMARY KEY,
    id_upl         INTEGER NOT NULL REFERENCES upl(id_upl),
    id_estrato     INTEGER NOT NULL REFERENCES estrato(id_estrato),
    codigo_manzana VARCHAR(30),
    geom           GEOMETRY(POLYGON, 4326)
);

-- =============================================================================
-- GRUPO 3: Sociodemográfico de UPL
-- =============================================================================

-- 8. CONDICION_VIDA
CREATE TABLE IF NOT EXISTS condicion_vida (
    id_condicion        SERIAL PRIMARY KEY,
    id_upl              INTEGER NOT NULL REFERENCES upl(id_upl),
    anio_medicion       INTEGER NOT NULL,
    ipm                 NUMERIC(5, 4),
    desempleo_fem       NUMERIC(5, 4),
    cobertura_educacion NUMERIC(5, 4),
    acceso_salud        NUMERIC(5, 4)
);

-- 9. CONDICIONES_TERRITORIALES
CREATE TABLE IF NOT EXISTS condiciones_territoriales (
    id_cond_terr              SERIAL PRIMARY KEY,
    id_upl                    INTEGER NOT NULL REFERENCES upl(id_upl),
    anio_medicion             INTEGER NOT NULL,
    indice_seguridad_nocturna NUMERIC(5, 4),
    cobertura_iluminacion     NUMERIC(5, 4),
    accesibilidad_transporte  NUMERIC(5, 4),
    densidad_institucional    NUMERIC(5, 4),
    tipo_entorno_urbano       VARCHAR(50)
);

-- =============================================================================
-- GRUPO 4: Lugar del hecho
-- =============================================================================

-- 10. LUGAR_HECHO
CREATE TABLE IF NOT EXISTS lugar_hecho (
    id_lugar       SERIAL PRIMARY KEY,
    id_barrio      INTEGER NOT NULL REFERENCES barrio(id_barrio),
    direccion_aprox VARCHAR(200),
    tipo_lugar     VARCHAR(80),
    geom           GEOMETRY(POINT, 4326)
);

-- =============================================================================
-- GRUPO 5: Institucional
-- =============================================================================

-- 11. INSTITUCION
CREATE TABLE IF NOT EXISTS institucion (
    id_institucion  SERIAL PRIMARY KEY,
    id_localidad    INTEGER NOT NULL REFERENCES localidad(id_localidad),
    tipo            VARCHAR(80) NOT NULL,
    nombre          VARCHAR(200) NOT NULL,
    direccion       VARCHAR(200),
    telefono        VARCHAR(30),
    horario_atencion VARCHAR(100),
    geom            GEOMETRY(POINT, 4326)
);

-- 12. RUTA_ATENCION
CREATE TABLE IF NOT EXISTS ruta_atencion (
    id_ruta                  SERIAL PRIMARY KEY,
    nombre_ruta              VARCHAR(150) NOT NULL,
    tipo_violencia_aplicable VARCHAR(100),
    entidad_coordinadora     VARCHAR(150)
);

-- 13. INSTITUCION_RUTA (tabla puente M:N — no parte del MER conceptual original)
CREATE TABLE IF NOT EXISTS institucion_ruta (
    id_institucion INTEGER NOT NULL REFERENCES institucion(id_institucion),
    id_ruta        INTEGER NOT NULL REFERENCES ruta_atencion(id_ruta),
    PRIMARY KEY (id_institucion, id_ruta)
);

-- 14. SERVICIO_PSICOLOGICO
CREATE TABLE IF NOT EXISTS servicio_psicologico (
    id_servicio    SERIAL PRIMARY KEY,
    id_institucion INTEGER NOT NULL REFERENCES institucion(id_institucion),
    tipo_atencion  VARCHAR(100),
    modalidad      VARCHAR(80)
);

-- =============================================================================
-- GRUPO 6: Personas
-- =============================================================================

-- 15. VICTIMA
CREATE TABLE IF NOT EXISTS victima (
    id_victima          SERIAL PRIMARY KEY,
    id_barrio_res       INTEGER REFERENCES barrio(id_barrio),
    edad_al_hecho       INTEGER,
    nivel_educativo     VARCHAR(80),
    ocupacion           VARCHAR(100),
    etnia               VARCHAR(80),
    condicion_migratoria VARCHAR(80),
    tiene_discapacidad  BOOLEAN DEFAULT FALSE,
    tiene_hijos         BOOLEAN DEFAULT FALSE,
    numero_hijos        INTEGER DEFAULT 0
);

-- 16. AGRESOR
CREATE TABLE IF NOT EXISTS agresor (
    id_agresor              SERIAL PRIMARY KEY,
    edad_al_hecho           INTEGER,
    ocupacion               VARCHAR(100),
    antecedentes_violencia  BOOLEAN DEFAULT FALSE,
    porta_arma              BOOLEAN DEFAULT FALSE,
    condicion_especial      VARCHAR(100),
    estado_actual           VARCHAR(80)
);

-- =============================================================================
-- GRUPO 7: Hecho central y relaciones
-- =============================================================================

-- 17. FEMINICIDIO
CREATE TABLE IF NOT EXISTS feminicidio (
    id_feminicidio      SERIAL PRIMARY KEY,
    id_victima          INTEGER NOT NULL REFERENCES victima(id_victima),
    id_agresor          INTEGER NOT NULL REFERENCES agresor(id_agresor),
    id_lugar            INTEGER NOT NULL REFERENCES lugar_hecho(id_lugar),
    fecha_hecho         DATE NOT NULL REFERENCES tiempo(fecha),
    hora_hecho          TIME,
    tipo                VARCHAR(80),
    modalidad           VARCHAR(80),
    tipificado_fiscalia BOOLEAN DEFAULT FALSE
);

-- 18. VICTIMA_INDIRECTA
CREATE TABLE IF NOT EXISTS victima_indirecta (
    id_vi            SERIAL PRIMARY KEY,
    id_feminicidio   INTEGER NOT NULL REFERENCES feminicidio(id_feminicidio),
    edad_al_hecho    INTEGER,
    parentesco       VARCHAR(80),
    era_menor        BOOLEAN DEFAULT FALSE,
    presencio_hecho  BOOLEAN DEFAULT FALSE
);

-- 19. RED_APOYO
CREATE TABLE IF NOT EXISTS red_apoyo (
    id_red                  SERIAL PRIMARY KEY,
    id_victima              INTEGER NOT NULL REFERENCES victima(id_victima),
    tipo_red                VARCHAR(80),
    conocimiento_violencia  BOOLEAN DEFAULT FALSE,
    intento_proteccion      BOOLEAN DEFAULT FALSE
);

-- 20. VIOLENCIA_PREVIA
CREATE TABLE IF NOT EXISTS violencia_previa (
    id_violencia        SERIAL PRIMARY KEY,
    id_victima          INTEGER NOT NULL REFERENCES victima(id_victima),
    id_agresor          INTEGER NOT NULL REFERENCES agresor(id_agresor),
    tipo                VARCHAR(80),
    frecuencia          VARCHAR(50),
    duracion_aprox_meses INTEGER
);

-- 21. REINCIDENCIA
CREATE TABLE IF NOT EXISTS reincidencia (
    id_reincidencia        SERIAL PRIMARY KEY,
    id_agresor             INTEGER NOT NULL REFERENCES agresor(id_agresor),
    conteo_denuncias       INTEGER DEFAULT 0,
    ventana_temporal_meses INTEGER,
    fecha_ultima_agresion  DATE
);

-- =============================================================================
-- GRUPO 8: Proceso (ruta judicial)
-- =============================================================================

-- 22. REPORTE_INICIAL
CREATE TABLE IF NOT EXISTS reporte_inicial (
    id_reporte          SERIAL PRIMARY KEY,
    id_victima          INTEGER NOT NULL REFERENCES victima(id_victima),
    fecha_reporte       DATE REFERENCES tiempo(fecha),
    canal               VARCHAR(80),
    tipo_hecho_reportado VARCHAR(100),
    resultado           VARCHAR(100)
);

-- 23. DENUNCIA
CREATE TABLE IF NOT EXISTS denuncia (
    id_denuncia       SERIAL PRIMARY KEY,
    id_victima        INTEGER NOT NULL REFERENCES victima(id_victima),
    id_institucion    INTEGER NOT NULL REFERENCES institucion(id_institucion),
    fecha_denuncia    DATE REFERENCES tiempo(fecha),
    entidad_receptora VARCHAR(150),
    tipo_delito       VARCHAR(100),
    estado            VARCHAR(80)
);

-- 24. VALORACION_RIESGO
CREATE TABLE IF NOT EXISTS valoracion_riesgo (
    id_valoracion      SERIAL PRIMARY KEY,
    id_denuncia        INTEGER NOT NULL REFERENCES denuncia(id_denuncia),
    id_institucion     INTEGER NOT NULL REFERENCES institucion(id_institucion),
    fecha_valoracion   DATE,
    nivel_riesgo       VARCHAR(50),
    entidad_valoradora VARCHAR(150)
);

-- 25. MEDIDA_PROTECCION
CREATE TABLE IF NOT EXISTS medida_proteccion (
    id_medida          SERIAL PRIMARY KEY,
    id_denuncia        INTEGER NOT NULL REFERENCES denuncia(id_denuncia),
    id_institucion     INTEGER NOT NULL REFERENCES institucion(id_institucion),
    fecha_solicitud    DATE REFERENCES tiempo(fecha),
    fecha_otorgamiento DATE,
    tipo_medida        VARCHAR(100),
    estado             VARCHAR(80)
);

-- 26. SEGUIMIENTO
CREATE TABLE IF NOT EXISTS seguimiento (
    id_seguimiento      SERIAL PRIMARY KEY,
    id_medida           INTEGER NOT NULL REFERENCES medida_proteccion(id_medida),
    fecha_seguimiento   DATE,
    resultado           VARCHAR(150),
    entidad_responsable VARCHAR(150)
);

-- 27. CONTRAORDEN
CREATE TABLE IF NOT EXISTS contraorden (
    id_contraorden   SERIAL PRIMARY KEY,
    id_medida        INTEGER NOT NULL REFERENCES medida_proteccion(id_medida),
    fecha_contraorden DATE,
    tipo             VARCHAR(80),
    motivo           TEXT,
    entidad_emisora  VARCHAR(150)
);

-- 28. PROCESO_PENAL
CREATE TABLE IF NOT EXISTS proceso_penal (
    id_proceso     SERIAL PRIMARY KEY,
    id_denuncia    INTEGER NOT NULL REFERENCES denuncia(id_denuncia),
    id_institucion INTEGER NOT NULL REFERENCES institucion(id_institucion),
    estado_actual  VARCHAR(80),
    fecha_apertura DATE,
    fecha_sentencia DATE
);

-- 29. ACTUACION_JUDICIAL
CREATE TABLE IF NOT EXISTS actuacion_judicial (
    id_actuacion SERIAL PRIMARY KEY,
    id_proceso   INTEGER NOT NULL REFERENCES proceso_penal(id_proceso),
    fecha        DATE,
    tipo_acto    VARCHAR(100),
    resultado    VARCHAR(150)
);

-- =============================================================================
-- Fin del DDL — 29 tablas creadas
-- =============================================================================
