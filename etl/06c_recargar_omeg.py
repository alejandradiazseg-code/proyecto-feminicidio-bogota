"""
Script 06c: Carga de datos OMEG (SDMujer) 2025 en feminicidio_agregado.

Los GeoJSON del OMEG son ACUMULADOS en el año (corte jun < sep < dic), por lo
que solo se carga el corte de diciembre de 2025 como cifra anual: sumar los
tres cortes triplicaría los casos. Las fuentes se registran como
OMEG_RIESGO_T3 y OMEG_ASESINATOS_T3 (las consume backend/main.py).

Reproducibilidad: se lee la copia local fechada en data/raw/omeg/; si no
existe, se descarga una nueva con la fecha del día (ver docs/FUENTES_DATOS.md).
"""
import os
import glob
from datetime import date

import geopandas as gpd
import pandas as pd
import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

SNAPSHOT_DIR = "data/raw/omeg"

# Código numérico de localidad usado por el OMEG → nombre canónico en la BD
LOCALIDAD_CODIGO = {
    '1': 'Usaquén', '2': 'Chapinero', '3': 'Santa Fe',
    '4': 'San Cristóbal', '5': 'Usme', '6': 'Tunjuelito',
    '7': 'Bosa', '8': 'Kennedy', '9': 'Fontibón',
    '10': 'Engativá', '11': 'Suba', '12': 'Barrios Unidos',
    '13': 'Teusaquillo', '14': 'Los Mártires', '15': 'Antonio Nariño',
    '16': 'Puente Aranda', '17': 'La Candelaria',
    '18': 'Rafael Uribe Uribe', '19': 'Ciudad Bolívar', '20': 'Sumapaz'
}

# (fuente, url, columna_conteo, columna_tasa) — corte 31-dic-2025
OMEG_CORTE_ANUAL = [
    ("OMEG_RIESGO_T3",
     "https://datosabiertos.bogota.gov.co/dataset/94a36c8e-8a4f-46b7-b75a-00e5c9668ddf/resource/54e82520-125b-4101-902b-25a74b9e07fc/download/riesgofeminicidio_122025.geojson",
     "TRiesgoFeminicidio", "TaRiesgoFemicidio"),
    ("OMEG_ASESINATOS_T3",
     "https://datosabiertos.bogota.gov.co/dataset/da552105-c3e5-49f1-b632-1c6201e96595/resource/3c0f4ddc-05e5-44f0-9f16-3d736a844cf8/download/asesinatos_122025.geojson",
     "TAsesinatos", "TaAsesinatos"),
]


def obtener_snapshot(url):
    """Devuelve la copia local más reciente del recurso, descargándola si no hay."""
    base = os.path.basename(url).removesuffix(".geojson")
    existentes = sorted(glob.glob(f"{SNAPSHOT_DIR}/{base}_descarga*.geojson"))
    if existentes:
        return existentes[-1]
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    destino = f"{SNAPSHOT_DIR}/{base}_descarga{date.today():%Y%m%d}.geojson"
    print(f"  Descargando {url}")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(destino, "wb") as fh:
        fh.write(r.content)
    return destino


def leer_fuente(fuente, url, col_conteo, col_tasa, loc_id_map):
    ruta = obtener_snapshot(url)
    gdf = gpd.read_file(ruta)
    faltan = {col_conteo, col_tasa, "Localidad", "Fecha"} - set(gdf.columns)
    if faltan:
        raise ValueError(f"{fuente}: columnas ausentes {faltan} en {ruta}")

    fechas = pd.to_datetime(gdf["Fecha"]).dt.date.unique()
    if len(fechas) != 1:
        raise ValueError(f"{fuente}: se esperaba una sola fecha de corte, hay {fechas}")
    fecha_corte = fechas[0]

    filas = []
    for _, row in gdf.iterrows():
        codigo = str(int(float(row["Localidad"])))
        nombre = LOCALIDAD_CODIGO.get(codigo)
        if nombre not in loc_id_map:
            raise ValueError(f"{fuente}: localidad con código {codigo} no está en la BD")
        conteo = row[col_conteo]
        if pd.isna(conteo):
            raise ValueError(f"{fuente}: conteo vacío para {nombre}")
        tasa = row[col_tasa]
        filas.append((loc_id_map[nombre], fecha_corte.year, int(conteo), fuente,
                       float(tasa) if pd.notna(tasa) else None, fecha_corte,
                       f"Corte acumulado anual · archivo {os.path.basename(ruta)}"))
    print(f"  {fuente}: {len(filas)} localidades, {sum(f[2] for f in filas)} casos, "
          f"corte {fecha_corte}, archivo {os.path.basename(ruta)}")
    return filas


def main():
    load_dotenv()
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    conn.set_client_encoding("UTF8")
    cur = conn.cursor()

    cur.execute("SELECT nombre, id_localidad FROM localidad")
    loc_id_map = dict(cur.fetchall())

    print("Cargando OMEG 2025 (corte anual al 31-dic-2025)")
    filas = []
    for fuente, url, col_conteo, col_tasa in OMEG_CORTE_ANUAL:
        filas += leer_fuente(fuente, url, col_conteo, col_tasa, loc_id_map)

    # Se reemplazan todas las fuentes OMEG (incluidos cortes T1/T2 que hubiera
    # dejado una versión anterior del ETL); INMLCF no se toca.
    cur.execute("DELETE FROM feminicidio_agregado WHERE fuente LIKE 'OMEG_%'")
    psycopg2.extras.execute_values(
        cur,
        """INSERT INTO feminicidio_agregado
           (id_localidad, anio, conteo_casos, fuente, tasa_por_100k, fecha_corte, observaciones)
           VALUES %s""",
        filas,
    )
    conn.commit()

    cur.execute("""SELECT fuente, COUNT(*), SUM(conteo_casos), MIN(fecha_corte)
                   FROM feminicidio_agregado GROUP BY fuente ORDER BY fuente""")
    print(f"\n{'Fuente':<26}{'Filas':>6}{'Casos':>8}  Corte")
    for fuente, n, total, corte in cur.fetchall():
        print(f"{fuente:<26}{n:>6}{total:>8}  {corte or ''}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
