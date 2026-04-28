# Proyecto Feminicidio Bogotá

Negligencia procesal o administrativa en casos de feminicidio, análisis comparativo entre zona sur y norte de Bogotá, cruzado por estratos socioeconómicos.

## Estructura del Proyecto

- `sql/`: Scripts SQL: DDL, consultas
- `etl/`: Scripts Python para descarga y carga de datos
- `backend/`: FastAPI backend
- `frontend/`: HTML + JS + CSS para dashboards
- `data/`: Datos brutos y procesados (excluidos de git)
- `docs/`: Documentación del proyecto
- `notebooks/`: Jupyter notebooks para exploración de datos

## Instalación

1. Clona el repositorio
2. Crea un entorno virtual (opcional pero recomendado)
3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Configuración 

Copia el archivo `.env.example` y renómbralo a `.env`. Llena los valores reales de conexión a tu base de datos PostGIS.

## Prueba de conexión
Para probar que las librerías y la conexión a la base de datos funcionan, puedes usar el script de testeo:

```bash
python etl/test_conexion.py
```
