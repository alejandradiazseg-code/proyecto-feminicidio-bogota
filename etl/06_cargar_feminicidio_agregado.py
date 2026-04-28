import os
import sys
import requests
import psycopg2
import psycopg2.extras
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

# URLs de OMEG
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

# API Socrata (VTUB-3DE2)
INMLCF_URL = "https://www.datos.gov.co/resource/vtub-3de2.json"

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
    n = n.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
    if n == 'SANTAFE': n = 'SANTA FE'
    if n == 'MARTIRES': n = 'LOS MARTIRES'
    if n == 'CANDELARIA': n = 'LA CANDELARIA'
    if n == 'RAFAEL URIBE': n = 'RAFAEL URIBE URIBE'
    return n

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
    
    # Mapa Localidades
    cur.execute("SELECT id_localidad, nombre, codigo_localidad FROM localidad")
    loc_data = cur.fetchall()
    loc_id_map = {normalizar_nombre_localidad(n): id_loc for id_loc, n, _ in loc_data}
    loc_code_map = {str(c).zfill(2): id_loc for id_loc, _, c in loc_data}
    
    inserts = []
    
    # 1. HOMICIDIOS INMLCF (vtub-3de2) - 2015 a 2024
    print("Obteniendo datos de API vtub-3de2 (Presuntos Homicidios a Mujeres, Bogotá)...")
    query_inmlcf = (
        f"{INMLCF_URL}?$select=a_o_del_hecho,localidad_del_hecho,count(*)&"
        f"$where=(departamento_del_hecho_dane='Bogotá D.C.' OR departamento_del_hecho_dane='Bogotá, D.C.') "
        f"AND sexo_de_la_victima='Mujer'&$group=a_o_del_hecho,localidad_del_hecho&$limit=50000"
    )
    r = requests.get(query_inmlcf)
    r.raise_for_status()
    homicidios = r.json()
    
    total_inmlcf = sum(int(h['count']) for h in homicidios)
    homicidios_sin_loc = sum(int(h['count']) for h in homicidios if 'localidad_del_hecho' not in h or normalizar_nombre_localidad(h['localidad_del_hecho']) not in loc_id_map)
    porcentaje_missing = (homicidios_sin_loc / total_inmlcf) * 100 if total_inmlcf > 0 else 0
    
    # Calculate and print yearly breakdown
    conteo_anual = {}
    for h in homicidios:
        anio = h['a_o_del_hecho']
        conteo_anual[anio] = conteo_anual.get(anio, 0) + int(h['count'])
        
    print("\nResumen Anual (Homicidios a Mujeres, Bogotá):")
    for anio in sorted(conteo_anual.keys()):
        print(f" - {anio}: {conteo_anual[anio]} casos")
        
    print(f"\nTotal General (2015-2024): {total_inmlcf} casos.")
    print(f"Registros sin localidad identificada: {homicidios_sin_loc} ({porcentaje_missing:.2f}%)")
    
    if porcentaje_missing > 10.0:
        print("❌ ALERTA: Más del 10% de registros INMLCF no tienen localidad válida. Proceso detenido por política metodológica.")
        sys.exit(1)
    elif homicidios_sin_loc > 0:
        print("⚠ WARNING: Se descartarán los registros sin localidad (<10%).")
        
    for doc in homicidios:
        loc_raw = doc.get('localidad_del_hecho', '')
        if 'Sin información' in loc_raw: continue
        
        loc_norm = normalizar_nombre_localidad(loc_raw)
        id_loc = loc_id_map.get(loc_norm)
        
        if id_loc:
            inserts.append((id_loc, int(doc['a_o_del_hecho']), int(doc['count']), 'INMLCF_HOMICIDIOS', None, None, f"Localidad_org: {loc_raw}"))

    # 2. OMEG RIESGO Y ASESINATOS (2025 GeoJSON)
    def procesar_omeg(fuentes_list, tipo_fuente):
        for url, anio, trim in fuentes_list:
            try:
                # Use requests to avoid PyOGRIO network hangs
                r_req = requests.get(url, timeout=30)
                r_req.raise_for_status()
                tmp_path = f"/tmp/omeg_{tipo_fuente}_{trim}_{anio}.geojson"
                with open(tmp_path, "wb") as f_tmp:
                    f_tmp.write(r_req.content)
                gdf = gpd.read_file(tmp_path)
                # Deducir la columna de conteo y tasa leyendo tipos numéricos de gdf
                num_cols = gdf.select_dtypes(include=['number']).columns.tolist()
                col_tasa = next((c for c in ['TaRiesgoFe', 'TaRiesgoFemicidio', 'TaAsesinat', 'TASA', 'tasa'] if c in gdf.columns), None)
                col_total = next((c for c in ['TRiesgoFem', 'TRiesgoFeminicidio', 'TAsesinato', 'TOTAL', 'CONTEO', 'CASOS', 'total'] if c in gdf.columns), None)
                col_loc = next((c for c in ['1','2','localidad','LOCALIDAD','Localidad','LocNombre'] if c in gdf.columns), None)
                
                if not col_loc: continue
                
                for idx, row in gdf.iterrows():
                    loc_raw = row[col_loc]
                    loc_code_str = str(loc_raw).zfill(2)
                    id_loc = loc_code_map.get(loc_code_str)
                    
                    if not id_loc:
                        loc_norm = normalizar_nombre_localidad(loc_raw)
                        id_loc = loc_id_map.get(loc_norm)
                        
                    if id_loc:
                        tasa = row[col_tasa] if col_tasa else None
                        conteo = row[col_total] if col_total else None
                        if pd.notna(conteo):
                            inserts.append((id_loc, anio, int(conteo), f"{tipo_fuente}_{trim}", float(tasa) if pd.notna(tasa) else None, None, f"Trimestre: {trim}"))
            except Exception as e:
                print(f"Error procesando {url}: {e}")

    print("Procesando OMEG Riesgo Feminicidio 2025...")
    procesar_omeg(OMEG_RIESGO, 'OMEG_RIESGO')
    print("Procesando OMEG Asesinatos Mujeres 2025...")
    procesar_omeg(OMEG_ASESINATOS, 'OMEG_ASESINATOS')

    # INSERT EN BASE DE DATOS
    print(f"\nTotal filas a insertar: {len(inserts)}")
    cur.execute("TRUNCATE TABLE feminicidio_agregado RESTART IDENTITY CASCADE;")
    
    psycopg2.extras.execute_values(cur, 
        """
        INSERT INTO feminicidio_agregado (id_localidad, anio, conteo_casos, fuente, tasa_por_100k, fecha_corte, observaciones)
        VALUES %s
        """,
        inserts
    )
    
    conn.commit()
    cur.close()
    conn.close()
    print("🚀 Carga en feminicidio_agregado completada con éxito.")

if __name__ == "__main__":
    main()
