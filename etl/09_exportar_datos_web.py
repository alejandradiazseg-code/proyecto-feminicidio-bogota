"""
09_exportar_datos_web.py
Exporta a frontend/data/*.json las respuestas de la API que consume la página,
para publicarla como sitio estático (GitHub Pages) sin backend ni base de datos.

Llama directamente a las funciones de backend/main.py: los JSON salen de las
mismas consultas SQL que usa la página en local.

Uso (desde la raíz del proyecto, con la BD en marcha):
    python3 etl/09_exportar_datos_web.py
"""
import inspect
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal

from shapely.geometry import mapping, shape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.main import app  # noqa: E402

DESTINO = "frontend/data"

# ruta de la API → archivo estático (debe coincidir con RUTAS_ESTATICAS en app.js)
EXPORTAR = {
    "/api/indicadores/desierto-institucional": "desierto-institucional.json",
    "/api/indicadores/negligencia-forense":    "negligencia-forense.json",
    "/api/indicadores/brecha-riesgo-muerte":   "brecha-riesgo-muerte.json",
    "/api/localidades/geojson":                "localidades.geojson",
    "/api/feminicidio/por-zona":               "por-zona.json",
    "/api/feminicidio/serie-temporal":         "serie-temporal.json",
    "/api/instituciones":                      "instituciones.geojson",
}

# Simplificación de polígonos para la web (~10 m): reduce el GeoJSON de
# localidades de ~1,6 MB a una fracción, sin cambio visible a escala de ciudad.
TOLERANCIA_GRADOS = 0.0001
DECIMALES = 5


def llamar(ruta):
    """Ejecuta el endpoint con sus valores por defecto (los de Query(...))."""
    endpoint = next(r.endpoint for r in app.routes if getattr(r, "path", None) == ruta)
    kwargs = {}
    for nombre, p in inspect.signature(endpoint).parameters.items():
        defecto = p.default
        kwargs[nombre] = getattr(defecto, "default", defecto)
    return endpoint(**kwargs)


def redondear(obj):
    if isinstance(obj, float):
        return round(obj, DECIMALES)
    if isinstance(obj, (list, tuple)):
        return [redondear(x) for x in obj]
    if isinstance(obj, dict):
        return {k: redondear(v) for k, v in obj.items()}
    return obj


def simplificar(geojson):
    for f in geojson.get("features", []):
        if f.get("geometry") and f["geometry"]["type"] in ("Polygon", "MultiPolygon"):
            g = shape(f["geometry"]).simplify(TOLERANCIA_GRADOS, preserve_topology=True)
            f["geometry"] = redondear(mapping(g))
    return geojson


def serializar(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"No serializable: {type(o)}")


def main():
    os.makedirs(DESTINO, exist_ok=True)
    for ruta, archivo in EXPORTAR.items():
        datos = llamar(ruta)
        if archivo.endswith(".geojson"):
            datos = simplificar(datos)
        destino = os.path.join(DESTINO, archivo)
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, separators=(",", ":"), default=serializar)
        n = len(datos["features"]) if isinstance(datos, dict) and "features" in datos else len(datos)
        print(f"  {archivo:<30} {n:>4} registros  {os.path.getsize(destino) / 1024:>7.1f} KB")

    with open(os.path.join(DESTINO, "exportado.json"), "w", encoding="utf-8") as fh:
        json.dump({"exportado": datetime.now().isoformat(timespec="seconds")}, fh)
    print(f"✔ Datos exportados en {DESTINO}/")


if __name__ == "__main__":
    main()
