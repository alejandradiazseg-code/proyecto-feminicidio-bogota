"""
Script 06c: Carga específica de datos OMEG 2025 con manejo correcto
de columnas y códigos numéricos de localidad.
"""
import os
import requests
import psycopg2
import psycopg2.extras
import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv

# Mapa de código numérico → nombre canónico de localidad
LOCALIDAD_CODIGO = {
    '1': 'Usaquén', '2': 'Chapinero', '3': 'Santa Fe',
    '4': 'San Cristóbal', '5': 'Usme', '6': 'Tunjuelito',
    '7': 'Bosa', '8': 'Kennedy', '9': 'Fontibón',
    '10': 'Engativá', '11': 'Suba', '12': 'Barrios Unidos',
    '13': 'Teusaquillo', '14': 'Los Mártires', '15': 'Antonio Nariño',
    '16': 'Puente Aranda', '17': 'La Candelaria',
    '18': 'Rafael Uribe Uribe', '19': 'Ciudad Bolívar', '20': 'Sumapaz'
}

OMEG_RIESGO = [
    ("https://datosabiertos.bogota.gov.co/dataset/94a36c8e-8a4f-46b7-b75a-00e5c9668ddf/resource/9365d2c6-e9a1-4e48-b209-65ee6b9f2f86/download/riesgofeminicidio_062025.geojson", 2025, "OMEG_RIESGO_T1"),
    ("https://datosabiertos.bogota.gov.co/dataset/94a36c8e-8a4f-46b7-b75a-00e5c9668ddf/resource/efe5dd07-ad41-43ac-9edf-d6717c7ddcfb/download/riesgofeminicidio_092025.geojson", 2025, "OMEG_RIESGO_T2"),
    ("https://datosabiertos.bogota.gov.co/dataset/94a36c8e-8a4f-46b7-b75a-00e5c9668ddf/resource/54e82520-125b-4101-902b-25a74b9e07fc/download/riesgofeminicidio_122025.geojson", 2025, "OMEG_RIESGO_T3"),
]

OMEG_ASESINATOS = [
    ("https://datosabiertos.bogota.gov.co/dataset/da552105-c3e5-49f1-b632-1c6201e96595/resource/db8dc8e9-5f74-48e5-bdf7-3e6fe6bc3c75/download/asesinatosmujeres_062025.geojson", 2025, "OMEG_ASESINATOS_T1"),
    ("https://datosabiertos.bogota.gov.co/dataset/da552105-c3e5-49f1-b632-1c6201e96595/resource/e0195eea-97d9-48fa-b086-c2af60dab654/download/asesinatosmujeres_092025.geojson", 2025, "OMEG_ASESINATOS_T2"),
    ("https://datosabiertos.bogota.gov.co/dataset/da552105-c3e5-49f1-b632-1c6201e96595/resource/3c0f4ddc-05e5-44f0-9f16-3d736a844cf8/download/asesinatos_122025.geojson", 2025, "OMEG_ASESINATOS_T3"),
]


def cargar_omeg(fuentes, col_conteo, col_tasa, loc_id_map):
    inserts = []
    for url, anio, fuente in fuentes:
        try:
            gdf = gpd.read_file(url)
            print(f"  {fuente}: {len(gdf)} filas descargadas")

            for _, row in gdf.iterrows():
                codigo = str(int(float(row['Localidad'])))
                nombre_loc = LOCALIDAD_CODIGO.get(codigo)
                if not nombre_loc:
                    print(f"    WARNING: código {codigo} no reconocido")
                    continue

                id_loc = loc_id_map.get(nombre_loc)
                if not id_loc:
                    print(f"    WARNING: localidad '{nombre_loc}' no en BD")
                    continue

                conteo = row.get(col_conteo)
                tasa = row.get(col_tasa)

                if pd.isna(conteo) or conteo is None:
                    continue

                inserts.append((
                    id_loc,
                    anio,
                    int(float(conteo)),
                    fuente,
                    float(tasa) if pd.notna(tasa) else None,
                    None,
                    f"Código localidad: {codigo}"
                ))

            print(f"  {fuente}: {len([i for i in inserts if i[3]==fuente])} inserts OK")

        except Exception as e:
            print(f"  ERROR en {fuente}: {e}")

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

    # Mapa nombre → id_localidad
    cur.execute("SELECT id_localidad, nombre FROM localidad")
    loc_id_map = {nombre: id_loc for id_loc, nombre in cur.fetchall()}

    print("=" * 60)
    print("CARGANDO OMEG RIESGO FEMINICIDIO 2025")
    print("=" * 60)
    inserts_riesgo = cargar_omeg(OMEG_RIESGO, 'TRiesgoFeminicidio', 'TaRiesgoFemicidio', loc_id_map)

    print("\n" + "=" * 60)
    print("CARGANDO OMEG ASESINATOS MUJERES 2025")
    print("=" * 60)
    inserts_asesinatos = cargar_omeg(OMEG_ASESINATOS, 'TAsesinatos', 'TaAsesinatos', loc_id_map)

    todos = inserts_riesgo + inserts_asesinatos
    print(f"\nTotal filas a insertar: {len(todos)}")

    if todos:
        # Borramos solo las fuentes OMEG (no tocamos INMLCF)
        cur.execute("""
            DELETE FROM feminicidio_agregado
            WHERE fuente LIKE 'OMEG_%';
        """)
        print("Fuentes OMEG anteriores eliminadas.")

        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO feminicidio_agregado
            (id_localidad, anio, conteo_casos, fuente, tasa_por_100k, fecha_corte, observaciones)
            VALUES %s
            """,
            todos
        )
        conn.commit()
        print("✅ OMEG insertado correctamente.")

    # Reporte final
    cur.execute("""
        SELECT fuente, COUNT(*) AS filas,
               SUM(conteo_casos) AS total_casos
        FROM feminicidio_agregado
        GROUP BY fuente
        ORDER BY fuente;
    """)

    print("\n" + "=" * 60)
    print("ESTADO FINAL DE feminicidio_agregado")
    print("=" * 60)
    print(f"{'Fuente':<30} {'Filas':<8} {'Total casos'}")
    print("-" * 60)
    for fuente, filas, total in cur.fetchall():
        print(f"{fuente:<30} {filas:<8} {total}")

    cur.close()
    conn.close()
    print("\n🎉 OMEG cargado exitosamente.")


if __name__ == "__main__":
    main()
