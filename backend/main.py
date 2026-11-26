"""
API REST para el proyecto de feminicidio en Bogotá.
Expone endpoints espaciales y analíticos sobre la BD PostGIS.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json

from backend.database import fetch_all, fetch_one

app = FastAPI(
    title="API Feminicidio Bogotá",
    description="API para análisis de negligencia procesal/administrativa en casos de feminicidio",
    version="1.0.0"
)

# Habilitar CORS para que el frontend pueda consumir la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ENDPOINT RAÍZ
# =============================================================================

@app.get("/")
def root():
    """Endpoint raíz con información general de la API."""
    return {
        "proyecto": "Feminicidio Bogotá",
        "version": "1.0.0",
        "descripcion": "API REST con datos espaciales para análisis de negligencia",
        "endpoints": {
            "territorio": [
                "/api/zonas",
                "/api/localidades",
                "/api/localidades/geojson",
                "/api/upl",
            ],
            "instituciones": [
                "/api/instituciones",
                "/api/instituciones/resumen",
            ],
            "feminicidio": [
                "/api/feminicidio/por-localidad",
                "/api/feminicidio/por-zona",
                "/api/feminicidio/serie-temporal",
                "/api/feminicidio/fuentes",
            ],
            "indicadores": [
                "/api/indicadores/desierto-institucional",
                "/api/indicadores/brecha-alerta-prevencion",
            ]
        }
    }


# =============================================================================
# ENDPOINTS TERRITORIO
# =============================================================================

@app.get("/api/zonas")
def listar_zonas():
    """Lista las 4 zonas con su conteo de localidades."""
    query = """
    SELECT z.id_zona, z.nombre,
           COUNT(l.id_localidad) AS total_localidades,
           ROUND((ST_Area(z.geom::geography)/1000000)::numeric, 2) AS area_km2
    FROM zona z
    LEFT JOIN localidad l ON l.id_zona = z.id_zona
    GROUP BY z.id_zona, z.nombre, z.geom
    ORDER BY z.nombre;
    """
    return fetch_all(query)


@app.get("/api/localidades")
def listar_localidades():
    """Lista las 20 localidades con su zona asignada."""
    query = """
    SELECT l.id_localidad, l.nombre, l.codigo_localidad,
           z.nombre AS zona,
           ROUND((ST_Area(l.geom::geography)/1000000)::numeric, 2) AS area_km2
    FROM localidad l
    JOIN zona z ON z.id_zona = l.id_zona
    ORDER BY z.nombre, l.nombre;
    """
    return fetch_all(query)


@app.get("/api/localidades/geojson")
def localidades_geojson():
    """Devuelve las localidades como GeoJSON para renderizar en Leaflet."""
    query = """
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', json_agg(
            json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(l.geom)::json,
                'properties', json_build_object(
                    'id', l.id_localidad,
                    'nombre', l.nombre,
                    'codigo', l.codigo_localidad,
                    'zona', z.nombre
                )
            )
        )
    ) AS geojson
    FROM localidad l
    JOIN zona z ON z.id_zona = l.id_zona;
    """
    result = fetch_one(query)
    return result["geojson"]


@app.get("/api/upl")
def listar_upl():
    """Lista las 33 UPLs."""
    query = """
    SELECT id_upl, codigo_upl, nombre, tipo_upl
    FROM upl
    ORDER BY codigo_upl;
    """
    return fetch_all(query)


# =============================================================================
# ENDPOINTS INSTITUCIONES
# =============================================================================

@app.get("/api/instituciones")
def listar_instituciones(tipo: Optional[str] = Query(None, description="Filtrar por tipo")):
    """Lista instituciones como GeoJSON, opcionalmente filtrado por tipo."""
    where_clause = ""
    params = None
    if tipo:
        where_clause = "WHERE i.tipo = %s"
        params = (tipo.upper(),)
    
    query = f"""
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', json_agg(
            json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(i.geom)::json,
                'properties', json_build_object(
                    'id', i.id_institucion,
                    'tipo', i.tipo,
                    'nombre', i.nombre,
                    'direccion', i.direccion,
                    'localidad', l.nombre
                )
            )
        )
    ) AS geojson
    FROM institucion i
    LEFT JOIN localidad l ON l.id_localidad = i.id_localidad
    {where_clause};
    """
    result = fetch_one(query, params)
    return result["geojson"]


@app.get("/api/instituciones/resumen")
def resumen_instituciones():
    """Resumen de instituciones por tipo y zona."""
    query = """
    SELECT i.tipo, z.nombre AS zona, COUNT(*) AS total
    FROM institucion i
    JOIN localidad l ON l.id_localidad = i.id_localidad
    JOIN zona z ON z.id_zona = l.id_zona
    GROUP BY i.tipo, z.nombre
    ORDER BY i.tipo, z.nombre;
    """
    return fetch_all(query)


# =============================================================================
# ENDPOINTS FEMINICIDIO
# =============================================================================

@app.get("/api/feminicidio/por-localidad")
def feminicidio_por_localidad(fuente: str = Query("INMLCF_HOMICIDIOS", description="Fuente de datos")):
    """Conteo de casos por localidad según fuente."""
    query = """
    SELECT l.nombre AS localidad, z.nombre AS zona,
           SUM(fa.conteo_casos) AS total_casos,
           MIN(fa.anio) AS anio_min,
           MAX(fa.anio) AS anio_max
    FROM localidad l
    JOIN zona z ON z.id_zona = l.id_zona
    LEFT JOIN feminicidio_agregado fa ON fa.id_localidad = l.id_localidad AND fa.fuente = %s
    GROUP BY l.nombre, z.nombre
    ORDER BY total_casos DESC NULLS LAST;
    """
    return fetch_all(query, (fuente,))


@app.get("/api/feminicidio/por-zona")
def feminicidio_por_zona(fuente: str = Query("INMLCF_HOMICIDIOS")):
    """Conteo de casos por zona."""
    query = """
    SELECT z.nombre AS zona,
           SUM(c.casos) AS total_casos,
           COUNT(*) AS num_localidades,
           SUM(l.poblacion_fem) AS poblacion_fem
    FROM zona z
    JOIN localidad l ON l.id_zona = z.id_zona
    LEFT JOIN (SELECT id_localidad, SUM(conteo_casos) AS casos
               FROM feminicidio_agregado WHERE fuente = %s
               GROUP BY id_localidad) c ON c.id_localidad = l.id_localidad
    GROUP BY z.nombre
    ORDER BY total_casos DESC NULLS LAST;
    """
    return fetch_all(query, (fuente,))


@app.get("/api/feminicidio/serie-temporal")
def serie_temporal(fuente: str = Query("INMLCF_HOMICIDIOS")):
    """Serie temporal de casos por año y zona."""
    query = """
    SELECT fa.anio, z.nombre AS zona, SUM(fa.conteo_casos) AS casos
    FROM feminicidio_agregado fa
    JOIN localidad l ON l.id_localidad = fa.id_localidad
    JOIN zona z ON z.id_zona = l.id_zona
    WHERE fa.fuente = %s
    GROUP BY fa.anio, z.nombre
    ORDER BY fa.anio, z.nombre;
    """
    return fetch_all(query, (fuente,))


@app.get("/api/feminicidio/fuentes")
def listar_fuentes():
    """Resumen de fuentes disponibles en feminicidio_agregado."""
    query = """
    SELECT fuente, COUNT(*) AS filas,
           MIN(anio) AS anio_min, MAX(anio) AS anio_max,
           SUM(conteo_casos) AS total_casos
    FROM feminicidio_agregado
    GROUP BY fuente
    ORDER BY fuente;
    """
    return fetch_all(query)


# =============================================================================
# ENDPOINTS INDICADORES DE NEGLIGENCIA
# =============================================================================

@app.get("/api/indicadores/desierto-institucional")
def indicador_desierto():
    """
    Proxy de desierto institucional: tres indicadores separados por función.
    - Vía formal: homicidios / (Comisarías + Casas de Justicia)
    - Emergencia: homicidios / CAI
    - Acompañamiento: homicidios / Casas de Igualdad
    """
    query = """
    SELECT l.nombre AS localidad, z.nombre AS zona,
           COALESCE(c.comisarias, 0) AS comisarias,
           COALESCE(cj.casas_justicia, 0) AS casas_justicia,
           COALESCE(ci.casas_igualdad, 0) AS casas_igualdad,
           COALESCE(ca.cais, 0) AS cais,
           COALESCE(f.homicidios, 0) AS homicidios,
           l.poblacion_fem,
           -- Tasa anual promedio 2015–2024 por 100.000 mujeres (población OMEG 2025)
           CASE WHEN l.poblacion_fem > 0
                THEN ROUND(COALESCE(f.homicidios, 0)::numeric / 10 / l.poblacion_fem * 100000, 1)
                ELSE NULL END AS tasa_anual_100k,
           -- Sin comisarías ni casas de justicia el índice es una división por
           -- cero: queda NULL («no calculable»), no 0.
           -- COALESCE en cada término: si una localidad no tiene Casas de Justicia
           -- (o Comisarías), el LEFT JOIN deja NULL y la suma completa sería NULL.
           CASE WHEN (COALESCE(c.comisarias, 0) + COALESCE(cj.casas_justicia, 0)) > 0
                THEN ROUND(COALESCE(f.homicidios, 0)::numeric
                           / (COALESCE(c.comisarias, 0) + COALESCE(cj.casas_justicia, 0)), 2)
                ELSE NULL END AS casos_por_via_formal,
           CASE WHEN ca.cais > 0 
                THEN ROUND(f.homicidios::numeric / ca.cais, 2) 
                ELSE NULL END AS casos_por_cai,
           CASE WHEN ci.casas_igualdad > 0 
                THEN ROUND(f.homicidios::numeric / ci.casas_igualdad, 2) 
                ELSE NULL END AS casos_por_casa_igualdad
    FROM localidad l
    JOIN zona z ON z.id_zona = l.id_zona
    LEFT JOIN (SELECT id_localidad, COUNT(*) AS comisarias FROM institucion WHERE tipo = 'COMISARIA_FAMILIA' GROUP BY id_localidad) c ON c.id_localidad = l.id_localidad
    LEFT JOIN (SELECT id_localidad, COUNT(*) AS casas_justicia FROM institucion WHERE tipo = 'CASA_JUSTICIA' GROUP BY id_localidad) cj ON cj.id_localidad = l.id_localidad
    LEFT JOIN (SELECT id_localidad, COUNT(*) AS casas_igualdad FROM institucion WHERE tipo = 'CASA_IGUALDAD' GROUP BY id_localidad) ci ON ci.id_localidad = l.id_localidad
    LEFT JOIN (SELECT id_localidad, COUNT(*) AS cais FROM institucion WHERE tipo = 'CAI' GROUP BY id_localidad) ca ON ca.id_localidad = l.id_localidad
    LEFT JOIN (SELECT id_localidad, SUM(conteo_casos) AS homicidios FROM feminicidio_agregado WHERE fuente = 'INMLCF_HOMICIDIOS' GROUP BY id_localidad) f ON f.id_localidad = l.id_localidad
    ORDER BY casos_por_via_formal DESC NULLS LAST;
    """
    return fetch_all(query)


@app.get("/api/indicadores/brecha-alerta-prevencion")
def indicador_brecha():
    """
    Proxy de brecha entre alerta y prevención.
    Compara valoraciones de riesgo (OMEG_RIESGO) con asesinatos (OMEG_ASESINATOS) 2025.
    """
    query = """
    SELECT l.nombre AS localidad, z.nombre AS zona,
           MAX(CASE WHEN fa.fuente LIKE 'OMEG_RIESGO%' THEN fa.conteo_casos END) AS mujeres_en_riesgo,
           MAX(CASE WHEN fa.fuente LIKE 'OMEG_ASESINATOS%' THEN fa.conteo_casos END) AS asesinatos_2025,
           ROUND(
             MAX(CASE WHEN fa.fuente LIKE 'OMEG_ASESINATOS%' THEN fa.conteo_casos END)::numeric / 
             NULLIF(MAX(CASE WHEN fa.fuente LIKE 'OMEG_RIESGO%' THEN fa.conteo_casos END), 0) * 100, 
             2
           ) AS tasa_conversion_riesgo_asesinato_pct
    FROM localidad l
    JOIN zona z ON z.id_zona = l.id_zona
    LEFT JOIN feminicidio_agregado fa ON fa.id_localidad = l.id_localidad AND fa.anio = 2025
    GROUP BY l.nombre, z.nombre
    ORDER BY tasa_conversion_riesgo_asesinato_pct DESC NULLS LAST;
    """
    return fetch_all(query)


# =============================================================================
# ENDPOINT DE SALUD
# =============================================================================

@app.get("/health")
def health_check():
    """Verifica conexión a BD."""
    try:
        result = fetch_one("SELECT PostGIS_Version() AS version, current_database() AS db;")
        return {
            "status": "ok",
            "database": result["db"],
            "postgis_version": result["version"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de conexión: {str(e)}")


# =============================================================================
# ENDPOINTS NUEVOS - FASE B
# =============================================================================

@app.get("/api/indicadores/negligencia-forense")
def indicador_negligencia_forense():
    """
    Proxy de negligencia en el registro forense.
    Compara casos sin clasificación vs total de homicidios de mujeres por localidad.
    Una proporción alta sugiere problemas sistemáticos de documentación forense.
    """
    # La circunstancia «Feminicidio» solo existe en el INMLCF desde 2018: su
    # porcentaje se calcula sobre los homicidios del MISMO período (2018–2024).
    # Un conteo 0 da 0 % (no NULL): NULL solo cuando no hay homicidios.
    query = """
    SELECT l.nombre AS localidad, z.nombre AS zona,
           COALESCE(h.total, 0) AS homicidios_total,
           COALESCE(h.total_2018, 0) AS homicidios_2018_2024,
           COALESCE(f.total, 0) AS feminicidios_forenses,
           COALESCE(vg.total, 0) AS violencia_genero_amplia,
           COALESCE(si.total, 0) AS sin_clasificacion,
           CASE WHEN h.total > 0
                THEN ROUND(COALESCE(si.total, 0)::numeric / h.total * 100, 1)
                ELSE NULL END AS pct_sin_clasificacion,
           CASE WHEN h.total_2018 > 0
                THEN ROUND(COALESCE(f.total, 0)::numeric / h.total_2018 * 100, 1)
                ELSE NULL END AS pct_feminicidio_explicito
    FROM localidad l
    JOIN zona z ON z.id_zona = l.id_zona
    LEFT JOIN (
        SELECT id_localidad, SUM(conteo_casos) AS total,
               SUM(conteo_casos) FILTER (WHERE anio >= 2018) AS total_2018
        FROM feminicidio_agregado WHERE fuente = 'INMLCF_HOMICIDIOS'
        GROUP BY id_localidad
    ) h ON h.id_localidad = l.id_localidad
    LEFT JOIN (
        SELECT id_localidad, SUM(conteo_casos) AS total
        FROM feminicidio_agregado WHERE fuente = 'INMLCF_FEMINICIDIO'
        GROUP BY id_localidad
    ) f ON f.id_localidad = l.id_localidad
    LEFT JOIN (
        SELECT id_localidad, SUM(conteo_casos) AS total
        FROM feminicidio_agregado WHERE fuente = 'INMLCF_VIOLENCIA_GENERO'
        GROUP BY id_localidad
    ) vg ON vg.id_localidad = l.id_localidad
    LEFT JOIN (
        SELECT id_localidad, SUM(conteo_casos) AS total
        FROM feminicidio_agregado WHERE fuente = 'INMLCF_SIN_INFO'
        GROUP BY id_localidad
    ) si ON si.id_localidad = l.id_localidad
    ORDER BY pct_sin_clasificacion DESC NULLS LAST;
    """
    return fetch_all(query)


@app.get("/api/indicadores/brecha-riesgo-muerte")
def indicador_brecha_riesgo_muerte():
    """
    Brecha entre mujeres identificadas en riesgo (OMEG 2025) y asesinatos consumados.
    Localidades con alta tasa de conversión sugieren falla del sistema preventivo.
    """
    query = """
    SELECT l.nombre AS localidad, z.nombre AS zona,
           COALESCE(r.mujeres_en_riesgo, 0) AS mujeres_en_riesgo_2025,
           COALESCE(a.asesinadas, 0) AS asesinadas_2025,
           CASE WHEN r.mujeres_en_riesgo > 0
                THEN ROUND(a.asesinadas::numeric / r.mujeres_en_riesgo * 100, 2)
                ELSE NULL END AS tasa_conversion_pct
    FROM localidad l
    JOIN zona z ON z.id_zona = l.id_zona
    LEFT JOIN (
        SELECT id_localidad, SUM(conteo_casos) AS mujeres_en_riesgo
        FROM feminicidio_agregado WHERE fuente = 'OMEG_RIESGO_T3'
        GROUP BY id_localidad
    ) r ON r.id_localidad = l.id_localidad
    LEFT JOIN (
        SELECT id_localidad, SUM(conteo_casos) AS asesinadas
        FROM feminicidio_agregado WHERE fuente = 'OMEG_ASESINATOS_T3'
        GROUP BY id_localidad
    ) a ON a.id_localidad = l.id_localidad
    ORDER BY tasa_conversion_pct DESC NULLS LAST;
    """
    return fetch_all(query)
