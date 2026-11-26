const API_BASE = "http://localhost:8000/api";

// Modo de datos:
//  - En local (localhost) se consulta la API FastAPI sobre PostGIS.
//  - Publicada (GitHub Pages) se leen los JSON exportados por
//    etl/09_exportar_datos_web.py en frontend/data/.
//  - ?datos=estaticos fuerza los JSON también en local (para probar).
const ES_LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);
const MODO_ESTATICO = !ES_LOCAL || new URLSearchParams(location.search).get("datos") === "estaticos";
const RUTAS_ESTATICAS = {
    "/indicadores/desierto-institucional": "data/desierto-institucional.json",
    "/indicadores/negligencia-forense":    "data/negligencia-forense.json",
    "/indicadores/brecha-riesgo-muerte":   "data/brecha-riesgo-muerte.json",
    "/localidades/geojson":                "data/localidades.geojson",
    "/feminicidio/por-zona":               "data/por-zona.json",
    "/feminicidio/serie-temporal":         "data/serie-temporal.json",
    "/instituciones":                      "data/instituciones.geojson",
};
const _cache = {};

async function obtenerDatos(ruta) {
    if (!MODO_ESTATICO) {
        const r = await fetch(`${API_BASE}${ruta}`);
        if (!r.ok) throw new Error(`${ruta}: HTTP ${r.status}`);
        return r.json();
    }
    // Estático: /instituciones?tipo=X se filtra en el navegador
    const [path, query] = ruta.split("?");
    const archivo = RUTAS_ESTATICAS[path];
    if (!archivo) throw new Error(`Sin archivo estático para ${path}`);
    _cache[archivo] ??= fetch(archivo).then(r => {
        if (!r.ok) throw new Error(`${archivo}: HTTP ${r.status}`);
        return r.json();
    });
    const datos = await _cache[archivo];
    const tipo = new URLSearchParams(query || "").get("tipo");
    return tipo ? { ...datos, features: datos.features.filter(f => f.properties.tipo === tipo) } : datos;
}

const COLORES_ZONA = {
    "Norte": "#29b6f6", "Sur": "#ef5350",
    "Centro": "#ffa726", "Rural": "#66bb6a"
};
const COLORES_INST = {
    "COMISARIA_FAMILIA": "#d32f2f", "CASA_JUSTICIA": "#f57c00",
    "CASA_IGUALDAD": "#0288d1", "CAI": "#546e7a"
};

let mapa, capaLocalidades, capasInst = {}, capaActiva = "homicidios";
let datosIndicadores = [], datosNegligencia = [], datosBrecha = [], datosLocalidades = {};
let todosInstsData = {};

// Tipografía de las gráficas acorde al tamaño base de la página (crece en pantallas grandes)
if (window.Chart) {
    const base = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    Chart.defaults.font.size = Math.round(base * 0.8);
    Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
}

document.addEventListener("DOMContentLoaded", async () => {
    inicializarMapa();
    await cargarTodo();
    configurarEventos();
});

function inicializarMapa() {
    mapa = L.map("mapa").setView([4.65, -74.1], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: "© OpenStreetMap contributors"
    }).addTo(mapa);
}

