"use strict";

let mapaSupervisores = null;
let capaEscuelas = null;
let capaRegionales = null;
let controlLeyenda = null;
let mapaInicializado = false;
let cargandoMapa = false;

const MAPA_SUPERVISORES_URL = "/supreg/api/mapa/supervisores/";
const CENTRO_CHACO = [-27.45, -59.0];

const PALETA_CATEGORIAS = [
    "#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#dc3545",
    "#20c997", "#6610f2", "#0dcaf0", "#ffc107", "#6c757d",
    "#8b5cf6", "#ef4444", "#10b981", "#f59e0b", "#3b82f6"
];

const mapaColoresCategorias = new Map();

function obtenerColorCategoria(clave) {
    const key = (clave || "Sin clasificación").trim() || "Sin clasificación";
    if (!mapaColoresCategorias.has(key)) {
        const index = mapaColoresCategorias.size % PALETA_CATEGORIAS.length;
        mapaColoresCategorias.set(key, PALETA_CATEGORIAS[index]);
    }
    return mapaColoresCategorias.get(key);
}

function obtenerCategoriasEscuela(escuela) {
    const categorias = [];
    const vistos = new Set();

    (escuela?.ofertas || []).forEach(item => {
        const oferta = item?.oferta || "Sin oferta";
        const niveles = Array.isArray(item?.niveles) && item.niveles.length
            ? item.niveles
            : (item?.nivel ? [item.nivel] : []);

        niveles.forEach(nivel => {
            const clave = `${oferta} · ${nivel}`;
            if (!vistos.has(clave)) {
                vistos.add(clave);
                categorias.push(clave);
            }
        });
    });

    if (!categorias.length) {
        (escuela?.ofertas || []).forEach(item => {
            const oferta = item?.oferta || "Sin oferta";
            const clave = `${oferta}`;
            if (!vistos.has(clave)) {
                vistos.add(clave);
                categorias.push(clave);
            }
        });
    }

    if (!categorias.length) {
        categorias.push("Sin clasificación");
    }

    return categorias;
}

function construirFondoMarcador(colores) {
    if (!colores || colores.length === 0) return "#0d6efd";
    if (colores.length === 1) return colores[0];

    const paso = 100 / colores.length;
    const segmentos = colores.map((color, idx) => {
        const ini = (idx * paso).toFixed(2);
        const fin = ((idx + 1) * paso).toFixed(2);
        return `${color} ${ini}% ${fin}%`;
    });
    return `conic-gradient(${segmentos.join(", ")})`;
}

