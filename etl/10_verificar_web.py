"""
10_verificar_web.py
Comprueba que la página web concuerde con los datos: fuentes oficiales → base
de datos → API → JSON publicados → cifras escritas en el HTML.

  1. JSON estáticos (frontend/data) == respuesta actual de la API/BD
  2. BD (INMLCF_HOMICIDIOS) == CSV oficial INMLCF, por año y por localidad
  3. BD (OMEG_*_T3) == copias GeoJSON del OMEG, por localidad
  4. Cifras escritas a mano en index.html == valores recalculados desde los datos
  5. No quedan cifras desactualizadas en la página

Uso (raíz del proyecto, BD en marcha):  python3 etl/10_verificar_web.py
Sale con código 1 si alguna comprobación falla.
"""
import glob
import json
import os
import re
import sys
import unicodedata

import geopandas as gpd
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.database import fetch_all  # noqa: E402
import importlib  # noqa: E402

exportar = importlib.import_module("09_exportar_datos_web")

INMLCF_CSV = "data/raw/fuentes_oficiales/Presuntos_Homicidios._Colombia,_2015_a_2024._Cifras_definitivas_20260417.csv"
FISCALIA_CSV = "data/raw/fuentes_oficiales/Conteo_de_Víctimas_V2_20260417 - feminicidio.csv"
SEGURIDAD = "data/raw/seguridad_nocturna/IndiceSeguridadLocalidad.geojson"
HTML = "frontend/index.html"

fallos = 0


def check(ok, msg):
    global fallos
    print(f"  [{'OK ' if ok else 'DIF'}] {msg}")
    fallos += 0 if ok else 1


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper().strip()
    return {"SANTAFE": "SANTA FE", "MARTIRES": "LOS MARTIRES", "CANDELARIA": "LA CANDELARIA",
            "RAFAEL URIBE": "RAFAEL URIBE URIBE"}.get(s, s)


def es(n, dec=0):
    """Formato es-CO: 1.053 / 3,5"""
    t = f"{n:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return t


def sin_geom(d):
    if isinstance(d, dict) and "features" in d:
        return sorted((json.dumps(f["properties"], sort_keys=True) for f in d["features"]))
    return json.loads(json.dumps(d, default=exportar.serializar))


# ---------------------------------------------------------------------------
print("\n1. JSON publicados vs API/BD actual")
for ruta, archivo in exportar.EXPORTAR.items():
    vivo = exportar.llamar(ruta)
    with open(os.path.join(exportar.DESTINO, archivo), encoding="utf-8") as fh:
        publicado = json.load(fh)
    if archivo.endswith(".geojson"):
        iguales = sin_geom(vivo) == sin_geom(publicado)
    else:
        iguales = exportar.redondear(sin_geom(vivo)) == exportar.redondear(publicado)
    check(iguales, f"{archivo} coincide con {ruta}")

# ---------------------------------------------------------------------------
print("\n2. BD vs CSV oficial INMLCF (vtub-3de2, descargado 17-abr-2026)")
h = pd.read_csv(INMLCF_CSV, dtype=str)
muj = h[h["Departamento del hecho DANE"].str.contains("Bogot", na=False) & (h["Sexo de la victima"] == "Mujer")]
con_loc = muj[muj["Localidad del Hecho"] != "Sin información"]

bd_anio = {r["anio"]: int(r["casos"]) for r in fetch_all(
    "SELECT anio, SUM(conteo_casos) casos FROM feminicidio_agregado WHERE fuente='INMLCF_HOMICIDIOS' GROUP BY anio")}
csv_anio = con_loc["Año del hecho"].astype(int).value_counts().to_dict()
check(bd_anio == csv_anio, f"Homicidios por año (BD {sum(bd_anio.values())} = CSV {sum(csv_anio.values())})")

bd_loc = {norm(r["nombre"]): int(r["casos"]) for r in fetch_all(
    """SELECT l.nombre, SUM(fa.conteo_casos) casos FROM feminicidio_agregado fa
       JOIN localidad l USING (id_localidad) WHERE fa.fuente='INMLCF_HOMICIDIOS' GROUP BY l.nombre""")}
csv_loc = con_loc["Localidad del Hecho"].map(norm).value_counts().to_dict()
difs = {k: (bd_loc.get(k), csv_loc.get(k)) for k in set(bd_loc) | set(csv_loc) if bd_loc.get(k) != csv_loc.get(k)}
check(not difs, "Homicidios por localidad" + (f" — diferencias: {difs}" if difs else ""))

