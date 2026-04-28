"""
Script 06b: Re-carga de feminicidio_agregado con clasificación forense refinada.
Crea 4 fuentes separadas desde el dataset vtub-3de2:
- INMLCF_HOMICIDIOS: todos los homicidios de mujeres (2015-2024)
- INMLCF_FEMINICIDIO: solo circunstancia='Feminicidio' (2018-2024)
- INMLCF_VIOLENCIA_GENERO: Feminicidio + Violencia de pareja + Conflicto de pareja
- INMLCF_SIN_INFO: casos con circunstancia='Sin información'

Mantiene también las fuentes OMEG_RIESGO_T1/T2/T3 y OMEG_ASESINATOS_T1/T2/T3 de 2025.
"""
import os
import sys
import requests
import psycopg2
import psycopg2.extras
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

INMLCF_URL = "https://www.datos.gov.co/resource/vtub-3de2.json"

OMEG_RIESGO = [
    ("https://datosabiertos.bogota.gov.co/dataset/94a36c8e-8a4f-46b7-b75a-00e5c9668ddf/resource/9365d2c6-e9a1-4e48-b209-65ee6b9f2f86/download/riesgofeminicidio_062025.geojson", 2025, 'T1'),
    ("https://datosabiertos.bogota.gov.co/dataset/94a36c8e-8a4f-46b7-b75a-00e5c9668ddf/resource/efe5dd07-ad41-43ac-9edf-d6717c7ddcfb/download/riesgofeminicidio_092025.geojson", 2025, 'T2'),
    ("https://datosabiertos.bogota.gov.co/dataset/94a36c8e-8a4f-46b7-b75a-00e5c9668ddf/resource/54e82520-125b-4101-902b-25a74b9e07fc/download/riesgofeminicidio_122025.geojson", 2025, 'T3')
]

OMEG_ASESINATOS = [
    ("https://datosabiertos.bogota.gov.co/dataset/da552105-c3e5-49f1-b632-1c6201e96595/resource/db8dc8e9-5f74-48e5-bdf7-3e6fe6bc3c75/download/asesinatosmujeres_062025.geojson", 2025, 'T1'),
    ("https://datosabiertos.bogota.gov.co/dataset/da552105-c3e5-49f1-b632-1c6201e96595/resource/e0195eea-97d9-48fa-b086-c2af60dab654/download/asesinatosmujeres_092025.geojson", 2025, 'T2'),
    ("https://datosabiertos.bogota.gov.co/dataset/da552105-c3e5-49f1-b632-1c6201e96595/resource/3c0f4ddc-05e5-44f0-9f16-3d736a844cf8/download/asesinatos_122025.geojson", 2025, 'T3')
]

NOMBRES_CANONICOS = {
    'USAQUEN': 'Usaquén', 'CHAPINERO': 'Chapinero', 'SANTA FE': 'Santa Fe',
    'SAN CRISTOBAL': 'San Cristóbal', 'USME': 'Usme', 'TUNJUELITO': 'Tunjuelito',
    'BOSA': 'Bosa', 'KENNEDY': 'Kennedy', 'FONTIBON': 'Fontibón',
    'ENGATIVA': 'Engativá', 'SUBA': 'Suba', 'BARRIOS UNIDOS': 'Barrios Unidos',
    'TEUSAQUILLO': 'Teusaquillo', 'LOS MARTIRES': 'Los Mártires',
    'ANTONIO NARIÑO': 'Antonio Nariño', 'PUENTE ARANDA': 'Puente Aranda',
    'LA CANDELARIA': 'La Candelaria', 'RAFAEL URIBE URIBE': 'Rafael Uribe Uribe',
    'CIUDAD BOLIVAR': 'Ciudad Bolívar', 'SUMAPAZ': 'Sumapaz'
}


def normalizar_nombre_localidad(nombre):
    if pd.isna(nombre) or nombre is None:
        return ""
    n = str(nombre).strip().upper()
    n = n.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
    if n == 'SANTAFE': n = 'SANTA FE'
    if n == 'MARTIRES': n = 'LOS MARTIRES'
    if n == 'CANDELARIA': n = 'LA CANDELARIA'
    if n == 'RAFAEL URIBE': n = 'RAFAEL URIBE URIBE'
    return n