async function cargarTodo() {
    try {
        const [indic, neglig, brecha, geojson, porZona, serie, instituciones] = await Promise.all([
            obtenerDatos("/indicadores/desierto-institucional"),
            obtenerDatos("/indicadores/negligencia-forense"),
            obtenerDatos("/indicadores/brecha-riesgo-muerte"),
            obtenerDatos("/localidades/geojson"),
            obtenerDatos("/feminicidio/por-zona"),
            obtenerDatos("/feminicidio/serie-temporal"),
            obtenerDatos("/instituciones")
        ]);

        datosIndicadores = indic;
        datosNegligencia = neglig;
        datosBrecha = brecha;
        datosIndicadores.forEach(d => datosLocalidades[d.localidad] = d);

        if (instituciones.features) {
            instituciones.features.forEach(f => {
                const loc = f.properties.localidad;
                if (!todosInstsData[loc]) todosInstsData[loc] = [];
                todosInstsData[loc].push(f.properties);
            });
        }

        actualizarHeroYKPIs();
        actualizarIndicadoresNegligencia();
        poblarSelectLocalidades();
        pintarLocalidades(geojson);
        await cargarInstituciones();
        dibujarChartZonas(porZona);
        dibujarChartSerie(serie);
        dibujarChartIndicador(datosIndicadores);

    } catch (err) {
        console.error("Error:", err);
        alert(MODO_ESTATICO
            ? "No se pudieron cargar los datos del observatorio. Recarga la página."
            : "Error al conectar con el backend. Verifica que FastAPI esté en http://localhost:8000 (o abre la página con ?datos=estaticos).");
    }
}

// ── HERO Y KPIs ───────────────────────────────────────────

function actualizarHeroYKPIs() {
    const totalHom   = datosNegligencia.reduce((s, d) => s + (d.homicidios_total || 0), 0);
    const totalFem   = datosNegligencia.reduce((s, d) => s + (d.feminicidios_forenses || 0), 0);
    const totalSI    = datosNegligencia.reduce((s, d) => s + (d.sin_clasificacion || 0), 0);
    const totalRiesgo = datosBrecha.reduce((s, d) => s + (d.mujeres_en_riesgo_2025 || 0), 0);

    animarNumero("hero-homicidios", totalHom);
    animarNumero("hero-feminicidios", totalFem);
    animarNumero("hero-riesgo", totalRiesgo);
    animarNumero("kpi-homicidios", totalHom);
    animarNumero("kpi-feminicidios", totalFem);
    animarNumero("kpi-sin-info", totalSI);
    const hom18 = datosNegligencia.reduce((s, d) => s + (d.homicidios_2018_2024 || 0), 0);
    const kfd = document.getElementById("kpi-feminicidios-detalle");
    if (kfd && hom18) kfd.textContent =
        `Circunstancia «Feminicidio» (INMLCF, categoría usada desde 2018) · ${fmtNum(totalFem / hom18 * 100, 1)} % de ${fmtNum(hom18)} homicidios 2018–2024`;

    const conInd = datosIndicadores.filter(d => d.casos_por_via_formal != null);
    if (conInd.length > 0) {
        const peor = conInd.reduce((m, d) => d.casos_por_via_formal > m.casos_por_via_formal ? d : m);
        document.getElementById("kpi-peor").textContent = peor.localidad;
        document.getElementById("kpi-peor-valor").textContent = `${fmtNum(peor.casos_por_via_formal, 1)} homicidios por comisaría o casa de justicia`;
    }
}

function animarNumero(id, fin) {
    const el = document.getElementById(id);
    if (!el) return;
    let inicio = 0;
    const dur = 1500, paso = dur / 60;
    const incremento = fin / (dur / paso);
    const timer = setInterval(() => {
        inicio += incremento;
        if (inicio >= fin) { inicio = fin; clearInterval(timer); }
        el.textContent = fmtNum(Math.floor(inicio));
    }, paso);
}

// ── INDICADORES DE NEGLIGENCIA ─────────────────────────────