function crearIconoEscuela(escuela) {
    const categorias = obtenerCategoriasEscuela(escuela);
    const colores = categorias.map(obtenerColorCategoria);
    const fondo = construirFondoMarcador(colores);

    return L.divIcon({
        className: "marcador-escuela",
        html: `
            <div class="marcador-escuela-pin" style="background:${fondo};">
                <span></span>
            </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 30],
        popupAnchor: [0, -30],
    });
}

function inicializarMapaSupervisores() {
    const contenedor = document.getElementById("mapaSupervisores");
    if (!contenedor) return;

    if (mapaInicializado) {
        recalcularTamanoMapa();
        return;
    }

    if (typeof L === "undefined") {
        actualizarEstadoMapa("Error: Leaflet no pudo inicializarse.", true);
        return;
    }

    mapaSupervisores = L.map("mapaSupervisores", {
        zoomControl: true,
        preferCanvas: true,
    }).setView(CENTRO_CHACO, 7);

    mapaSupervisores.createPane("paneRegionales");
    mapaSupervisores.getPane("paneRegionales").style.zIndex = 410;
    mapaSupervisores.getPane("paneRegionales").style.pointerEvents = "auto";

    L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=cb1_2s9h_1_bd646db33e2c8813a2d9b537",
        {
            subdomains: "abcd",
            maxZoom: 20,
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
        }
    ).addTo(mapaSupervisores);

    capaRegionales = L.geoJSON(null, {
        pane: "paneRegionales",
        style: feature => ({
            color: feature?.properties?.strokeColor || feature?.properties?.fillColor || "#495057",
            weight: 2,
            opacity: 0.85,
            fillColor: feature?.properties?.fillColor || "#6c757d",
            fillOpacity: 0.18,
        }),
        onEachFeature: (feature, layer) => {
            const props = feature?.properties || {};
            const titulo = props.titulo || props.region_pad || "Regional";
            layer.bindTooltip(titulo, { sticky: true });
            layer.bindPopup(`
                <div class="popup-supervisor">
                    <div class="popup-supervisor-titulo">${escapeHtml(titulo)}</div>
                    ${props.region_pad ? `<div class="popup-supervisor-dato"><strong>Código:</strong> ${escapeHtml(props.region_pad)}</div>` : ""}
                    ${props.objectid ? `<div class="popup-supervisor-dato"><strong>ObjectID:</strong> ${escapeHtml(props.objectid)}</div>` : ""}
                </div>
            `);
        }
    }).addTo(mapaSupervisores);

    capaEscuelas = L.layerGroup().addTo(mapaSupervisores);
    mapaInicializado = true;
    recalcularTamanoMapa();
    window.addEventListener("resize", recalcularTamanoMapa);
}

function recalcularTamanoMapa() {
    if (!mapaSupervisores) return;
    [100, 400, 800].forEach(delay => {
        setTimeout(() => mapaSupervisores.invalidateSize({ animate: false }), delay);
    });
}

function limpiarMapa() {
    capaEscuelas?.clearLayers();
    capaRegionales?.clearLayers();
    if (controlLeyenda) {
        mapaSupervisores.removeControl(controlLeyenda);
        controlLeyenda = null;
    }
}

function obtenerFiltrosMapa() {
    return {
        region: document.getElementById("filtroRegion")?.value || "",
        nivel: document.getElementById("filtroNivel")?.value || "",
        situacion: document.getElementById("filtroSituacion")?.value || "",
        q: document.getElementById("filtroBusqueda")?.value?.trim() || "",
    };
}

function construirParametrosMapa(supervisorId = null) {
    const params = new URLSearchParams();
    const filtros = obtenerFiltrosMapa();
    if (supervisorId) params.set("supervisor_id", supervisorId);
    if (filtros.region) params.set("region", filtros.region);
    if (filtros.nivel) params.set("nivel", filtros.nivel);
    if (filtros.situacion) params.set("situacion", filtros.situacion);
    if (filtros.q) params.set("q", filtros.q);
    return params;
}

function mostrarCoberturaGeneral() {
    cargarMapaSupervisores(null);
}

async function cargarMapaSupervisores(supervisorId = null) {
    inicializarMapaSupervisores();
    if (!mapaSupervisores || cargandoMapa) return;

    cargandoMapa = true;
    limpiarMapa();
    actualizarEstadoMapa("Cargando cobertura territorial...");

    try {
        const params = construirParametrosMapa(supervisorId);
        const query = params.toString();
        const url = query ? `${MAPA_SUPERVISORES_URL}?${query}` : MAPA_SUPERVISORES_URL;
        const response = await fetch(url, {
            method: "GET",
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
        });

        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data?.error || `Error HTTP ${response.status}`);
        }

        dibujarRegionales(data.regionales || null);
        dibujarEscuelas(data.escuelas || []);
        actualizarKpis(data.estadisticas || {});
        actualizarTituloMapa(data);
        actualizarLeyendaMapa(data.regionales || null, data.escuelas || []);

        if (!Array.isArray(data.escuelas) || data.escuelas.length === 0) {
            actualizarEstadoMapa("No se encontraron establecimientos.");
        } else {
            actualizarEstadoMapa(`${data.escuelas.length} establecimiento(s) cargado(s).`);
        }
    } catch (error) {
        actualizarEstadoMapa(error.message || "Error cargando el mapa.", true);
        actualizarKpis({ total: 0, geolocalizadas: 0, sin_geolocalizar: 0, supervisores: 0, regiones: 0 });
    } finally {
        cargandoMapa = false;
    }
}

function dibujarRegionales(geojson) {
    if (!capaRegionales) return;
    capaRegionales.clearLayers();
    if (!geojson || !Array.isArray(geojson.features) || geojson.features.length === 0) return;
    capaRegionales.addData(geojson);
}

function dibujarEscuelas(escuelas) {
    if (!Array.isArray(escuelas) || !capaEscuelas) return;
    capaEscuelas.clearLayers();

    const bounds = [];
    escuelas.forEach(escuela => {
        if (escuela.latitud == null || escuela.longitud == null) return;
        const lat = Number(escuela.latitud);
        const lon = Number(escuela.longitud);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
        if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return;

        const marker = L.marker([lat, lon], {
            icon: crearIconoEscuela(escuela),
            title: escuela.escuela || "Establecimiento",
            riseOnHover: true,
            riseOffset: 1000,
        });

        marker.bindPopup(construirPopup(escuela), { minWidth: 300, maxWidth: 450 });
        marker.addTo(capaEscuelas);
        bounds.push([lat, lon]);
    });

    setTimeout(() => {
        mapaSupervisores.invalidateSize({ animate: false });
        if (bounds.length === 1) {
            mapaSupervisores.setView(bounds[0], 15, { animate: false });
        } else if (bounds.length > 1) {
            mapaSupervisores.fitBounds(bounds, { padding: [40, 40], maxZoom: 15, animate: false });
        } else if (capaRegionales && capaRegionales.getLayers().length > 0) {
            mapaSupervisores.fitBounds(capaRegionales.getBounds(), { padding: [20, 20], maxZoom: 9, animate: false });
        } else {
            mapaSupervisores.setView(CENTRO_CHACO, 7, { animate: false });
        }
    }, 250);
}

function construirPopup(escuela) {
    return `
        <div class="popup-supervisor">
            <div class="popup-supervisor-titulo">${escapeHtml(escuela.escuela)}</div>
            <div class="popup-supervisor-dato"><strong>CUEANEXO:</strong> ${escapeHtml(escuela.cueanexo)}</div>
            ${escuela.region_loc ? `<div class="popup-supervisor-dato"><strong>Región:</strong> ${escapeHtml(escuela.region_loc)}</div>` : ""}
            ${escuela.localidad ? `<div class="popup-supervisor-dato"><strong>Localidad:</strong> ${escapeHtml(escuela.localidad)}</div>` : ""}
            ${escuela.departamento ? `<div class="popup-supervisor-dato"><strong>Departamento:</strong> ${escapeHtml(escuela.departamento)}</div>` : ""}
            ${construirRegiones(escuela.regiones)}
            ${construirSupervisores(escuela.supervisores)}
            ${construirOfertas(escuela.ofertas)}
        </div>
    `;
}

function construirRegiones(regiones) {
    if (!Array.isArray(regiones) || regiones.length === 0) return "";
    const nombres = regiones.map(item => escapeHtml(item?.nombre || "")).filter(Boolean);
    if (!nombres.length) return "";
    return `<div class="popup-supervisor-seccion"><strong>Regional asignada:</strong><div>${nombres.join(", ")}</div></div>`;
}

function construirSupervisores(supervisores) {
    if (!Array.isArray(supervisores) || supervisores.length === 0) return "";
    let html = `<div class="popup-supervisor-seccion"><strong>Supervisor${supervisores.length > 1 ? "es" : ""}:</strong>`;
    supervisores.forEach(supervisor => {
        html += `
            <div class="popup-supervisor-persona">
                <div><strong>${escapeHtml(supervisor.nombre || "Sin nombre")}</strong></div>
                ${supervisor.cuil ? `<div>CUIL: ${escapeHtml(supervisor.cuil)}</div>` : ""}
                ${supervisor.telefono ? `<div>Teléfono: ${escapeHtml(supervisor.telefono)}</div>` : ""}
                ${supervisor.email ? `<div>Email: <a href="mailto:${escapeHtml(supervisor.email)}">${escapeHtml(supervisor.email)}</a></div>` : ""}
            </div>
        `;
    });
    html += `</div>`;
    return html;
}

function construirOfertas(ofertas) {
    if (!Array.isArray(ofertas) || ofertas.length === 0) return "";
    let html = `
        <div class="popup-supervisor-seccion">
            <strong>Oferta${ofertas.length > 1 ? "s" : ""}:</strong>
            <ul style="padding-left:20px;margin-top:5px;margin-bottom:0;">
    `;

    ofertas.forEach(oferta => {
        const niveles = Array.isArray(oferta.niveles) && oferta.niveles.length
            ? oferta.niveles
            : (oferta.nivel ? [oferta.nivel] : []);
        const colores = niveles.length
            ? niveles.map(nivel => obtenerColorCategoria(`${oferta.oferta || "Sin oferta"} · ${nivel}`))
            : [obtenerColorCategoria(oferta.oferta || "Sin oferta")];
        const muestraColores = colores.map(color =>
            `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:3px;"></span>`
        ).join("");

        html += `
            <li>
                ${muestraColores}
                ${escapeHtml(oferta.oferta || "")}
                ${niveles.length ? `<span class="text-muted">(${escapeHtml(niveles.join(" / "))})</span>` : ""}
            </li>
        `;
    });

    html += `</ul></div>`;
    return html;
}