# ---------------------------------------------------------------------------
print("\n3. BD vs copias del OMEG (corte 31-dic-2025)")
for fuente, patron, col in [("OMEG_RIESGO_T3", "riesgofeminicidio_122025", "TRiesgoFeminicidio"),
                            ("OMEG_ASESINATOS_T3", "asesinatos_122025", "TAsesinatos")]:
    archivo = sorted(glob.glob(f"data/raw/omeg/{patron}_descarga*.geojson"))[-1]
    g = gpd.read_file(archivo)
    snap = {int(float(r["Localidad"])): int(r[col]) for _, r in g.iterrows()}
    bd = {int(r["codigo"]): int(r["casos"]) for r in fetch_all(
        """SELECT l.codigo_localidad codigo, fa.conteo_casos casos FROM feminicidio_agregado fa
           JOIN localidad l USING (id_localidad) WHERE fa.fuente=%s""", (fuente,))}
    check(snap == bd, f"{fuente}: {sum(bd.values())} casos en BD = {sum(snap.values())} en {os.path.basename(archivo)}")

# ---------------------------------------------------------------------------
print("\n4. Cifras escritas en la página vs datos")
html = open(HTML, encoding="utf-8").read()
texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script).*?</\1>", "", html, flags=re.S)))

f = pd.read_csv(FISCALIA_CSV, dtype=str)
f["n"] = f["TOTAL_VÍCTIMAS"].astype(int)
fb = f[(f.MUNICIPIO_HECHO == "BOGOTÁ, D.C.") & (f.SEXO == "FEMENINO") & f["AÑO_HECHOS"].between("2015", "2024")]
consumado = int(fb.loc[fb["VÍCTIMA_CONSUMADO"] == "SI", "n"].sum())
tentativa = int(fb.loc[fb["VÍCTIMA_CONSUMADO"] == "NO", "n"].sum())
total_inmlcf = len(muj)
total_bd = sum(bd_anio.values())

inst = {r["tipo"]: int(r["n"]) for r in fetch_all("SELECT tipo, COUNT(*) n FROM institucion GROUP BY tipo")}
neg = fetch_all("SELECT fuente, SUM(conteo_casos) n FROM feminicidio_agregado GROUP BY fuente")
neg = {r["fuente"]: int(r["n"]) for r in neg}
circ = con_loc["Circunstancia del Hecho Detallada"].value_counts()

s = pd.read_csv(INMLCF_CSV, nrows=0)  # noqa: F841  (solo asegura que el CSV existe)
seg = gpd.read_file(SEGURIDAD).drop(columns="geometry")
seg["anio"] = pd.to_datetime(seg.Fecha).dt.year
t = seg[["MUY_BAJO", "BAJO", "MEDIO", "ALTO", "MUY_ALTO"]].fillna(0)
seg["indice"] = (t.MUY_BAJO + 2 * t.BAJO + 3 * t.MEDIO + 4 * t.ALTO + 5 * t.MUY_ALTO) / t.sum(axis=1)
cod_zona = {int(r["codigo"]): r["zona"] for r in fetch_all(
    "SELECT l.codigo_localidad codigo, z.nombre zona FROM localidad l JOIN zona z USING (id_zona)")}
seg["zona"] = seg.LOCCODIGO.astype(int).map(cod_zona)
pz = seg.pivot_table(index="zona", columns="anio", values="indice", aggfunc="mean")
cambio = (pz[2019] - pz[2015]).round(2)

desierto = {r["localidad"]: r for r in fetch_all(
    "SELECT l.nombre localidad, l.poblacion_fem pob, SUM(fa.conteo_casos) hom FROM localidad l "
    "JOIN feminicidio_agregado fa USING (id_localidad) WHERE fa.fuente='INMLCF_HOMICIDIOS' GROUP BY 1, 2")}
pob = {k: int(v["pob"]) for k, v in desierto.items()}
tasa = {k: round(float(v["hom"]) / 10 / int(v["pob"]) * 100000, 1) for k, v in desierto.items()}
rank_candelaria = sorted(tasa.values(), reverse=True).index(tasa["La Candelaria"]) + 1

serie = {r["anio"]: int(r["c"]) for r in fetch_all(
    "SELECT anio, SUM(conteo_casos) c FROM feminicidio_agregado WHERE fuente='INMLCF_HOMICIDIOS' GROUP BY anio")}