function actualizarIndicadoresNegligencia() {
    // Zona urbana: Sumapaz (rural, 1 caso en 10 años) no es comparable como "mejor" localidad
    const conInd = datosIndicadores.filter(d => d.casos_por_via_formal != null && d.zona !== "Rural");
    if (conInd.length > 0) {
        const peor  = conInd.reduce((m, d) => d.casos_por_via_formal > m.casos_por_via_formal ? d : m);
        const mejor = conInd.reduce((m, d) => d.casos_por_via_formal < m.casos_por_via_formal ? d : m);
        document.getElementById("ind-via-formal").textContent = fmtNum(peor.casos_por_via_formal, 1);
        document.getElementById("ind-via-formal-peor").textContent =
            `⬆ Peor: ${peor.localidad} (${fmtNum(peor.casos_por_via_formal, 1)} homicidios por punto de atención)`;
        document.getElementById("ind-via-formal-mejor").textContent =
            `⬇ Mejor (zona urbana): ${mejor.localidad} (${fmtNum(mejor.casos_por_via_formal, 1)} homicidios por punto de atención)`;
    }

    const conSI = datosNegligencia.filter(d => d.pct_sin_clasificacion != null);
    if (conSI.length > 0) {
        const peorSI  = conSI.reduce((m, d) => d.pct_sin_clasificacion > m.pct_sin_clasificacion ? d : m);
        const urbSI   = conSI.filter(d => d.zona !== "Rural");   // Sumapaz: 1 caso en 10 años
        const mejorSI = urbSI.reduce((m, d) => d.pct_sin_clasificacion < m.pct_sin_clasificacion ? d : m);
        // Bogotá total, calculado con los mismos datos de la tabla
        const totSI  = datosNegligencia.reduce((s, d) => s + (d.sin_clasificacion || 0), 0);
        const totHom = datosNegligencia.reduce((s, d) => s + (d.homicidios_total || 0), 0);
        document.getElementById("ind-sin-info").textContent = totHom ? fmtNum(totSI / totHom * 100) + " %" : "—";
        document.getElementById("ind-sin-info-peor").textContent =
            `⬆ Peor: ${peorSI.localidad} (${fmtNum(peorSI.pct_sin_clasificacion)} %)`;
        document.getElementById("ind-sin-info-mejor").textContent =
            `⬇ Mejor (zona urbana): ${mejorSI.localidad} (${fmtNum(mejorSI.pct_sin_clasificacion)} %)`;
    }

    const conBrecha = datosBrecha.filter(d => d.tasa_conversion_pct != null && d.tasa_conversion_pct > 0);
    if (conBrecha.length > 0) {
        const peorB  = conBrecha.reduce((m, d) => d.tasa_conversion_pct > m.tasa_conversion_pct ? d : m);
        const mejorB = conBrecha.reduce((m, d) => d.tasa_conversion_pct < m.tasa_conversion_pct ? d : m);
        document.getElementById("ind-brecha").textContent = fmtNum(peorB.tasa_conversion_pct, 1);
        document.getElementById("ind-brecha-peor").textContent =
            `⬆ Peor: ${peorB.localidad} · ${peorB.asesinadas_2025} asesinatos frente a ${peorB.mujeres_en_riesgo_2025} mujeres en riesgo`;
        document.getElementById("ind-brecha-mejor").textContent =
            `⬇ Menor: ${mejorB.localidad} (${fmtNum(mejorB.tasa_conversion_pct, 1)} por cada 100)`;
    }
}

// ── MAPA ──────────────────────────────────────────────────

