import os
import requests
import psycopg2
import psycopg2.extras
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

DATA_RAW_DIR = "data/raw"
LOC_URL = "https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8/resource/497b8756-0927-4aee-8da9-ca4e32ca3a8a/download/loca.json"
UPL_URL = "https://datosabiertos.bogota.gov.co/dataset/808582fc-ffc8-4649-8428-7e1fd8d3820c/resource/a5c8c591-0708-420f-8eb7-9f3147e21c40/download/unidadplaneamientolocal.json"

ZONAS = {
    'NORTE': ['USAQUEN', 'CHAPINERO', 'SUBA', 'BARRIOS UNIDOS', 'TEUSAQUILLO', 'ENGATIVA'],
    'SUR': ['BOSA', 'KENNEDY', 'CIUDAD BOLIVAR', 'USME', 'TUNJUELITO', 'RAFAEL URIBE URIBE', 'SAN CRISTOBAL'],
    'CENTRO': ['SANTA FE', 'LA CANDELARIA', 'LOS MARTIRES', 'ANTONIO NARIÑO', 'PUENTE ARANDA', 'FONTIBON'],
    'RURAL': ['SUMAPAZ']
}

NOMBRES_CANONICOS = {
    'USAQUEN': 'Usaquén',
    'CHAPINERO': 'Chapinero',
    'SANTA FE': 'Santa Fe',
    'SAN CRISTOBAL': 'San Cristóbal',
    'USME': 'Usme',
    'TUNJUELITO': 'Tunjuelito',
    'BOSA': 'Bosa',
    'KENNEDY': 'Kennedy',
    'FONTIBON': 'Fontibón',
    'ENGATIVA': 'Engativá',
    'SUBA': 'Suba',
    'BARRIOS UNIDOS': 'Barrios Unidos',
    'TEUSAQUILLO': 'Teusaquillo',
    'LOS MARTIRES': 'Los Mártires',
    'ANTONIO NARIÑO': 'Antonio Nariño',
    'PUENTE ARANDA': 'Puente Aranda',
    'LA CANDELARIA': 'La Candelaria',
    'RAFAEL URIBE URIBE': 'Rafael Uribe Uribe',
    'CIUDAD BOLIVAR': 'Ciudad Bolívar',
    'SUMAPAZ': 'Sumapaz'
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
    loc_file = download_file(LOC_URL, f"{DATA_RAW_DIR}/localidades.geojson")
    upl_file = download_file(UPL_URL, f"{DATA_RAW_DIR}/upl.geojson")

    print("\nLeyendo GeoJSONs con Geopandas (puede tardar un momento)...")
    gdf_loc = gpd.read_file(loc_file).to_crs(4326)
    gdf_upl = gpd.read_file(upl_file).to_crs(4326)
    
    print("\n--- ANÁLISIS DEL DATASET LOCALIDADES ---")
    print(f"Total filas: {len(gdf_loc)}")
    print(f"Columnas: {gdf_loc.columns.tolist()}")
    print("Primeros 3 registros:")
    print(gdf_loc.head(3))
    
    print("\n--- ANÁLISIS DEL DATASET UPL ---")
    print(f"Total filas: {len(gdf_upl)}")
    print(f"Columnas: {gdf_upl.columns.tolist()}")
    print("Primeros 3 registros:")
    print(gdf_upl.head(3))
    
    loc_name_col = next((c for c in ['LocNombre', 'locnombre', 'nombre', 'NOMBRE'] if c in gdf_loc.columns), None)
    if not loc_name_col:
        loc_name_col = gdf_loc.columns[1]

    print("\nIniciando conexión a PostGIS...")
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        conn.set_client_encoding('UTF8') 
        cur = conn.cursor()
        
        print("Limpiando tablas territoriales antes de re-cargar...")
        cur.execute("TRUNCATE TABLE upl, localidad, zona RESTART IDENTITY CASCADE;")
        conn.commit()

        print("Insertando Zonas (Norte, Sur, Centro, Rural)...")
        zona_ids = {}
        for z_key in ZONAS.keys():
            z_nombre = z_key.title()
            cur.execute("INSERT INTO zona (nombre, descripcion) VALUES (%s, %s) RETURNING id_zona", (z_nombre, f"Zona {z_nombre}"))
            zona_ids[z_key] = cur.fetchone()[0]
            
        print("Preparando inserts de Localidades con WKT y cruce de zonas...")
        loc_ids = {}
        loc_insert = []
        for idx, row in gdf_loc.iterrows():
            name_raw = str(row[loc_name_col])
            name_norm = normalizar_nombre_localidad(name_raw)
            
            id_zona_loc = next((zona_ids[z] for z, locs in ZONAS.items() if name_norm in locs), None)
            if id_zona_loc is None:
                raise ValueError(f"Localidad '{name_raw}' (normalizada: '{name_norm}') no mapeada a ninguna zona. Revisar función normalizar_nombre_localidad o diccionario ZONAS.")

            loc_code = str(row.get('LocCodigo', str(idx+1).zfill(2)))
            wkt = row.geometry.wkt
            
            name_display = NOMBRES_CANONICOS.get(name_norm, name_raw)
            loc_insert.append((id_zona_loc, loc_code, name_display, wkt))

        psycopg2.extras.execute_values(cur, 
            "INSERT INTO localidad (id_zona, codigo_localidad, nombre, geom) VALUES %s", 
            loc_insert,
            template="(%s, %s, %s, ST_GeomFromText(%s, 4326))"
        )
        
        cur.execute("SELECT nombre, id_localidad FROM localidad")
        loc_display_to_id = dict(cur.fetchall())
        
        for display_name, id_loc in loc_display_to_id.items():
            loc_ids[normalizar_nombre_localidad(display_name)] = id_loc

        print(f"✔ Localidades insertadas: {len(loc_insert)}")

        print("Preparando inserts de UPL...")
        upl_insert = []
        name_col_upl = next((c for c in ['UPlNombre', 'nombre', 'UPLNombre', 'UPlTipo'] if c in gdf_upl.columns), gdf_upl.columns[1])
        code_col_upl = next((c for c in ['UPlCodigo', 'codigo'] if c in gdf_upl.columns), 'id')
        
        for idx, row in gdf_upl.iterrows():
            name = str(row.get(name_col_upl, f"UPL_generada_{idx}"))
            code = str(row.get(code_col_upl, f"U{idx}"))
            tipo = str(row.get('UPlTipo', 'UPL')) if 'UPlTipo' in gdf_upl.columns else 'UPL'
            wkt = row.geometry.wkt
            upl_insert.append((code, name, tipo, wkt))

        psycopg2.extras.execute_values(cur,
            "INSERT INTO upl (codigo_upl, nombre, tipo_upl, geom) VALUES %s",
            upl_insert,
            template="(%s, %s, %s, ST_GeomFromText(%s, 4326))"
        )
        print(f"✔ UPLs insertadas: {len(upl_insert)}")
        
        print("Insertando Estratos (Catálogo estático)...")
        estratos = [(1, "Bajo-Bajo"), (2, "Bajo"), (3, "Medio-Bajo"), (4, "Medio"), (5, "Medio-Alto"), (6, "Alto")]
        psycopg2.extras.execute_values(cur, "INSERT INTO estrato (nivel, descripcion) VALUES %s ON CONFLICT DO NOTHING", estratos)
        print(f"✔ Estratos insertados: {len(estratos)}")

        conn.commit()
        cur.close()
        conn.close()
        print("🚀 Carga territorial (Script 01) finalizada exitosamente.")
        
    except Exception as e:
        print(f"❌ Error en la carga ETL: {e}")
        try: conn.rollback() 
        except: pass

if __name__ == "__main__":
    main()