esperado = {
    "Homicidios de mujeres INMLCF 2015–2024 (total Bogotá)": es(total_inmlcf),
    "Víctimas de feminicidio consumado · Fiscalía": str(consumado),
    "Víctimas de tentativa · Fiscalía": f"{tentativa} víctimas de tentativa",
    "Tasa de tipificación": f"{round(consumado / total_inmlcf * 100)}%",
    "Por cada 100 asesinadas": f"la Fiscalía registró {round(consumado / total_inmlcf * 100)} víctimas",
    "Diferencia entre fuentes": f"dos fuentes ({total_inmlcf - consumado})",
    "Comisarías de Familia": f"({inst['COMISARIA_FAMILIA']})",
    "Casas de Justicia": f"({inst['CASA_JUSTICIA']})",
    "Casas de Igualdad": f"({inst['CASA_IGUALDAD']})",
    "CAI Policía": f"({inst['CAI']})",
    "Mínimo 2023": f"({serie[2023]} casos",
    "Repunte 2024": f"({serie[2024]} casos",
    "Variación 2023→2024": f"+{round((serie[2024] / serie[2023] - 1) * 100)} %",
    "% sin clasificación": f"{round(neg['INMLCF_SIN_INFO'] / total_bd * 100)} %",
    "Sin clasificación (n de N)": f"{neg['INMLCF_SIN_INFO']} de {es(total_bd)}",
    "Violencia de pareja": f"Violencia de pareja: {circ.get('Violencia de pareja', 0)} casos",
    "Feminicidio explícito": f"Feminicidio explícito: {circ.get('Feminicidio', 0)} casos",
    "Conflicto de pareja": f"Conflicto de pareja: {circ.get('Conflicto de pareja', 0)} casos",
    "Violencia sexual": f"Violencia sexual: {circ.get('Violencia sexual', 0)} casos",
    "Seguridad nocturna Sur 2015→2019": f"+{es(cambio['Sur'], 2)} puntos",
    "Seguridad nocturna Norte 2015→2019": f"(+{es(cambio['Norte'], 2)})",
    "Homicidios La Candelaria": f"Sus {desierto['La Candelaria']['hom']} homicidios se cuentan por lugar del hecho",
    "Tasa La Candelaria": f"({es(tasa['La Candelaria'], 1)} por 100.000 mujeres residentes al año)",
}
for nombre, valor in esperado.items():
    check(valor in texto, f"{nombre}: «{valor}»")
check(neg["INMLCF_FEMINICIDIO"] == circ.get("Feminicidio", 0),
      f"Feminicidio forense BD ({neg['INMLCF_FEMINICIDIO']}) = CSV ({circ.get('Feminicidio', 0)})")
check(pz.loc["Sur", 2019] > pz.loc["Norte", 2019], "En 2019 el índice del Sur supera al del Norte (afirmación del texto)")

# ---------------------------------------------------------------------------
print("\n5. Cifras y frases desactualizadas que no deben aparecer")
for viejo in ["63%", "+0.89", "+0.74", "Violencia de pareja: 80", "89 casos en Bogotá total", "Padilla",
              "112 440",  # línea no verificable, reemplazada por la Línea Púrpura
              "Índice vía formal", "procesos tipificados", "tendencia de mejora sostenida",
              "3,5 tentativas", "casi un punto", "Ver directorio", "es la 3.ª más alta"]:
    check(viejo not in texto, f"no aparece «{viejo}»")

# ---------------------------------------------------------------------------
print("\n6. Calidad de los datos publicados")
inst_json = json.load(open("frontend/data/instituciones.geojson", encoding="utf-8"))["features"]
numericos = [f["properties"]["nombre"] for f in inst_json if re.fullmatch(r"\d+", str(f["properties"]["nombre"] or ""))]
check(not numericos, f"ninguna institución con nombre numérico ({len(numericos)} encontradas)")
sin_dir = [f["properties"]["nombre"] for f in inst_json if not f["properties"]["direccion"]]
check(not sin_dir, f"todas las instituciones tienen dirección de la fuente ({len(sin_dir)} sin dirección)")
check(not any("Ver directorio" in str(f["properties"]["direccion"]) for f in inst_json),
      "las direcciones salen del GeoJSON oficial (no hay textos escritos a mano)")
negf = json.load(open("frontend/data/negligencia-forense.json", encoding="utf-8"))
check(all(r["pct_feminicidio_explicito"] is not None for r in negf if r["homicidios_2018_2024"] > 0),
      "% feminicidio explícito: 0 % (no nulo) donde hay homicidios y ningún feminicidio")
check(all(r["pct_sin_clasificacion"] is not None for r in negf if r["homicidios_total"] > 0),
      "% sin circunstancia: sin nulos donde hay homicidios")
fem = sum(r["feminicidios_forenses"] for r in negf)
h18 = sum(r["homicidios_2018_2024"] for r in negf)
check(fem == neg["INMLCF_FEMINICIDIO"] and h18 > 0,
      f"% feminicidio explícito con el mismo período 2018–2024: {fem} de {h18} = {es(fem / h18 * 100, 1)} %")
des = json.load(open("frontend/data/desierto-institucional.json", encoding="utf-8"))
nulos = [r["localidad"] for r in des if r["casos_por_via_formal"] is None]
check(all((r["comisarias"] + r["casas_justicia"]) == 0 for r in des if r["casos_por_via_formal"] is None),
      f"desierto institucional nulo solo con 0 puntos de atención (no calculable: {', '.join(nulos) or 'ninguna'})")

print(f"\n{'✔ Todo concuerda' if not fallos else f'✘ {fallos} comprobación(es) con diferencias'}")
sys.exit(1 if fallos else 0)
