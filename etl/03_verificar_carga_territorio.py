import os
import psycopg2
from dotenv import load_dotenv

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
    
    queries = [
        ("COUNT Zona", "SELECT count(*) FROM zona"),
        ("COUNT Localidad", "SELECT count(*) FROM localidad"),
        ("COUNT UPL", "SELECT count(*) FROM upl"),
        ("COUNT Estrato", "SELECT count(*) FROM estrato"),
        ("COUNT Tiempo", "SELECT count(*) FROM tiempo"),
        ("Areas Zonas (KM2)", "SELECT nombre, ROUND((ST_Area(geom::geography)/1000000)::numeric, 2) AS area_km2 FROM zona ORDER BY area_km2 DESC"),
        ("Conteo Locs x Zona", "SELECT z.nombre AS zona, COUNT(l.*) AS total FROM zona z LEFT JOIN localidad l ON l.id_zona = z.id_zona GROUP BY z.nombre ORDER BY z.nombre"),
        ("Locs x Zona", "SELECT z.nombre AS zona, l.nombre FROM localidad l JOIN zona z ON l.id_zona = z.id_zona ORDER BY z.nombre, l.nombre")
    ]
    
    for title, q in queries:
        print(f"\n--- {title} ---")
        try:
            cur.execute(q)
            res = cur.fetchall()
            for r in res: print(r)
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()

    print("\n--- ST_Within UPL en Localidad (Revisando si UPLs se salen de su Localidad asignada) ---")
    st_within_q = """
    SELECT u.nombre AS upl, l.nombre AS loc
    FROM upl u
    JOIN localidad l ON u.id_localidad = l.id_localidad
    WHERE ST_Within(ST_Centroid(u.geom), l.geom) = FALSE;
    """
    cur.execute(st_within_q)
    falsos = cur.fetchall()
    if not falsos:
        print("✅ Todas las UPLs (evaluando por centroide) caen correctamente dentro del polígono de su Localidad.")
    else:
        print(f"⚠️ Hay {len(falsos)} UPLs con su centroide fuera del polígono directo de su Localidad: {falsos}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
