import os
import psycopg2
from dotenv import load_dotenv

def exec_query(cur, title, query):
    print(f"\n--- {title} ---")
    cur.execute(query)
    colnames = [desc[0] for desc in cur.description]
    print(f"{' | '.join(colnames)}")
    print("-" * 50)
    for row in cur.fetchall():
        print(" | ".join(str(val) for val in row))

def main():
    load_dotenv()
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cur = conn.cursor()

    # 1. Conteos Generales
    print("\n1. CONTEOS TOTALES")
    for tbl in ['barrio', 'institucion', 'feminicidio_agregado', 'condiciones_territoriales']:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"Total en {tbl}: {cur.fetchone()[0]}")

    # 2. Instituciones por tipo
    exec_query(cur, "Instituciones por Tipo", 
        "SELECT tipo, COUNT(*) FROM institucion GROUP BY tipo ORDER BY count DESC;")

    # 3. Feminicidios por fuente y año
    exec_query(cur, "Feminicidio Agregado por Fuente", 
        "SELECT fuente, MIN(anio) as anio_min, MAX(anio) as anio_max, SUM(conteo_casos) as casos_totales FROM feminicidio_agregado GROUP BY fuente ORDER BY fuente;")

    # 4. Distribución de instituciones por Zona
    q_zona = """
    SELECT z.nombre as zona, i.tipo, COUNT(i.id_institucion) 
    FROM institucion i
    JOIN localidad l ON i.id_localidad = l.id_localidad
    JOIN zona z ON l.id_zona = z.id_zona
    GROUP BY z.nombre, i.tipo
    ORDER BY z.nombre, i.tipo;
    """
    exec_query(cur, "Distribución de Instituciones por Zona", q_zona)

    # 5. Validación Espacial ST_Within
    q_within = """
    SELECT 
        COUNT(i.id_institucion) as total_instituciones,
        SUM(CASE WHEN ST_Within(i.geom, l.geom) THEN 1 ELSE 0 END) as caen_dentro_poligono_localidad,
        SUM(CASE WHEN NOT ST_Within(i.geom, l.geom) THEN 1 ELSE 0 END) as por_fuera
    FROM institucion i
    JOIN localidad l ON i.id_localidad = l.id_localidad;
    """
    exec_query(cur, "Validación Espacial (Instituciones dentro de su Localidad)", q_within)

    # 6. Densidad de Comisarías por zona (Ejemplo estructural)
    # Suponiendo un total arbitrario de población o usando conteos relativos
    q_densidad = """
    SELECT z.nombre as zona, COUNT(i.id_institucion) as num_comisarias
    FROM institucion i
    JOIN localidad l ON i.id_localidad = l.id_localidad
    JOIN zona z ON l.id_zona = z.id_zona
    WHERE i.tipo = 'COMISARIA_FAMILIA'
    GROUP BY z.nombre
    ORDER BY num_comisarias DESC;
    """
    exec_query(cur, "Comisarías de Familia por Zona", q_densidad)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