function actualizarLeyendaMapa(geojson, escuelas) {
    if (!mapaSupervisores) return;

    const categorias = new Set();
    (escuelas || []).forEach(escuela => {
        obtenerCategoriasEscuela(escuela).forEach(cat => categorias.add(cat));
    });

    const regiones = [];
    if (geojson?.features?.length) {
        geojson.features.forEach(feature => {
            regiones.push({
                nombre: feature?.properties?.titulo || feature?.properties?.region_pad || "Regional",
                color: feature?.properties?.fillColor || "#6c757d",
            });
        });
    }

    controlLeyenda = L.control({ position: "bottomright" });

    controlLeyenda.onAdd = function () {
        const contenedor = L.DomUtil.create(
            "div",
            "mapa-leyenda-control leaflet-bar"
        );

        const boton = L.DomUtil.create(
            "button",
            "mapa-leyenda-toggle",
            contenedor
        );

        boton.type = "button";
        boton.setAttribute("aria-expanded", "false");
        boton.setAttribute("aria-label", "Mostrar leyenda del mapa");
        boton.innerHTML = `
            <span class="mapa-leyenda-toggle-icon" aria-hidden="true">☰</span>
            <span>Leyenda</span>
            <span class="mapa-leyenda-chevron" aria-hidden="true">⌃</span>
        `;

        const contenido = L.DomUtil.create(
            "div",
            "mapa-leyenda-contenido",
            contenedor
        );

        let html = "";

        if (regiones.length) {
            html += `
                <div class="mapa-leyenda-seccion">
                    <div class="mapa-leyenda-titulo">Regionales</div>
            `;

            regiones.forEach(item => {
                html += `
                    <div class="mapa-leyenda-item">
                        <span
                            class="mapa-leyenda-muestra mapa-leyenda-muestra-region"
                            style="background:${item.color};"
                        ></span>
                        <span>${escapeHtml(item.nombre)}</span>
                    </div>
                `;
            });

            html += `</div>`;
        }

        if (categorias.size) {
            html += `
                <div class="mapa-leyenda-seccion">
                    <div class="mapa-leyenda-titulo">Oferta / nivel</div>
            `;

            Array.from(categorias)
                .sort((a, b) => a.localeCompare(b, "es"))
                .forEach(cat => {
                    const color = obtenerColorCategoria(cat);

                    html += `
                        <div class="mapa-leyenda-item">
                            <span
                                class="mapa-leyenda-muestra mapa-leyenda-muestra-marcador"
                                style="background:${color};"
                            ></span>
                            <span>${escapeHtml(cat)}</span>
                        </div>
                    `;
                });

            html += `</div>`;
        }

        if (!html) {
            html = `
                <div class="mapa-leyenda-vacia">
                    Sin elementos para mostrar.
                </div>
            `;
        }

        contenido.innerHTML = html;

        const alternarLeyenda = event => {
            L.DomEvent.stopPropagation(event);
            L.DomEvent.preventDefault(event);

            const abierta = contenedor.classList.toggle("abierta");

            boton.setAttribute(
                "aria-expanded",
                abierta ? "true" : "false"
            );

            boton.setAttribute(
                "aria-label",
                abierta
                    ? "Ocultar leyenda del mapa"
                    : "Mostrar leyenda del mapa"
            );
        };

        L.DomEvent.on(boton, "click", alternarLeyenda);

        // Evita que al interactuar con la leyenda se arrastre o haga zoom el mapa.
        L.DomEvent.disableClickPropagation(contenedor);
        L.DomEvent.disableScrollPropagation(contenedor);

        return contenedor;
    };

    controlLeyenda.addTo(mapaSupervisores);
}