function pintarLocalidades(geojson) {
    if (capaLocalidades) mapa.removeLayer(capaLocalidades);
    capaLocalidades = L.geoJSON(geojson, {
        style: f => estiloLocalidad(f),
        onEachFeature: (f, layer) => {
            const nom  = f.properties.nombre;
            const zona = f.properties.zona;
            const d = datosLocalidades[nom] || {};
            const n = datosNegligencia.find(x => x.localidad === nom) || {};
            const b = datosBrecha.find(x => x.localidad === nom) || {};
            layer.bindPopup(`
                <div style="min-width:240px;font-family:'Segoe UI',sans-serif;">
                    <h6 style="color:#4a148c;margin-bottom:6px;">${nom}</h6>
                    <span style="background:${COLORES_ZONA[zona]};color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem;">Zona ${zona}</span>
                    <hr style="margin:8px 0;">
                    <table style="width:100%;font-size:0.82rem;">
                        <tr><td>🔪 Homicidios 2015–2024</td><td><b>${n.homicidios_total || 0}</b></td></tr>
                        <tr><td>📈 Tasa anual por 100.000 mujeres</td><td><b>${d.tasa_anual_100k != null ? fmtNum(d.tasa_anual_100k, 1) : '—'}</b></td></tr>
                        <tr><td>⚡ Feminicidios forenses 2018–2024</td><td><b>${n.feminicidios_forenses || 0}${n.pct_feminicidio_explicito != null ? ` (${fmtNum(n.pct_feminicidio_explicito, 1)} %)` : ''}</b></td></tr>
                        <tr><td>❓ Sin circunstancia registrada</td><td><b>${n.sin_clasificacion || 0} (${fmtNum(n.pct_sin_clasificacion || 0, 1)} %)</b></td></tr>
                        <tr><td>📊 Desierto institucional</td><td><b>${d.casos_por_via_formal != null ? fmtNum(d.casos_por_via_formal, 1) : 'no calculable (0 puntos)'}</b></td></tr>
                        <tr><td>🚨 Homicidios por CAI</td><td><b>${d.casos_por_cai != null ? fmtNum(d.casos_por_cai, 1) : '—'}</b></td></tr>
                        <tr><td>👥 En riesgo 2025</td><td><b>${b.mujeres_en_riesgo_2025 || 0}</b></td></tr>
                        <tr><td>💀 Asesinadas 2025</td><td><b>${b.asesinadas_2025 || 0}</b></td></tr>
                    </table>
                    <hr style="margin:8px 0;">
                    <small style="color:#666;">🏛 Comisarías: ${d.comisarias || 0} · ⚖️ Casas Justicia: ${d.casas_justicia || 0} · 🤝 Igualdad: ${d.casas_igualdad || 0} · 🚓 CAI: ${d.cais || 0}</small>
                </div>
            `);
            layer.on("mouseover", () => layer.setStyle({ weight: 3, fillOpacity: 0.9 }));
            layer.on("mouseout",  () => capaLocalidades.resetStyle(layer));
        }
    }).addTo(mapa);
    // Encuadre en el área urbana: Sumapaz (rural) ocupa casi la mitad del Distrito
    // y deja las localidades urbanas diminutas; sigue visible al alejar el mapa.
    const urbanas = capaLocalidades.getLayers().filter(l => l.feature.properties.zona !== "Rural");
    mapa.fitBounds(L.featureGroup(urbanas.length ? urbanas : capaLocalidades.getLayers()).getBounds(), { padding: [10, 10] });
    setTimeout(() => mapa.invalidateSize(), 300); setTimeout(() => mapa.invalidateSize(), 800); setTimeout(() => mapa.invalidateSize(), 1500);
    agregarLeyenda();
}

function estiloLocalidad(f) {
    const nom = f.properties.nombre;
    const d = datosLocalidades[nom] || {};
    const n = datosNegligencia.find(x => x.localidad === nom) || {};
    let valor = 0;
    if (capaActiva === "homicidios")  valor = n.homicidios_total || 0;
    else if (capaActiva === "feminicidio") valor = n.feminicidios_forenses || 0;
    else if (capaActiva === "sin-info")    valor = n.pct_sin_clasificacion || 0;
    else if (capaActiva === "via-formal")  valor = d.casos_por_via_formal ?? null;
    return { fillColor: colorPorValor(valor, capaActiva), weight: 1.5, opacity: 1, color: "#333", fillOpacity: 0.75 };
}

const COLOR_NO_CALCULABLE = "#bdbdbd";

