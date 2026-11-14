-- =============================================================================
-- 02_crear_indices.sql
-- Índices espaciales GiST + Índices B-tree sobre FKs y columnas de consulta
-- Proyecto: Feminicidio Bogotá — Base de Datos Espacial
-- =============================================================================

-- =============================================================================
-- ÍNDICES ESPACIALES GiST (7 tablas con geometría)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_zona_geom
    ON zona USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_localidad_geom
    ON localidad USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_upl_geom
    ON upl USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_barrio_geom
    ON barrio USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_manzana_geom
    ON manzana USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_lugar_hecho_geom
    ON lugar_hecho USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_institucion_geom
    ON institucion USING GIST (geom);

-- =============================================================================
-- ÍNDICES B-TREE SOBRE FOREIGN KEYS
-- =============================================================================

-- LOCALIDAD
CREATE INDEX IF NOT EXISTS idx_localidad_id_zona
    ON localidad (id_zona);

-- UPL: sin índice de FK (relación N:M con localidad vía ST_Intersects,
--      acelerada por idx_upl_geom e idx_localidad_geom).

-- BARRIO
CREATE INDEX IF NOT EXISTS idx_barrio_id_upl
    ON barrio (id_upl);

-- MANZANA
CREATE INDEX IF NOT EXISTS idx_manzana_id_upl
    ON manzana (id_upl);

CREATE INDEX IF NOT EXISTS idx_manzana_id_estrato
    ON manzana (id_estrato);

-- CONDICION_VIDA
CREATE INDEX IF NOT EXISTS idx_condicion_vida_id_upl
    ON condicion_vida (id_upl);

-- CONDICIONES_TERRITORIALES
CREATE INDEX IF NOT EXISTS idx_condiciones_territoriales_id_upl
    ON condiciones_territoriales (id_upl);

-- LUGAR_HECHO
CREATE INDEX IF NOT EXISTS idx_lugar_hecho_id_barrio
    ON lugar_hecho (id_barrio);

-- INSTITUCION
CREATE INDEX IF NOT EXISTS idx_institucion_id_localidad
    ON institucion (id_localidad);

-- INSTITUCION_RUTA (tabla puente)
CREATE INDEX IF NOT EXISTS idx_institucion_ruta_id_institucion
    ON institucion_ruta (id_institucion);

CREATE INDEX IF NOT EXISTS idx_institucion_ruta_id_ruta
    ON institucion_ruta (id_ruta);

-- SERVICIO_PSICOLOGICO
CREATE INDEX IF NOT EXISTS idx_servicio_psicologico_id_institucion
    ON servicio_psicologico (id_institucion);

-- VICTIMA
CREATE INDEX IF NOT EXISTS idx_victima_id_barrio_res
    ON victima (id_barrio_res);

-- FEMINICIDIO
CREATE INDEX IF NOT EXISTS idx_feminicidio_id_victima
    ON feminicidio (id_victima);

CREATE INDEX IF NOT EXISTS idx_feminicidio_id_agresor
    ON feminicidio (id_agresor);

CREATE INDEX IF NOT EXISTS idx_feminicidio_id_lugar
    ON feminicidio (id_lugar);

CREATE INDEX IF NOT EXISTS idx_feminicidio_fecha_hecho
    ON feminicidio (fecha_hecho);

-- FEMINICIDIO_AGREGADO (base de todos los indicadores del observatorio)
CREATE INDEX IF NOT EXISTS idx_fem_agregado_localidad_anio
    ON feminicidio_agregado (id_localidad, anio);

CREATE INDEX IF NOT EXISTS idx_fem_agregado_fuente
    ON feminicidio_agregado (fuente);

-- VICTIMA_INDIRECTA
CREATE INDEX IF NOT EXISTS idx_victima_indirecta_id_feminicidio
    ON victima_indirecta (id_feminicidio);

-- RED_APOYO
CREATE INDEX IF NOT EXISTS idx_red_apoyo_id_victima
    ON red_apoyo (id_victima);

-- VIOLENCIA_PREVIA
CREATE INDEX IF NOT EXISTS idx_violencia_previa_id_victima
    ON violencia_previa (id_victima);

CREATE INDEX IF NOT EXISTS idx_violencia_previa_id_agresor
    ON violencia_previa (id_agresor);

-- REINCIDENCIA
CREATE INDEX IF NOT EXISTS idx_reincidencia_id_agresor
    ON reincidencia (id_agresor);

-- REPORTE_INICIAL
CREATE INDEX IF NOT EXISTS idx_reporte_inicial_id_victima
    ON reporte_inicial (id_victima);

CREATE INDEX IF NOT EXISTS idx_reporte_inicial_fecha_reporte
    ON reporte_inicial (fecha_reporte);

-- DENUNCIA
CREATE INDEX IF NOT EXISTS idx_denuncia_id_victima
    ON denuncia (id_victima);

CREATE INDEX IF NOT EXISTS idx_denuncia_id_institucion
    ON denuncia (id_institucion);

CREATE INDEX IF NOT EXISTS idx_denuncia_fecha_denuncia
    ON denuncia (fecha_denuncia);

-- VALORACION_RIESGO
CREATE INDEX IF NOT EXISTS idx_valoracion_riesgo_id_denuncia
    ON valoracion_riesgo (id_denuncia);

CREATE INDEX IF NOT EXISTS idx_valoracion_riesgo_id_institucion
    ON valoracion_riesgo (id_institucion);

-- MEDIDA_PROTECCION
CREATE INDEX IF NOT EXISTS idx_medida_proteccion_id_denuncia
    ON medida_proteccion (id_denuncia);

CREATE INDEX IF NOT EXISTS idx_medida_proteccion_id_institucion
    ON medida_proteccion (id_institucion);

CREATE INDEX IF NOT EXISTS idx_medida_proteccion_fecha_solicitud
    ON medida_proteccion (fecha_solicitud);

-- SEGUIMIENTO
CREATE INDEX IF NOT EXISTS idx_seguimiento_id_medida
    ON seguimiento (id_medida);

-- CONTRAORDEN
CREATE INDEX IF NOT EXISTS idx_contraorden_id_medida
    ON contraorden (id_medida);

-- PROCESO_PENAL
CREATE INDEX IF NOT EXISTS idx_proceso_penal_id_denuncia
    ON proceso_penal (id_denuncia);

CREATE INDEX IF NOT EXISTS idx_proceso_penal_id_institucion
    ON proceso_penal (id_institucion);

-- ACTUACION_JUDICIAL
CREATE INDEX IF NOT EXISTS idx_actuacion_judicial_id_proceso
    ON actuacion_judicial (id_proceso);

-- =============================================================================
-- Este script: 7 GiST + 38 B-tree = 45 índices "idx_*".
-- Más los índices implícitos que crea 01_crear_tablas.sql:
--   30 PRIMARY KEY + 4 UNIQUE (localidad.codigo_localidad, upl.codigo_upl,
--   estrato.nivel, feminicidio_agregado(id_localidad, anio, fuente))
-- Total en la BD: 79 índices (7 GiST + 72 B-tree).
-- =============================================================================
