-- =============================================================================
-- 03_comentarios.sql
-- COMMENT ON TABLE y COMMENT ON COLUMN para documentación in-DB
-- Proyecto: Feminicidio Bogotá — Base de Datos Espacial
-- =============================================================================

-- =============================================================================
-- COMMENT ON TABLE
-- =============================================================================

COMMENT ON TABLE zona IS
  'División macro de Bogotá en zonas (Norte, Sur, etc.) para análisis comparativo.';

COMMENT ON TABLE estrato IS
  'Catálogo de estratos socioeconómicos de Bogotá (1 a 6).';

COMMENT ON TABLE tiempo IS
  'Dimensión temporal (calendario). PK natural: fecha. Permite análisis por año, mes, trimestre, día de semana.';

COMMENT ON TABLE localidad IS
  'Localidades administrativas de Bogotá (20 localidades). Contiene geometría y datos demográficos.';

COMMENT ON TABLE upl IS
  'Unidades de Planeamiento Local (antes UPZ). Subdivisión de localidades vigente desde 2022.';

COMMENT ON TABLE barrio IS
  'Barrios dentro de cada UPL. Nivel territorial más granular con geometría poligonal.';

COMMENT ON TABLE manzana IS
  'Manzanas catastrales vinculadas a UPL y estrato socioeconómico.';

COMMENT ON TABLE condicion_vida IS
  'Indicadores de calidad de vida por UPL y año: IPM, desempleo femenino, cobertura educativa, acceso a salud.';

COMMENT ON TABLE condiciones_territoriales IS
  'Indicadores de entorno territorial por UPL y año: seguridad nocturna, iluminación, transporte, densidad institucional.';

COMMENT ON TABLE lugar_hecho IS
  'Ubicación geográfica puntual donde ocurrió el feminicidio. Geometría POINT.';

COMMENT ON TABLE institucion IS
  'Instituciones del Estado que participan en la ruta de atención: Fiscalía, Comisarías, ICBF, etc. Geometría POINT.';

COMMENT ON TABLE ruta_atencion IS
  'Rutas de atención institucional definidas para víctimas de violencia de género.';

COMMENT ON TABLE institucion_ruta IS
  'Tabla puente M:N entre institucion y ruta_atencion. Tabla de implementación física, no parte del MER conceptual original de 28 entidades.';

COMMENT ON TABLE servicio_psicologico IS
  'Servicios de atención psicológica ofrecidos por instituciones.';

COMMENT ON TABLE victima IS
  'Información sociodemográfica de la víctima directa de feminicidio.';

COMMENT ON TABLE agresor IS
  'Información del agresor: edad, ocupación, antecedentes, estado procesal actual.';

COMMENT ON TABLE feminicidio IS
  'Hecho central del modelo: un caso de feminicidio vinculado a víctima, agresor, lugar y fecha.';

COMMENT ON TABLE victima_indirecta IS
  'Personas afectadas indirectamente por el feminicidio (hijos, familiares).';

COMMENT ON TABLE red_apoyo IS
  'Red de apoyo de la víctima: familia, amigos, instituciones que conocían la situación.';

COMMENT ON TABLE violencia_previa IS
  'Episodios de violencia previos al feminicidio entre la víctima y el agresor.';

COMMENT ON TABLE reincidencia IS
  'Historial de reincidencia del agresor: cantidad de denuncias y ventana temporal.';

COMMENT ON TABLE reporte_inicial IS
  'Primer reporte o llamada de alerta de la víctima ante una entidad (línea 155, etc.).';

COMMENT ON TABLE denuncia IS
  'Denuncia formal interpuesta por la víctima ante una institución.';

COMMENT ON TABLE valoracion_riesgo IS
  'Evaluación del nivel de riesgo realizada sobre una denuncia por una institución.';

COMMENT ON TABLE medida_proteccion IS
  'Medida de protección solicitada/otorgada a partir de una denuncia.';

COMMENT ON TABLE seguimiento IS
  'Seguimiento institucional al cumplimiento de una medida de protección.';

