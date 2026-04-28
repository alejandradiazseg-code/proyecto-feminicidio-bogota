import os
import psycopg2
from dotenv import load_dotenv

def test_connection():
    # Cargar variables de entorno desde .env
    load_dotenv()
    
    # Obtener variables
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    
    print(f"Intentando conectar a {dbname} en {host}:{port} con usuario {user}...")
    
    try:
        # Establecer conexión
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        
        cur = conn.cursor()
        
        # Ejecutar SELECT PostGIS_Version()
        print("\nVerificando versión de PostGIS:")
        cur.execute("SELECT PostGIS_Version();")
        postgis_version = cur.fetchone()[0]
        print(f"✅ {postgis_version}")
        
        # Ejecutar SELECT current_database(), current_user
        print("\nVerificando base de datos y usuario actuales:")
        cur.execute("SELECT current_database(), current_user;")
        db_user = cur.fetchone()
        print(f"✅ Base de datos: {db_user[0]}")
        print(f"✅ Usuario: {db_user[1]}")
        
        # Cerrar cursor y conexión
        cur.close()
        conn.close()
        print("\n✅ Conexión cerrada exitosamente. Todo está funcionando correctamente.")
        
    except Exception as e:
        print("\n❌ Error al intentar conectar o enviar consultas a la base de datos:")
        print(e)
        
if __name__ == "__main__":
    test_connection()
