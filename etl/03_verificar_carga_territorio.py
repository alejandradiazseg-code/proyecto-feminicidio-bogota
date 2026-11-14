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

    # La relación UPL-Localidad es N:M (Modelo Físico §3.1): se resuelve con
    # ST_Intersects. Se descartan contactos de solo borde exigiendo que la
    # intersección cubra al menos el 1 % del área de la UPL.
    print("\n--- Relación N:M UPL ↔ Localidad (intersección ≥ 1 % del área de la UPL) ---")
    cur.execute("""
        SELECT u.codigo_upl, u.nombre,
               COUNT(*) AS localidades,
               STRING_AGG(l.nombre, ', ' ORDER BY l.nombre) AS lista
        FROM upl u
        JOIN localidad l ON ST_Intersects(u.geom, l.geom)
        WHERE ST_Area(ST_Intersection(u.geom, l.geom)) >= 0.01 * ST_Area(u.geom)
        GROUP BY u.codigo_upl, u.nombre
        ORDER BY localidades DESC, u.codigo_upl;
    """)
    for codigo, nombre, n, lista in cur.fetchall():
        print(f"  {codigo:<6} {nombre:<10} {n} localidad(es): {lista}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