COMMENT ON TABLE contraorden IS
  'Revocación o modificación de una medida de protección vigente.';

COMMENT ON TABLE proceso_penal IS
  'Proceso penal abierto a partir de una denuncia, tramitado por una institución judicial.';

COMMENT ON TABLE actuacion_judicial IS
  'Actuaciones dentro de un proceso penal: audiencias, sentencias, autos, etc.';

-- =============================================================================
-- COMMENT ON COLUMN — Geometrías
-- =============================================================================

COMMENT ON COLUMN zona.geom IS
  'Geometría MULTIPOLYGON en SRID 4326 (WGS84). Unión de localidades de la zona.';

COMMENT ON COLUMN localidad.geom IS
  'Geometría MULTIPOLYGON en SRID 4326. Límite administrativo de la localidad.';

COMMENT ON COLUMN upl.geom IS
  'Geometría POLYGON en SRID 4326. Límite de la Unidad de Planeamiento Local.';

COMMENT ON COLUMN barrio.geom IS
  'Geometría POLYGON en SRID 4326. Límite del barrio.';

COMMENT ON COLUMN manzana.geom IS
  'Geometría POLYGON en SRID 4326. Polígono catastral de la manzana.';

COMMENT ON COLUMN lugar_hecho.geom IS
  'Geometría POINT en SRID 4326. Coordenada aproximada del lugar del feminicidio.';

COMMENT ON COLUMN institucion.geom IS
  'Geometría POINT en SRID 4326. Ubicación de la sede institucional.';

-- =============================================================================
-- COMMENT ON COLUMN — Foreign Keys principales
-- =============================================================================

COMMENT ON COLUMN localidad.id_zona IS
  'FK → zona. Zona macro a la que pertenece la localidad.';

COMMENT ON COLUMN upl.id_localidad IS
  'FK → localidad. Localidad que contiene esta UPL.';

COMMENT ON COLUMN barrio.id_upl IS
  'FK → upl. UPL que contiene este barrio.';

COMMENT ON COLUMN manzana.id_upl IS
  'FK → upl. UPL que contiene esta manzana.';

COMMENT ON COLUMN manzana.id_estrato IS
  'FK → estrato. Estrato socioeconómico asignado a la manzana.';

COMMENT ON COLUMN condicion_vida.id_upl IS
  'FK → upl. UPL a la que corresponden estos indicadores.';

COMMENT ON COLUMN condiciones_territoriales.id_upl IS
  'FK → upl. UPL a la que corresponden estas condiciones territoriales.';

COMMENT ON COLUMN lugar_hecho.id_barrio IS
  'FK → barrio. Barrio donde se ubica el lugar del hecho.';

COMMENT ON COLUMN institucion.id_localidad IS
  'FK → localidad. Localidad donde se encuentra la institución.';

COMMENT ON COLUMN servicio_psicologico.id_institucion IS
  'FK → institucion. Institución que presta el servicio psicológico.';

COMMENT ON COLUMN victima.id_barrio_res IS
  'FK → barrio. Barrio de residencia de la víctima.';

COMMENT ON COLUMN feminicidio.id_victima IS
  'FK → victima. Víctima directa del feminicidio.';

COMMENT ON COLUMN feminicidio.id_agresor IS
  'FK → agresor. Agresor del feminicidio.';

COMMENT ON COLUMN feminicidio.id_lugar IS
  'FK → lugar_hecho. Lugar donde ocurrió el feminicidio.';

COMMENT ON COLUMN feminicidio.fecha_hecho IS
  'FK → tiempo(fecha). Fecha en que ocurrió el feminicidio.';

COMMENT ON COLUMN victima_indirecta.id_feminicidio IS
  'FK → feminicidio. Caso de feminicidio que afectó a esta persona.';

COMMENT ON COLUMN red_apoyo.id_victima IS
  'FK → victima. Víctima a la que pertenece esta red de apoyo.';

COMMENT ON COLUMN violencia_previa.id_victima IS
  'FK → victima. Víctima del episodio de violencia previa.';

