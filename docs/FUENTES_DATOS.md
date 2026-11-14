# Fuentes de datos — Observatorio Feminicidio Bogotá

Validación de URLs y APIs realizada el **13 de noviembre de 2026**: todas responden HTTP 200.

## 1. Fuentes estadísticas oficiales (CSV, descargados en abril de 2026)

Los dos CSV se exportaron de datos.gov.co el **17 de abril de 2026**; el sufijo `_20260417` es el que pone Socrata al exportar. Copias locales en `data/raw/fuentes_oficiales/`; no se versionan porque `data/raw/` está en .gitignore. Las cifras se recalculan con `python etl/07_verificar_cifras_oficiales.py`.

| | INMLCF — Presuntos homicidios | Fiscalía — Conteo de víctimas |
|---|---|---|
| Dataset | *Presuntos Homicidios. Colombia, 2015 a 2024. Cifras definitivas* | *Conteo de Víctimas V2*, exportado con filtro a delitos de feminicidio (art. 104A y 104B C.P.) |
| Publicador | Instituto Nacional de Medicina Legal y Ciencias Forenses | Fiscalía General de la Nación |
| ID / URL | `vtub-3de2` · https://www.datos.gov.co/resource/vtub-3de2.json | Sin ID recuperable (ver nota) |
| Cobertura del archivo | Años del hecho **2015–2024**, cifras definitivas (datos actualizados el 2025-09-19) | Año de los hechos **2012–2026** (corte abril 2026) |
| Período usado | 2015–2024 | 2015–2024 |
| Filtro aplicado | Departamento = Bogotá D.C., Sexo = Mujer | Municipio = BOGOTÁ, D.C., SEXO = FEMENINO; suma de `TOTAL_VÍCTIMAS` por `VÍCTIMA_CONSUMADO` |
| Cifra | **1.053** homicidios de mujeres (**1.037** con localidad informada, cargados en la BD) | **253** consumados (SI) · **893** tentativas (NO) |
| Fecha de obtención | 17 de abril de 2026 | 17 de abril de 2026 |
| Archivo | `Presuntos_Homicidios._Colombia,_2015_a_2024._Cifras_definitivas_20260417.csv` (125.284 filas) | `Conteo_de_Víctimas_V2_20260417 - feminicidio.csv` (5.515 filas) |
| SHA-256 | `6af40343c913405af94eadc8b84b285cb01b18017dd04723e349b373f0e9e29e` | `8082895d21498fea2e3464dba5c9b9cdc315e2753cb70132b77f82bec335c2e9` |

Indicadores derivados: tasa de tipificación 253 / 1.053 = **24 %**; 1.053 − 253 = **800** casos sin tipificar; **3,5** tentativas por caso consumado.

