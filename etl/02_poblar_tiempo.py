import os
import psycopg2
import psycopg2.extras
import pandas as pd
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
    
    print("Generando dimensiones de tiempo 2010 - 2025...")
    dts = pd.date_range(start='2010-01-01', end='2025-12-31', freq='D')
    
    # Spanish translations
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    insert_data = []
    for dt in dts:
        fecha = dt.date().isoformat()
        anio = dt.year
        mes = dt.month
        trimestre = dt.quarter
        dia_semana_str = dias_es[dt.weekday()]
        es_fin = bool(dt.weekday() >= 5)  # 5=Sábado, 6=Domingo
        
        insert_data.append((fecha, anio, mes, trimestre, dia_semana_str, es_fin))
        
    psycopg2.extras.execute_values(cur,
        "INSERT INTO tiempo (fecha, anio, mes, trimestre, dia_semana, es_fin_de_semana) VALUES %s ON CONFLICT DO NOTHING",
        insert_data
    )
    
    print(f"✔ ¡Insertadas {len(insert_data)} filas en la tabla 'tiempo'!")
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