COMMENT ON COLUMN violencia_previa.id_agresor IS
  'FK → agresor. Agresor del episodio de violencia previa.';

COMMENT ON COLUMN reincidencia.id_agresor IS
  'FK → agresor. Agresor con historial de reincidencia.';

COMMENT ON COLUMN denuncia.id_victima IS
  'FK → victima. Víctima que interpone la denuncia.';

COMMENT ON COLUMN denuncia.id_institucion IS
  'FK → institucion. Institución que recibe la denuncia.';

COMMENT ON COLUMN denuncia.fecha_denuncia IS
  'FK → tiempo(fecha). Fecha de la denuncia.';

COMMENT ON COLUMN valoracion_riesgo.id_denuncia IS
  'FK → denuncia. Denuncia sobre la que se realiza la valoración.';

COMMENT ON COLUMN valoracion_riesgo.id_institucion IS
  'FK → institucion. Institución que realiza la valoración de riesgo.';

COMMENT ON COLUMN medida_proteccion.id_denuncia IS
  'FK → denuncia. Denuncia que motiva la medida de protección.';

COMMENT ON COLUMN medida_proteccion.id_institucion IS
  'FK → institucion. Institución que emite la medida de protección.';

COMMENT ON COLUMN seguimiento.id_medida IS
  'FK → medida_proteccion. Medida a la que se le da seguimiento.';

COMMENT ON COLUMN contraorden.id_medida IS
  'FK → medida_proteccion. Medida que se revoca o modifica.';

COMMENT ON COLUMN proceso_penal.id_denuncia IS
  'FK → denuncia. Denuncia que dio origen al proceso penal.';

COMMENT ON COLUMN proceso_penal.id_institucion IS
  'FK → institucion. Institución que tramita el proceso penal.';

COMMENT ON COLUMN actuacion_judicial.id_proceso IS
  'FK → proceso_penal. Proceso al que pertenece esta actuación.';

-- =============================================================================
-- COMMENT ON COLUMN — Campos enum / dominio cerrado
-- =============================================================================

COMMENT ON COLUMN estrato.nivel IS
  'Nivel de estrato socioeconómico: 1 (más bajo) a 6 (más alto).';

COMMENT ON COLUMN tiempo.dia_semana IS
  'Nombre del día de la semana: Lunes, Martes, ..., Domingo.';

COMMENT ON COLUMN lugar_hecho.tipo_lugar IS
  'Tipo de lugar: vivienda, vía pública, establecimiento comercial, etc.';

COMMENT ON COLUMN institucion.tipo IS
  'Tipo de institución: Fiscalía, Comisaría de Familia, ICBF, Casa de Justicia, etc.';

COMMENT ON COLUMN feminicidio.tipo IS
  'Tipología del feminicidio: íntimo, no íntimo, por conexión, sexual, etc.';

COMMENT ON COLUMN feminicidio.modalidad IS
  'Modalidad del hecho: arma blanca, arma de fuego, asfixia, etc.';

COMMENT ON COLUMN valoracion_riesgo.nivel_riesgo IS
  'Nivel de riesgo evaluado: bajo, medio, alto, extremo.';

COMMENT ON COLUMN medida_proteccion.estado IS
  'Estado de la medida: solicitada, otorgada, vigente, vencida, revocada.';

COMMENT ON COLUMN denuncia.estado IS
  'Estado procesal de la denuncia: radicada, en investigación, archivada, con sentencia.';

COMMENT ON COLUMN proceso_penal.estado_actual IS
  'Estado del proceso penal: investigación, juicio, sentencia condenatoria, sentencia absolutoria, archivado.';

COMMENT ON COLUMN agresor.estado_actual IS
  'Estado actual del agresor: libre, detenido, prófugo, condenado, muerto.';

COMMENT ON COLUMN condiciones_territoriales.tipo_entorno_urbano IS
  'Clasificación del entorno: residencial, comercial, industrial, mixto, rural.';

-- =============================================================================
-- Fin de comentarios
-- =============================================================================