function colorPorValor(v, tipo) {
    if (v == null) return COLOR_NO_CALCULABLE;   // p. ej. desierto institucional sin puntos de atención
    const escalas = {
        "homicidios":  [[0,"#f3e5f5"],[10,"#e1bee7"],[30,"#ce93d8"],[60,"#ab47bc"],[100,"#8e24aa"],[150,"#6a1b9a"]],
        "feminicidio": [[0,"#fce4ec"],[2,"#f48fb1"],[5,"#f06292"],[8,"#e91e63"],[12,"#c2185b"],[15,"#880e4f"]],
        "sin-info":    [[0,"#e8f5e9"],[30,"#a5d6a7"],[50,"#66bb6a"],[65,"#ffa726"],[80,"#ef5350"],[95,"#b71c1c"]],
        "via-formal":  [[0,"#e3f2fd"],[10,"#90caf9"],[20,"#42a5f5"],[30,"#1e88e5"],[45,"#1565c0"],[55,"#0d47a1"]]
    };
    const escala = escalas[tipo] || escalas["homicidios"];
    let color = escala[0][1];
    for (const [umbral, c] of escala) { if (v >= umbral) color = c; }
    return color;
}

function agregarLeyenda() {
    if (mapa.leyenda) mapa.removeControl(mapa.leyenda);
    const leyenda = L.control({ position: "bottomright" });
    leyenda.onAdd = () => {
        const div = L.DomUtil.create("div", "leyenda");
        const labels = {
            "homicidios":  ["Homicidios 2015–2024", [[0,"0"],[10,"1–10"],[30,"11–30"],[60,"31–60"],[100,"61–100"],[150,"100+"]]],
            "feminicidio": ["Feminicidios forenses 2018–2024", [[0,"0"],[2,"1–2"],[5,"3–5"],[8,"6–8"],[12,"9–12"],[15,"12+"]]],
            "sin-info":    ["% Sin clasificación",   [[0,"0%"],[30,"30%"],[50,"50%"],[65,"65%"],[80,"80%"],[95,"95%"]]],
            "via-formal":  ["Desierto institucional", [[0,"0"],[10,"1–10"],[20,"11–20"],[30,"21–30"],[45,"31–45"],[55,"45+"],[null,"No calculable (sin puntos de atención)"]]]
        };
        const [titulo, escala] = labels[capaActiva];
        div.innerHTML = `<strong>${titulo}</strong><br>`;
        escala.forEach(([v, l]) => {
            div.innerHTML += `<span class="leyenda-color" style="background:${colorPorValor(v, capaActiva)};"></span>${l}<br>`;
        });
        return div;
    };
    leyenda.addTo(mapa);
    mapa.leyenda = leyenda;
}

function cambiarCapa(nueva, btn) {
    capaActiva = nueva;
    document.querySelectorAll(".btn-capa").forEach(b => b.classList.remove("activo"));
    btn.classList.add("activo");
    if (capaLocalidades) capaLocalidades.setStyle(estiloLocalidad);
    agregarLeyenda();
}

// ── INSTITUCIONES ─────────────────────────────────────────

async function cargarInstituciones() {
    const tipos = ["COMISARIA_FAMILIA", "CASA_JUSTICIA", "CASA_IGUALDAD", "CAI"];
    for (const tipo of tipos) {
        const geojson = await obtenerDatos(`/instituciones?tipo=${tipo}`);
        capasInst[tipo] = L.geoJSON(geojson, {
            pointToLayer: (f, ll) => L.circleMarker(ll, {
                radius: tipo === "CAI" ? 4 : 6,
                fillColor: COLORES_INST[tipo], color: "#fff",
                weight: 1, opacity: 1, fillOpacity: 0.9
            }),
            onEachFeature: (f, layer) => {
                const p = f.properties;
                layer.bindPopup(`<strong>${p.nombre || tipo}</strong><br><em>${p.localidad}</em><br>${p.direccion || ""}`);
            }
        });
    }
    capasInst["COMISARIA_FAMILIA"].addTo(mapa);
    capasInst["CASA_JUSTICIA"].addTo(mapa);
    capasInst["CASA_IGUALDAD"].addTo(mapa);
}

// ── GRÁFICAS ──────────────────────────────────────────────

