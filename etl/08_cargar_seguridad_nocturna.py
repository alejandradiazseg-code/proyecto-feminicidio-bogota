"""
Script 08: Carga del Índice de Condiciones de Seguridad Nocturna para Mujeres.
Fuente: Secretaría Distrital de la Mujer - SDMujer / IDECA
Cobertura: 20 localidades, dos mediciones: 2015 y 2019.
"""
import os
import json
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

RUTA_GEOJSON = os.path.expanduser(
    "~/proyecto-feminicidio/data/raw/seguridad_nocturna/IndiceSeguridadLocalidad.geojson"
)

def calcular_indice(props):
    muy_bajo = props.get('MUY_BAJO', 0) or 0
    bajo     = props.get('BAJO', 0) or 0
    medio    = props.get('MEDIO', 0) or 0
    alto     = props.get('ALTO', 0) or 0
    muy_alto = props.get('MUY_ALTO', 0) or 0
    total    = muy_bajo + bajo + medio + alto + muy_alto
    if total == 0:
        return None
    return round((muy_bajo*1 + bajo*2 + medio*3 + alto*4 + muy_alto*5) / total, 4)

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

    cur.execute("SELECT id_localidad, codigo_localidad FROM localidad")
    mapa = {}
    for id_loc, cod in cur.fetchall():
        mapa[cod] = id_loc
        mapa[str(int(cod))] = id_loc

    with open(RUTA_GEOJSON, encoding='utf-8') as f:
        data = json.load(f)

    features = data.get('features', [])
    print(f"Features en GeoJSON: {len(features)}")

    registros = {}
    sin_match = []

    for feat in features:
        props = feat['properties']
        cod_raw = str(props.get('LOCCODIGO', '')).strip()
        id_loc = mapa.get(cod_raw.zfill(2)) or mapa.get(cod_raw)
        if not id_loc:
            sin_match.append(cod_raw)
            continue
        anio = int(props.get('Fecha', '2019/01/01').split('/')[0])
        registros[(id_loc, anio)] = {
            'indice':     calcular_indice(props),
            'iluminacion': round((props.get('P_ILUMINAC', 0) or 0) / 100, 4),
            'transporte':  round((props.get('P_TRANSPOR', 0) or 0) / 100, 4),
        }

    print(f"Registros procesados: {len(registros)}")
    if sin_match:
        print(f"Sin match: {sin_match}")

    # ST_Intersects también es verdadero cuando dos polígonos solo comparten un
    # borde o se solapan en una astilla por diferencias de digitalización (75 de
    # 127 pares eran < 1 % del área de la UPL). Por eso cada UPL toma el valor de
    # la localidad con la que comparte MÁS área (una fila por UPL y año).
    cur.execute("""
        SELECT DISTINCT ON (u.id_upl) u.id_upl, l.id_localidad
        FROM upl u
        JOIN localidad l ON ST_Intersects(u.geom, l.geom)
        ORDER BY u.id_upl, ST_Area(ST_Intersection(u.geom, l.geom)::geography) DESC
    """)
    pares = cur.fetchall()
    print(f"UPL asignadas a su localidad de mayor área común: {len(pares)}")

    inserts = []
    for id_upl, id_loc in pares:
        for anio in [2015, 2019]:
            r = registros.get((id_loc, anio))
            if r:
                inserts.append((
                    id_upl,
                    anio,
                    r['indice'],
                    r['iluminacion'],
                    r['transporte'],
                    None,
                    None,
                ))

    print(f"Filas a insertar: {len(inserts)}")

    cur.execute("TRUNCATE TABLE condiciones_territoriales RESTART IDENTITY CASCADE;")
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO condiciones_territoriales
            (id_upl, anio_medicion, indice_seguridad_nocturna,
             cobertura_iluminacion, accesibilidad_transporte,
             densidad_institucional, tipo_entorno_urbano)
        VALUES %s
        """,
        inserts
    )
    conn.commit()

    cur.execute("""
        SELECT l.nombre, ct.anio_medicion,
               ROUND(AVG(ct.indice_seguridad_nocturna)::numeric, 4) AS indice,
               ROUND(AVG(ct.cobertura_iluminacion)::numeric, 2) AS ilum_pct,
               COUNT(*) AS upls
        FROM condiciones_territoriales ct
        JOIN upl u ON u.id_upl = ct.id_upl
        JOIN localidad l ON ST_Intersects(u.geom, l.geom)
        GROUP BY l.nombre, ct.anio_medicion
        ORDER BY ct.anio_medicion, indice ASC
        LIMIT 20;
    """)

    print(f"\n{'Localidad':<22} {'Año':<6} {'Índice':>8} {'Ilum%':>8} {'UPLs':>6}")
    print("-" * 55)
    for row in cur.fetchall():
        print(f"  {row[0]:<20} {row[1]:<6} {str(row[2]):>8} {str(row[3]):>8} {row[4]:>6}")

    cur.close()
    conn.close()
    print("\n✅ Carga completada")

if __name__ == "__main__":
    main()
