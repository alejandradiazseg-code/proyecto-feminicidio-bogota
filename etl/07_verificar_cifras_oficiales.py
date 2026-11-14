"""
07_verificar_cifras_oficiales.py
Recalcula las cifras oficiales del observatorio a partir de los CSV descargados
de datos.gov.co el 17 de abril de 2026 (ver docs/FUENTES_DATOS.md).

Cifras que debe reproducir (frontend/index.html, sección "Hallazgo Fiscalía"):
  - INMLCF : 1.053 homicidios de mujeres en Bogotá 2015–2024
             (1.037 con localidad del hecho informada → cargados en la BD)
  - Fiscalía: 253 víctimas de feminicidio consumado y 893 tentativas,
             Bogotá, sexo femenino, año de los hechos 2015–2024
  - Tasa de tipificación: 253 / 1.053 = 24 %

Uso:  python etl/07_verificar_cifras_oficiales.py
"""
import sys
import pandas as pd

DIR = "data/raw/fuentes_oficiales"
FISCALIA_CSV = f"{DIR}/Conteo_de_Víctimas_V2_20260417 - feminicidio.csv"
INMLCF_CSV = f"{DIR}/Presuntos_Homicidios._Colombia,_2015_a_2024._Cifras_definitivas_20260417.csv"
ANIO_INI, ANIO_FIN = "2015", "2024"

ESPERADO = {"inmlcf_mujeres": 1053, "inmlcf_con_localidad": 1037,
            "fiscalia_consumado": 253, "fiscalia_tentativa": 893}


def main():
    # --- INMLCF (datos.gov.co vtub-3de2) ---
    h = pd.read_csv(INMLCF_CSV, dtype=str)
    print(f"INMLCF: {len(h):,} registros nacionales, años {h['Año del hecho'].min()}–{h['Año del hecho'].max()}")
    m = h[h["Departamento del hecho DANE"].str.contains("Bogot", na=False)
          & (h["Sexo de la victima"] == "Mujer")
          & h["Año del hecho"].between(ANIO_INI, ANIO_FIN)]
    inmlcf_mujeres = len(m)
    inmlcf_loc = int((m["Localidad del Hecho"] != "Sin información").sum())

    # --- Fiscalía (Conteo de Víctimas V2, filtrado a delitos de feminicidio) ---
    f = pd.read_csv(FISCALIA_CSV, dtype=str)
    f["n"] = f["TOTAL_VÍCTIMAS"].astype(int)
    print(f"Fiscalía: {len(f):,} filas nacionales, año de los hechos "
          f"{f['AÑO_HECHOS'].min()}–{f['AÑO_HECHOS'].max()}")
    b = f[(f["MUNICIPIO_HECHO"] == "BOGOTÁ, D.C.")
          & (f["SEXO"] == "FEMENINO")
          & f["AÑO_HECHOS"].between(ANIO_INI, ANIO_FIN)]
    por_grado = b.groupby("VÍCTIMA_CONSUMADO")["n"].sum()

    obtenido = {"inmlcf_mujeres": inmlcf_mujeres, "inmlcf_con_localidad": inmlcf_loc,
                "fiscalia_consumado": int(por_grado.get("SI", 0)),
                "fiscalia_tentativa": int(por_grado.get("NO", 0))}

    print(f"\nPeríodo analizado: {ANIO_INI}–{ANIO_FIN} · Bogotá D.C.")
    ok = True
    for k, esperado in ESPERADO.items():
        estado = "OK " if obtenido[k] == esperado else "DIF"
        ok &= obtenido[k] == esperado
        print(f"  [{estado}] {k:<22} obtenido={obtenido[k]:>5}  esperado={esperado:>5}")
    tasa = obtenido["fiscalia_consumado"] / obtenido["inmlcf_mujeres"]
    print(f"  Tasa de tipificación: {tasa:.1%}  |  tentativas por consumado: "
          f"{obtenido['fiscalia_tentativa'] / obtenido['fiscalia_consumado']:.1f}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