function dibujarChartZonas(datosApi) {
    const datos = datosApi
        .map(d => ({ ...d, total_casos: Number(d.total_casos) || 0, num_localidades: Number(d.num_localidades) || 0 }))
        .sort((a, b) => b.total_casos - a.total_casos);
    const total = datos.reduce((s, d) => s + d.total_casos, 0);
    if (total === 0) return;
    const pct = n => fmtPct(n / total * 100);

    new Chart(document.getElementById("chart-zonas").getContext("2d"), {
        type: "doughnut",
        data: {
            labels: datos.map(d => d.zona),
            datasets: [{
                data: datos.map(d => d.total_casos),
                backgroundColor: datos.map(d => COLORES_ZONA[d.zona] || "#9e9e9e"),
                borderWidth: 3,
                borderColor: "#fff",
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "64%",
            layout: { padding: 8 },
            plugins: {
                legend: { display: false },   // la leyenda va en la tabla de la derecha
                tooltip: {
                    callbacks: {
                        label: ctx => ` Zona ${ctx.label}: ${fmtNum(ctx.parsed)} ${plural(ctx.parsed)} (${pct(ctx.parsed)})`
                    }
                }
            }
        }
    });

    document.getElementById("dona-total").textContent = fmtNum(total);

    // Tabla por zona: barra proporcional + casos, % y promedio por localidad
    const detalle = document.getElementById("dona-detalle");
    const max = datos[0].total_casos;
    detalle.innerHTML = `
        <div class="zona-fila encabezado"><span>Zona</span><span>Participación</span><span class="zona-cifras">Casos · prom./localidad</span></div>` +
        datos.map(d => {
            const prom = d.num_localidades ? d.total_casos / d.num_localidades : 0;
            const tasa = tasaAnual(d);
            return `
            <div class="zona-fila">
                <span class="zona-nombre"><span class="zona-badge" style="background:${COLORES_ZONA[d.zona]};"></span>${d.zona}</span>
                <span class="zona-barra" title="${pct(d.total_casos)}"><span style="width:${d.total_casos / max * 100}%;background:${COLORES_ZONA[d.zona]};"></span></span>
                <span class="zona-cifras"><strong>${fmtNum(d.total_casos)}</strong> · ${pct(d.total_casos)}
                    <small>${fmtNum(prom, 1)} por localidad (${d.num_localidades} ${d.num_localidades === 1 ? "localidad" : "localidades"})</small>${tasa != null ? `<small>tasa anual: ${fmtNum(tasa, 1)} por 100.000 mujeres</small>` : ""}</span>
            </div>`;
        }).join("");

    // Lectura automática a partir de los datos
    const [mayor] = datos;
    const promedios = datos.filter(d => d.num_localidades).map(d => ({ ...d, prom: d.total_casos / d.num_localidades }));
    const otrasUrbanas = promedios.filter(d => d.zona !== mayor.zona && d.zona !== "Rural");
    const promOtras = otrasUrbanas.reduce((s, d) => s + d.total_casos, 0) /
                      Math.max(1, otrasUrbanas.reduce((s, d) => s + d.num_localidades, 0));
    const promMayor = mayor.total_casos / mayor.num_localidades;
    document.getElementById("dona-lectura").innerHTML =
        `<strong style="color:${COLORES_ZONA[mayor.zona]};">Zona ${mayor.zona}</strong> concentra el ${pct(mayor.total_casos)} de los casos (conteo absoluto). ` +
        `Cada una de sus localidades registra en promedio ${fmtNum(promMayor, 1)} homicidios de mujeres, ` +
        `${fmtNum(promMayor / promOtras, 1)} veces más que una localidad de las demás zonas urbanas (${fmtNum(promOtras, 1)}). ` +
        lecturaTasas(datos) +
        `La <strong style="color:${COLORES_ZONA.Rural};">Zona Rural</strong> (Sumapaz) tiene 1 caso en 10 años y muy poca población: su tasa no es comparable.`;
}

// Tasa anual promedio 2015–2024 por 100.000 mujeres (población OMEG 2025)
function tasaAnual(d) {
    const pob = Number(d.poblacion_fem);
    return pob > 0 ? Number(d.total_casos) / 10 / pob * 100000 : null;
}

function lecturaTasas(datos) {
    const urb = datos.filter(d => d.zona !== "Rural" && tasaAnual(d) != null)
                     .sort((a, b) => tasaAnual(b) - tasaAnual(a));
    if (urb.length < 2) return "";
    return `En proporción a la población (tasa anual por 100.000 mujeres): ` +
        urb.map(d => `${d.zona} ${fmtNum(tasaAnual(d), 1)}`).join(", ") + ". ";
}

// ── FORMATO (es-CO) ───────────────────────────────────────
function fmtNum(n, dec = 0) {
    return Number(n).toLocaleString("es-CO", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function fmtPct(p) {
    return (p > 0 && p < 0.1 ? "<0,1" : fmtNum(p, 1)) + " %";
}
function plural(n) { return n === 1 ? "caso" : "casos"; }

function dibujarChartSerie(datos) {
    const anos  = [...new Set(datos.map(d => d.anio))].sort();
    const zonas = [...new Set(datos.map(d => d.zona))];
    const datasets = zonas.map(z => ({
        label: z,
        data: anos.map(a => {
            const r = datos.find(d => d.anio === a && d.zona === z);
            return r ? r.casos : 0;
        }),
        borderColor: COLORES_ZONA[z],
        backgroundColor: COLORES_ZONA[z] + "22",
        tension: 0.3,
        fill: true,
        pointRadius: 4,
        pointHoverRadius: 7
    }));
    new Chart(document.getElementById("chart-serie").getContext("2d"), {
        type: "line",
        data: { labels: anos, datasets },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "top" },
                tooltip: {
                    mode: "index",
                    intersect: false,
                    callbacks: {
                        title: ctx => `Año ${ctx[0].label}`,
                        afterBody: ctx => {
                            const total = ctx.reduce((s, c) => s + c.parsed.y, 0);
                            return [`—`, `Total Bogotá: ${total} casos`];
                        }
                    }
                }
            },
            scales: { y: { beginAtZero: true, title: { display: true, text: "Homicidios de mujeres" } } },
            interaction: { mode: "index", intersect: false }
        }
    });
}

function dibujarChartIndicador(datos) {
    const top10 = datos
        .filter(d => d.casos_por_via_formal != null)
        .sort((a, b) => b.casos_por_via_formal - a.casos_por_via_formal)
        .slice(0, 10);

    // Resaltar peor y mejor
    const peor  = top10[0];
    const colores = top10.map((d, i) => {
        if (i === 0) return "#c62828";  // peor: rojo oscuro
        return COLORES_ZONA[d.zona] || "#888";
    });

    new Chart(document.getElementById("chart-indicador").getContext("2d"), {
        type: "bar",
        data: {
            labels: top10.map(d => d.localidad),
            datasets: [{
                label: "Homicidios por punto de atención",
                data: top10.map(d => d.casos_por_via_formal),
                backgroundColor: colores,
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${fmtNum(ctx.parsed.x, 1)} homicidios por punto de atención · Zona ${top10[ctx.dataIndex].zona}`
                    }
                }
            },
            scales: {
                x: { title: { display: true, text: "Homicidios por comisaría o casa de justicia (2015–2024)" } }
            }
        }
    });

    // Texto destacado debajo del Top 10
    const highlight = document.getElementById("top10-highlight");
    if (highlight && top10.length > 0) {
        const mejor = [...datos.filter(d => d.casos_por_via_formal != null && d.zona !== "Rural")]
            .sort((a, b) => a.casos_por_via_formal - b.casos_por_via_formal)[0];
        highlight.innerHTML =
            `<strong style="color:#c62828;">⬆ Mayor carga:</strong> ${peor.localidad} con ${fmtNum(peor.casos_por_via_formal, 1)} homicidios por punto de atención (${peor.zona}). ` +
            `<strong style="color:#2e7d32;">⬇ Menor carga (zona urbana):</strong> ${mejor.localidad} con ${fmtNum(mejor.casos_por_via_formal, 1)} (${mejor.zona}). ` +
            sinPuntos(datos);
    }
}

function sinPuntos(datos) {
    const sin = datos.filter(d => d.casos_por_via_formal == null).map(d => d.localidad);
    return sin.length ? `<strong>${sin.join(", ")}</strong>: sin comisarías ni casas de justicia dentro de su límite; el índice no se puede calcular (división por cero).` : "";
}

// ── BUSCADOR DE INSTITUCIONES ─────────────────────────────

function poblarSelectLocalidades() {
    const sel = document.getElementById("select-localidad");
    const localidades = [...new Set(datosIndicadores.map(d => d.localidad))].sort();
    localidades.forEach(loc => {
        const opt = document.createElement("option");
        opt.value = loc;
        opt.textContent = loc;
        sel.appendChild(opt);
    });
}

document.addEventListener("change", e => {
    if (e.target.id !== "select-localidad") return;
    const loc = e.target.value;
    const contenedor = document.getElementById("resultado-instituciones");
    if (!loc) { contenedor.innerHTML = ""; return; }

    // Instituciones que llevan el nombre de la localidad pero están ubicadas en otra
    // (p. ej. la Comisaría de Familia La Candelaria funciona en Santa Fe).
    const sinTilde = t => (t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
    const externas = Object.entries(todosInstsData)
        .filter(([otra]) => otra !== loc)
        .flatMap(([otra, lista]) => lista
            .filter(i => i.tipo !== "CAI" && sinTilde(i.nombre).includes(sinTilde(loc)))
            .map(i => ({ ...i, direccion: `${i.direccion || ""} · ubicada en ${otra}` })));
    const insts = [...(todosInstsData[loc] || []), ...externas];
    if (insts.length === 0) {
        contenedor.innerHTML = `<p style="color:rgba(255,255,255,0.6);font-size:0.8rem;text-align:center;">No hay instituciones registradas para ${loc}</p>`;
        return;
    }

    const colores = { COMISARIA_FAMILIA: "#d32f2f", CASA_JUSTICIA: "#f57c00", CASA_IGUALDAD: "#0288d1", CAI: "#546e7a" };
    const nombres = { COMISARIA_FAMILIA: "Comisaría de Familia", CASA_JUSTICIA: "Casa de Justicia", CASA_IGUALDAD: "Casa de Igualdad", CAI: "CAI Policía" };

    contenedor.innerHTML = insts.map(i => `
        <div class="inst-resultado">
            <span class="tipo-badge" style="background:${colores[i.tipo] || '#888'};color:white;">
                ${nombres[i.tipo] || i.tipo}
            </span><br>
            <strong style="color:white;">${i.nombre || '—'}</strong><br>
            <small style="color:rgba(255,255,255,0.7);">${i.direccion || 'Dirección no disponible'}</small>
        </div>
    `).join("");
});

// ── EVENTOS FILTROS MAPA ──────────────────────────────────

function configurarEventos() {
    ["comisarias","casas-justicia","casas-igualdad","cai"].forEach((id, i) => {
        const tipos = ["COMISARIA_FAMILIA","CASA_JUSTICIA","CASA_IGUALDAD","CAI"];
        document.getElementById(`show-${id}`)?.addEventListener("change", e => {
            const capa = capasInst[tipos[i]];
            if (!capa) return;
            e.target.checked ? capa.addTo(mapa) : mapa.removeLayer(capa);
        });
    });
}

// Forzar redibujado del mapa al hacer scroll
const mapaEl = document.getElementById('mapa');
if (mapaEl) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => { if (e.isIntersecting && mapa) mapa.invalidateSize(); });
    });
    observer.observe(mapaEl);
}