def consultar_inmlcf(where_circunstancia=""):
    """Consulta INMLCF con filtro opcional por circunstancia."""
    filtro_base = (
        "(departamento_del_hecho_dane='Bogotá D.C.' OR departamento_del_hecho_dane='Bogotá, D.C.') "
        "AND sexo_de_la_victima='Mujer'"
    )
    where_completo = filtro_base + where_circunstancia
    
    query = (
        f"{INMLCF_URL}?$select=a_o_del_hecho,localidad_del_hecho,count(*)"
        f"&$where={where_completo}"
        f"&$group=a_o_del_hecho,localidad_del_hecho"
        f"&$limit=50000"
    )
    r = requests.get(query)
    r.raise_for_status()
    return r.json()


def procesar_inmlcf(datos, fuente, loc_id_map):
    """Convierte registros de INMLCF a tuplas para insertar."""
    inserts = []
    descartados = 0
    total = 0
    
    for doc in datos:
        total += int(doc['count'])
        loc_raw = doc.get('localidad_del_hecho', '')
        
        if 'Sin información' in loc_raw:
            descartados += int(doc['count'])
            continue
        
        loc_norm = normalizar_nombre_localidad(loc_raw)
        id_loc = loc_id_map.get(loc_norm)
        
        if id_loc:
            inserts.append((
                id_loc,
                int(doc['a_o_del_hecho']),
                int(doc['count']),
                fuente,
                None,  # tasa
                None,  # fecha_corte
                f"Localidad original: {loc_raw}"
            ))
        else:
            descartados += int(doc['count'])
    
    print(f"  {fuente}: {len(inserts)} filas | {sum(i[2] for i in inserts)} casos | Descartados sin localidad: {descartados}/{total}")
    return inserts


def procesar_omeg(fuentes_list, tipo_fuente, loc_id_map):
    """Procesa los GeoJSON trimestrales del OMEG."""
    inserts = []
    
    for url, anio, trim in fuentes_list:
        fuente_con_trim = f"{tipo_fuente}_{trim}"
        try:
            gdf = gpd.read_file(url)
            num_cols = gdf.select_dtypes(include=['number']).columns.tolist()
            col_tasa = next((c for c in num_cols if 'TASA' in c.upper() or 'TARIESGO' in c.upper()), None)
            col_total = next((c for c in num_cols if 'TOTAL' in c.upper() or 'CONTEO' in c.upper() 
                             or 'PRIESGO' in c.upper() or 'CASOS' in c.upper()), None)
            col_loc = next((c for c in ['Localidad', 'localidad', 'LOCALIDAD', 'LocNombre', '1'] 
                           if c in gdf.columns), None)
            
            if not col_loc or not col_total:
                print(f"  WARNING: columnas no encontradas para {url}")
                continue
            
            for idx, row in gdf.iterrows():
                loc_raw = row[col_loc]
                loc_norm = normalizar_nombre_localidad(loc_raw)
                id_loc = loc_id_map.get(loc_norm)
                if id_loc and pd.notna(row[col_total]):
                    tasa = row[col_tasa] if col_tasa and pd.notna(row[col_tasa]) else None
                    inserts.append((
                        id_loc, anio, int(row[col_total]), fuente_con_trim,
                        float(tasa) if tasa is not None else None,
                        None, f"Trimestre: {trim}"
                    ))
        except Exception as e:
            print(f"  ERROR procesando {url}: {e}")
    
    print(f"  {tipo_fuente}: {len(inserts)} filas total (3 trimestres)")
    return inserts