function actualizarKpis(estadisticas) {
    setTexto("kpiSupervisores", estadisticas.supervisores ?? 0);
    setTexto("kpiRegionales", estadisticas.regiones ?? 0);
    setTexto("kpiEscuelas", estadisticas.total ?? 0);
    setTexto("kpiGeo", estadisticas.geolocalizadas ?? 0);
    setTexto("kpiSinGeo", estadisticas.sin_geolocalizar ?? 0);
}

function actualizarTituloMapa(data) {
    const titulo = document.getElementById("tituloMapa");
    if (!titulo) return;
    titulo.textContent = data.modo === "supervisor"
        ? "Cobertura territorial del supervisor"
        : "Cobertura territorial de supervisores";
}

function actualizarEstadoMapa(mensaje, error = false) {
    const estado = document.getElementById("estadoMapa");
    if (!estado) return;
    estado.textContent = mensaje;
    estado.classList.remove("text-muted", "text-danger", "text-success");
    estado.classList.add(error ? "text-danger" : "text-muted");
}

function mostrarCoberturaSupervisor(supervisorId) {
    if (!supervisorId) return;
    cargarMapaSupervisores(supervisorId);
    document.getElementById("mapaSupervisores")?.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function mostrarMapaSupervisorPorCuil() {
    const valor = document.getElementById("filtroBusqueda")?.value?.trim();
    if (!valor) {
        if (typeof Swal !== "undefined") {
            Swal.fire("Atención", "Ingrese un CUIL, apellido o nombre.", "warning");
        } else {
            alert("Ingrese un CUIL, apellido o nombre.");
        }
        return;
    }
    await cargarMapaSupervisores();
}

function setTexto(id, valor) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(valor);
}

function escapeHtml(valor) {
    if (valor == null) return "";
    return String(valor)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function configurarBuscadorMapa() {
    const input = document.getElementById("filtroBusqueda");
    if (!input) return;
    input.addEventListener("keydown", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            mostrarCoberturaGeneral();
        }
    });
}

function configurarFiltrosMapa() {
    ["filtroRegion", "filtroNivel", "filtroSituacion"].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener("change", () => mostrarCoberturaGeneral());
    });
}

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("mapaSupervisores")) return;
    inicializarMapaSupervisores();
    configurarBuscadorMapa();
    configurarFiltrosMapa();
    setTimeout(() => mostrarCoberturaGeneral(), 300);
});

window.inicializarMapaSupervisores = inicializarMapaSupervisores;
window.cargarMapaSupervisores = cargarMapaSupervisores;
window.mostrarCoberturaGeneral = mostrarCoberturaGeneral;
window.mostrarCoberturaSupervisor = mostrarCoberturaSupervisor;
window.mostrarMapaSupervisorPorCuil = mostrarMapaSupervisorPorCuil;