**Nota sobre la Fiscalía.** La Fiscalía publicaba "Conteo de víctimas V2" en datos.gov.co; así lo nombra su [guía de consulta de cifras](https://www.fiscalia.gov.co/colombia/wp-content/uploads/PASO-A-PASO-PARA-LA-CONSULTA-DE-CIFRAS-ESTADISTICAS-A-TRAVES-DE-DATOS-ABIERTOS-V3.pdf). Ese dataset ya no aparece en el catálogo. El 25 de mayo de 2026 se publicó su reemplazo, **Víctimas Fiscalía - V3** ([`hr73-zqjf`](https://www.datos.gov.co/resource/hr73-zqjf.json)), con otra estructura: un registro por víctima y proceso, en vez de conteos. Por eso el CSV de abril es la única fuente que reproduce las cifras 253 y 893.

**Calidad del dato.** En el archivo de Fiscalía para Bogotá hay registros con SEXO = MASCULINO o SIN DATO. Se excluyen con el filtro SEXO = FEMENINO.

## 2. Capas geográficas — Datos Abiertos Bogotá (descarga directa GeoJSON)

| Capa | Script | Recurso |
|---|---|---|
| Localidades | 01 | `dataset/856cb657…/resource/497b8756…/download/loca.json` |
| UPL | 01 | `dataset/808582fc…/resource/a5c8c591…/download/unidadplaneamientolocal.json` |
| Barrios legalizados | 04 | `dataset/36a80ef3…/resource/ba69f395…/download/barriolegalizado.json` |
| Comisarías de Familia | 05 | `dataset/16f59d0f…/download/acceso-a-la-justicia-comisarias-de-familia.geojson` |
| Casas de Justicia | 05 | `dataset/7a7f4b3d…/download/casajusticia.geojson` |
| Casas de Igualdad (CIOM, jul-2025) | 05 | `dataset/76b44eeb…/download/ciom_072025.geojson` |
| CAI | 05 | `dataset/bcc51101…/download/comandoatencioninmediata.geojson` |
| OMEG — Riesgo de feminicidio (jun, sep, dic 2025) | 06, 06b, 06c | `dataset/94a36c8e…/riesgofeminicidio_{06,09,12}2025.geojson` |
| OMEG — Asesinatos de mujeres (jun, sep, dic 2025) | 06, 06b, 06c | `dataset/da552105…/asesinatos*_{06,09,12}2025.geojson` |

Las URL completas están en cada script de `etl/`. Las 13 respondieron HTTP 200 el 2026-11-13.

## 3. OMEG (Secretaría Distrital de la Mujer) — datos 2025

Copias locales descargadas el **13 de noviembre de 2026** en `data/raw/omeg/*_descarga20261113.geojson`. `etl/06c_recargar_omeg.py` lee esas copias y solo descarga si faltan.

Los cortes del OMEG son **acumulados en el año**: riesgo 1.161 en junio, 1.997 en septiembre y 2.766 en diciembre. Por eso se carga únicamente el corte del **31-dic-2025** como cifra anual 2025.

| Fuente en BD | Archivo | Corte | Total Bogotá |
|---|---|---|---|
| `OMEG_RIESGO_T3` | `riesgofeminicidio_122025` | 2025-12-31 | **2.766** mujeres valoradas en riesgo de feminicidio |
| `OMEG_ASESINATOS_T3` | `asesinatos_122025` | 2025-12-31 | **109** asesinatos de mujeres |

| Archivo | SHA-256 |
|---|---|
| riesgofeminicidio_122025 | `8b52123c7899a9f4074ded68f3d2707058c275a5a55b464d501e9961d8c6f1bc` |
| asesinatos_122025 | `4e7017f4ade56d51f849c99a3104115d6d34d074a80c33c6998acd182d30c784` |

Inconsistencias del portal:
- `asesinatosmujeres_092025.geojson` trae `Fecha = 2024-12-31` y un total de 116; no es el corte de septiembre de 2025.
- Los archivos de diciembre usan otros nombres de columna (`TAsesinatos`, `TRiesgoFeminicidio`) que los de junio y septiembre (`TAsesinato`, `TRiesgoFem`).

## 4. Cifras en la BD (`feminicidio_agregado`, verificado 2026-11-13)

| Fuente | Casos | Relación |
|---|---|---|
| `INMLCF_HOMICIDIOS` | 1.037 | Total de homicidios de mujeres con localidad, 2015–2024 |
| `INMLCF_SIN_INFO` | 646 | Subconjunto del anterior (circunstancia sin información) |
| `INMLCF_VIOLENCIA_GENERO` | 168 | Subconjunto (feminicidio + violencia o conflicto de pareja) |
| `INMLCF_FEMINICIDIO` | 77 | Subconjunto (circunstancia = Feminicidio, 2018–2024) |
| `OMEG_RIESGO_T3` | 2.766 | 2025, corte anual |
| `OMEG_ASESINATOS_T3` | 109 | 2025, corte anual |

Las fuentes INMLCF no se suman entre sí: las tres últimas son desgloses de `INMLCF_HOMICIDIOS`.
