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

## Ejecutar el observatorio en local

Requiere PostgreSQL/PostGIS en marcha con la base cargada. Desde la raíz del proyecto:

```bash
./iniciar_observatorio.sh
```

El script levanta el backend en http://localhost:8000 y la página en http://localhost:5500, y abre el navegador. Para detener ambos, usa Ctrl+C.

Para hacerlo a mano, en dos terminales y siempre desde la raíz del proyecto:

```bash
python3 -m uvicorn backend.main:app --port 8000 --reload
python3 -m http.server 5500 --directory frontend
```

No abras `index.html` con doble clic. Ábrelo por http://localhost:5500.

## Publicar la web (GitHub Pages)

La versión publicada no usa backend: lee los JSON de `frontend/data/`, que se exportan desde la base de datos. Cada vez que cambien los datos:

```bash
python3 etl/09_exportar_datos_web.py   # BD → frontend/data/*.json
python3 etl/10_verificar_web.py        # fuentes = BD = JSON = cifras del HTML
git add frontend && git commit -m "Actualizar datos web"
git push origin main
git subtree push --prefix frontend origin gh-pages   # publica la carpeta frontend/
```

En GitHub, en *Settings → Pages*, se elige *Deploy from a branch* con la rama `gh-pages` y la carpeta `/ (root)`.

Para probar en local con los JSON, sin backend, abre http://localhost:5500/?datos=estaticos.

## Prueba de conexión
Para probar que las librerías y la conexión a la base de datos funcionan, puedes usar el script de testeo:

```bash
python etl/test_conexion.py
```
