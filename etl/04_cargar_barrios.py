import os
import requests
import psycopg2
import psycopg2.extras
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

DATA_RAW_DIR = "data/raw"
BARRIOS_URL = "https://datosabiertos.bogota.gov.co/dataset/36a80ef3-02c1-4a48-b3c7-c285e1de4323/resource/ba69f395-13ed-4071-802d-3808e2ba9062/download/barriolegalizado.json"

def download_file(url, dest_path):
    if not os.path.exists(dest_path):
        print(f"Descargando {url}...")
        r = requests.get(url)
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            f.write(r.content)
        print(f"Guardado en {dest_path}")
    else:
        print(f"Archivo ya existe: {dest_path}")
    return dest_path

def main():
    load_dotenv()
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    barrios_file = download_file(BARRIOS_URL, f"{DATA_RAW_DIR}/barrios.geojson")

    print("\nLeyendo Barrios con Geopandas...")
    gdf_barrios = gpd.read_file(barrios_file).to_crs(4326)
    
    print("\n--- ANÁLISIS DEL DATASET BARRIOS ---")
    print(f"Total filas: {len(gdf_barrios)}")
    print(f"Columnas: {gdf_barrios.columns.tolist()}")
    print("Primeros 3 registros:")
    print(gdf_barrios.head(3))

    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    conn.set_client_encoding('UTF8') 
    
    # 1. Extraer geom de UPL de la BD para Spatial Join
    print("\nExtrayendo UPLs de la base de datos...")
    query_upl = "SELECT id_upl, geom FROM upl"
    gdf_upl = gpd.GeoDataFrame.from_postgis(query_upl, conn, geom_col='geom', crs=4326)

    # 2. Hacer Spatial Join
    print("Realizando cruce espacial (Spatial Join: Centroide Barrio dentro de Polígono UPL)...")
    gdf_barrios['centroid'] = gdf_barrios.geometry.centroid
    joined = gpd.sjoin(gdf_barrios.set_geometry('centroid'), gdf_upl, how='left', predicate='within')
    
    # Filtrar barrios sin UPL
    missing_upl = joined['id_upl'].isna().sum()
    print(f"Resultados SJOIN: {len(joined) - missing_upl} con UPL, {missing_upl} sin UPL.")
    
    # Restituir la geometría original de polígonos
    joined = joined.set_geometry('geometry')

    print("\nInsertando en base de datos...")
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE barrio RESTART IDENTITY CASCADE;")
    
    # Columnas esperadas en el JSON
    name_col = next((c for c in ['BarNombre', 'nombre', 'NOMB_BARR'] if c in joined.columns), joined.columns[0])
    code_col = next((c for c in ['BarCodigo', 'codigo', 'COD_BARR'] if c in joined.columns), joined.columns[1])
    
    barrio_insert = []
    for idx, row in joined.iterrows():
        if row.get('geometry') is None or (hasattr(row.get('geometry'), 'is_empty') and row.get('geometry').is_empty):
            continue
        id_upl = None if pd.isna(row['id_upl']) else int(row['id_upl'])
        codigo = str(row.get(code_col, idx))
        nombre = str(row.get(name_col, f"Barrio_{idx}"))
        geom = row['geometry']
        if geom.geom_type == 'MultiPolygon':
            geom = max(geom.geoms, key=lambda a: a.area)
        wkt = geom.wkt
        barrio_insert.append((id_upl, nombre, wkt))

    psycopg2.extras.execute_values(cur, 
        "INSERT INTO barrio (id_upl, nombre, geom) VALUES %s", 
        barrio_insert, 
        template="(%s, %s, ST_GeomFromText(%s, 4326))"
    )
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"🚀 Carga de barrios finalizada. Insertados: {len(barrio_insert)}")

if __name__ == "__main__":
    main()