def main():
    load_dotenv()
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()
    
    # Mapa de localidades
    cur.execute("SELECT id_localidad, nombre FROM localidad")
    loc_id_map = {normalizar_nombre_localidad(n): id_loc for id_loc, n in cur.fetchall()}
    
    print("=" * 70)
    print("CARGANDO FUENTES INMLCF (Medicina Legal)")
    print("=" * 70)
    
    # 1. Todos los homicidios de mujeres (total)
    print("\n1. INMLCF_HOMICIDIOS (todos los homicidios de mujeres)")
    datos_total = consultar_inmlcf("")
    inserts_total = procesar_inmlcf(datos_total, 'INMLCF_HOMICIDIOS', loc_id_map)
    
    # 2. Solo feminicidio explícito
    print("\n2. INMLCF_FEMINICIDIO (circunstancia = Feminicidio)")
    datos_fem = consultar_inmlcf(" AND circunstancia_del_hecho_detallada='Feminicidio'")
    inserts_fem = procesar_inmlcf(datos_fem, 'INMLCF_FEMINICIDIO', loc_id_map)
    
    # 3. Violencia de género amplia
    print("\n3. INMLCF_VIOLENCIA_GENERO (Feminicidio + Violencia de pareja + Conflicto de pareja)")
    datos_vg = consultar_inmlcf(
        " AND (circunstancia_del_hecho_detallada='Feminicidio' "
        "OR circunstancia_del_hecho_detallada='Violencia de pareja' "
        "OR circunstancia_del_hecho_detallada='Conflicto de pareja')"
    )
    inserts_vg = procesar_inmlcf(datos_vg, 'INMLCF_VIOLENCIA_GENERO', loc_id_map)
    
    # 4. Sin información (proxy de negligencia forense)
    print("\n4. INMLCF_SIN_INFO (circunstancia = Sin información)")
    datos_si = consultar_inmlcf(" AND circunstancia_del_hecho_detallada='Sin información'")
    inserts_si = procesar_inmlcf(datos_si, 'INMLCF_SIN_INFO', loc_id_map)
    
    print("\n" + "=" * 70)
    print("CARGANDO FUENTES OMEG (SDMujer 2025)")
    print("=" * 70)
    
    # 5. OMEG RIESGO
    print("\n5. OMEG_RIESGO (mujeres valoradas en riesgo de feminicidio 2025)")
    inserts_omeg_r = procesar_omeg(OMEG_RIESGO, 'OMEG_RIESGO', loc_id_map)
    
    # 6. OMEG ASESINATOS
    print("\n6. OMEG_ASESINATOS (asesinatos a mujeres 2025)")
    inserts_omeg_a = procesar_omeg(OMEG_ASESINATOS, 'OMEG_ASESINATOS', loc_id_map)
    
    todos_inserts = (inserts_total + inserts_fem + inserts_vg + inserts_si + 
                     inserts_omeg_r + inserts_omeg_a)
    
    print("\n" + "=" * 70)
    print(f"TOTAL FILAS A INSERTAR: {len(todos_inserts)}")
    print("=" * 70)
    
    # TRUNCATE y CARGA
    cur.execute("TRUNCATE TABLE feminicidio_agregado RESTART IDENTITY CASCADE;")
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO feminicidio_agregado 
        (id_localidad, anio, conteo_casos, fuente, tasa_por_100k, fecha_corte, observaciones)
        VALUES %s
        """,
        todos_inserts
    )
    
    conn.commit()
    
    # Reporte final
    cur.execute("""
        SELECT fuente, COUNT(*) AS filas, 
               MIN(anio) AS anio_min, MAX(anio) AS anio_max,
               SUM(conteo_casos) AS total_casos
        FROM feminicidio_agregado
        GROUP BY fuente
        ORDER BY fuente;
    """)
    
    print("\n" + "=" * 70)
    print("RESUMEN FINAL EN BD")
    print("=" * 70)
    print(f"{'Fuente':<30} {'Filas':<10} {'Años':<15} {'Total casos':<10}")
    print("-" * 70)
    for row in cur.fetchall():
        fuente, filas, anio_min, anio_max, total = row
        años = f"{anio_min}-{anio_max}"
        print(f"{fuente:<30} {filas:<10} {años:<15} {total:<10}")
    
    cur.close()
    conn.close()
    print("\n🎉 Recarga completada")


if __name__ == "__main__":
    main()

# ============================================================
# PARCHE: mapa de códigos numéricos de localidad (OMEG usa IDs)
# ============================================================
LOCALIDAD_CODIGO_A_NOMBRE = {
    '1': 'Usaquén', '2': 'Chapinero', '3': 'Santa Fe',
    '4': 'San Cristóbal', '5': 'Usme', '6': 'Tunjuelito',
    '7': 'Bosa', '8': 'Kennedy', '9': 'Fontibón',
    '10': 'Engativá', '11': 'Suba', '12': 'Barrios Unidos',
    '13': 'Teusaquillo', '14': 'Los Mártires', '15': 'Antonio Nariño',
    '16': 'Puente Aranda', '17': 'La Candelaria',
    '18': 'Rafael Uribe Uribe', '19': 'Ciudad Bolívar', '20': 'Sumapaz'
}
