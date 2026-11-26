import os
import requests
import psycopg2
import psycopg2.extras
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from dotenv import load_dotenv

DATA_RAW_DIR = "data/raw"

FUENTES = {
    'COMISARIA_FAMILIA': 'https://datosabiertos.bogota.gov.co/dataset/16f59d0f-f37b-4297-b2b7-3e1fbcc406cc/resource/97a96ebb-0e8e-4c98-bbd5-6633db251eba/download/acceso-a-la-justicia-comisarias-de-familia.geojson',
    'CASA_JUSTICIA': 'https://datosabiertos.bogota.gov.co/dataset/7a7f4b3d-c01e-4e0d-a5fc-89fc3eacefc3/resource/b5f1a08a-f21c-4208-862f-46d331cc5a3a/download/casajusticia.geojson',
    'CASA_IGUALDAD': 'https://datosabiertos.bogota.gov.co/dataset/76b44eeb-c825-4fd2-9318-ff2fc6becfec/resource/b64f469d-8204-428e-bdaa-bec7cee830eb/download/ciom_072025.geojson',
    'CAI': 'https://datosabiertos.bogota.gov.co/dataset/bcc51101-762b-4e13-9455-f77502c75a0f/resource/202c5810-6880-43f8-b801-df70aaf6d237/download/comandoatencioninmediata.geojson'
}

# Columna de cada campo en el GeoJSON de cada fuente (verificadas el 25-nov-2026).
COLUMNAS = {
    'COMISARIA_FAMILIA': {'nombre': 'OSSUOpera', 'direccion': 'OSSDirecc', 'telefono': 'OSSTelefo', 'horario': 'OSSHAtenc'},
    'CASA_JUSTICIA':     {'nombre': 'CJUNOMBRE', 'direccion': 'CJUDIR_SIT', 'telefono': 'CJUTELEFON', 'horario': 'CJUHORARIO'},
    'CASA_IGUALDAD':     {'nombre': 'CIONombre', 'direccion': 'CIODirecci', 'telefono': 'CIOTelefon', 'horario': 'CIOHorario'},
    'CAI':               {'nombre': 'CAINOMBRE', 'direccion': 'CAIDIR_SIT', 'telefono': 'CAITELEFON', 'horario': 'CAIHORARIO'},
}


def columna_exacta(gdf, tipo, campo):
    col = COLUMNAS[tipo][campo]
    if col not in gdf.columns:
        raise KeyError(f"{tipo}: no existe la columna '{col}' ({campo}). Columnas: {gdf.columns.tolist()}")
    return col


def acortar(texto, maximo):
    """Ajusta el texto al largo del Modelo Físico (telefono VARCHAR(30)).
    Varias comisarías listan todas sus extensiones; se corta en un separador
    y se marca con «…» para que no parezca un número completo."""
    texto = " ".join(texto.split())
    if len(texto) <= maximo:
        return texto
    corte = texto[:maximo - 1]
    pos = max(corte.rfind(s) for s in (" ", ",", "-"))
    return (corte[:pos] if pos > 0 else corte).rstrip(" ,-") + "…"


def download_file(url, dest_path):
    if not os.path.exists(dest_path):
        print(f"Descargando {url}...")
        r = requests.get(url)
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            f.write(r.content)
    return dest_path

def main():
    load_dotenv()
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    
    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    conn.set_client_encoding('UTF8') 
    cur = conn.cursor()
    
    # 1. Extraer Localidades
    print("Extrayendo Localidades para cruce espacial...")
    gdf_loc = gpd.GeoDataFrame.from_postgis("SELECT id_localidad, nombre, geom FROM localidad", conn, geom_col='geom', crs=4326)

    cur.execute("TRUNCATE TABLE institucion RESTART IDENTITY CASCADE;")
    
    instituciones_insert = []
    
    # 2. Iterar por tipos de instituciones y hacer Spatial Join
    for tipo, url in FUENTES.items():
        fname = f"{DATA_RAW_DIR}/{tipo.lower()}.geojson"
        download_file(url, fname)
        gdf = gpd.read_file(fname).to_crs(4326)
        
        print(f"\n--- {tipo} ---")
        print(f"Total: {len(gdf)}")
        print(f"Cols: {gdf.columns.tolist()}")

        # Columnas exactas de cada GeoJSON (nombre, dirección, teléfono, horario).
        # Sin valores por defecto: si la fuente cambia sus columnas, el ETL se
        # detiene y dice cuál falta, en vez de cargar en silencio otra columna
        # (antes se tomaba gdf.columns[1] y las Casas de Justicia quedaban con
        # el código de entidad «137» como nombre).
        name_col, dir_col, tel_col, horario_col = (
            columna_exacta(gdf, tipo, campo) for campo in ('nombre', 'direccion', 'telefono', 'horario'))

        # Spatial join para buscar id_localidad
        joined = gpd.sjoin(gdf, gdf_loc, how='left', predicate='within')

        for idx, row in joined.iterrows():
            id_loc = None if pd.isna(row['id_localidad']) else int(row['id_localidad'])
            if pd.isna(row[name_col]) or not str(row[name_col]).strip():
                raise ValueError(f"{tipo}: registro {idx} sin nombre en la columna {name_col}")
            nombre = str(row[name_col]).strip()
            direccion = str(row[dir_col]) if dir_col and not pd.isna(row[dir_col]) else None
            telefono = acortar(str(row[tel_col]), 30) if not pd.isna(row[tel_col]) else None
            horario = str(row[horario_col]) if horario_col and not pd.isna(row[horario_col]) else None
            wkt = row['geometry'].wkt
            
            instituciones_insert.append((id_loc, tipo, nombre, direccion, telefono, horario, wkt))

    # 3. Eliminar hardcode de Casa de Todas
    # NOTA METODOLÓGICA: Casa de Todas fue excluida del análisis. 
    # Su misión es específicamente atender a mujeres que ejercen Actividades Sexuales Pagadas (ASP), 
    # por lo que no es una ruta formal de atención general a violencias contra mujeres/feminicidio.
    
    print("\nInsertando en BD...")
    psycopg2.extras.execute_values(cur, 
        "INSERT INTO institucion (id_localidad, tipo, nombre, direccion, telefono, horario_atencion, geom) VALUES %s", 
        instituciones_insert,
        template="(%s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))"
    )
    
    conn.commit()
    cur.close()
    conn.close()
    
    conteo = pd.Series([i[1] for i in instituciones_insert]).value_counts()
    print("🚀 Instituciones insertadas:")
    print(conteo)
    
if __name__ == "__main__":
    main()
