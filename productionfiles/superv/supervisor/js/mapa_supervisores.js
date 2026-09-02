let mapaSupervisores = null;
let capaEscuelas = null;

function inicializarMapaSupervisores() {
    const el = document.getElementById("mapaSupervisores");
    if (!el || typeof L === "undefined") return;

    if (mapaSupervisores) {
        mapaSupervisores.invalidateSize();
        return;
    }

    mapaSupervisores = L.map("mapaSupervisores").setView([-27.45, -59.0], 8);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(mapaSupervisores);

    capaEscuelas = L.layerGroup().addTo(mapaSupervisores);
}

function limpiarMapaSupervisores() {
    if (capaEscuelas) capaEscuelas.clearLayers();
}

function parametrosMapa() {
    const params = new URLSearchParams();
    const ids = ["filtroRegion", "filtroNivel", "filtroSituacion"];
    ids.forEach(id => {
        const value = document.getElementById(id)?.value;
        if (value) params.append(id.replace("filtro", "").toLowerCase(), value);
    });
    const q = document.getElementById("filtroBusqueda")?.value?.trim();
    if (q) params.append("q", q);
    return params;
}

async function cargarMapaSupervisores(supervisorId = null) {
    inicializarMapaSupervisores();
    if (!mapaSupervisores) return;
    limpiarMapaSupervisores();

    const params = parametrosMapa();
    if (supervisorId) params.set("supervisor_id", supervisorId);

    const response = await fetch(`/supreg/api/mapa/supervisores/?${params.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
        mostrarEstadoMapa(data.error || `Error ${response.status}`);
        return;
    }

    actualizarKPIs(data.estadisticas, data.modo, data.supervisor);
    dibujarEscuelasSupervisores(data.escuelas || []);
}

function actualizarKPIs(e, modo, supervisor) {
    document.getElementById("kpiSupervisores").textContent = e.supervisores ?? 0;
    document.getElementById("kpiRegionales").textContent = e.regionales ?? 0;
    document.getElementById("kpiEscuelas").textContent = e.escuelas ?? 0;
    document.getElementById("kpiGeo").textContent = e.geolocalizadas ?? 0;
    document.getElementById("kpiSinGeo").textContent = e.sin_geolocalizar ?? 0;
    document.getElementById("tituloMapa").textContent = modo === "supervisor" && supervisor
        ? `Cobertura: ${supervisor.nombre}`
        : "Cobertura territorial de supervisores";
}

function mostrarEstadoMapa(texto) {
    const estado = document.getElementById("estadoMapa");
    if (estado) estado.textContent = texto;
}

function dibujarEscuelasSupervisores(escuelas) {
    const bounds = [];
    let visibles = 0;

    escuelas.forEach(escuela => {
        if (escuela.latitud == null || escuela.longitud == null) return;
        visibles++;

        const marker = L.marker([escuela.latitud, escuela.longitud]);
        let supervisoresHtml = "";
        if (escuela.supervisores?.length) {
            supervisoresHtml = `<hr><strong>Supervisores</strong><ul class="mb-0">${
                escuela.supervisores.map(s => `<li><strong>${escapeHtml(s.nombre)}</strong><br>CUIL: ${escapeHtml(s.cuil)}<br>Regional: ${escapeHtml(s.region)}</li>`).join("")
            }</ul>`;
        }
        const ofertas = escuela.ofertas?.length
            ? `<hr><strong>Ofertas asignadas</strong><ul class="mb-0">${escuela.ofertas.map(o => `<li>${escapeHtml(o)}</li>`).join("")}</ul>`
            : "";

        marker.bindPopup(`<div style="min-width:300px;max-width:420px">
            <h6><strong>${escapeHtml(escuela.escuela)}</strong></h6>
            <div><strong>CUEANEXO:</strong> ${escapeHtml(escuela.cueanexo)}</div>
            <div><strong>Localidad:</strong> ${escapeHtml(escuela.localidad)}</div>
            <div><strong>Departamento:</strong> ${escapeHtml(escuela.departamento)}</div>
            <div><strong>Región:</strong> ${escapeHtml(escuela.region_loc)}</div>
            ${ofertas}${supervisoresHtml}
        </div>`);
        marker.addTo(capaEscuelas);
        bounds.push([escuela.latitud, escuela.longitud]);
    });

    document.getElementById("estadoMapa").textContent = `${visibles} establecimientos geolocalizados en el mapa`;
    if (bounds.length) mapaSupervisores.fitBounds(bounds, { padding: [30, 30] });
    else mapaSupervisores.setView([-27.45, -59.0], 8);
}

async function mostrarCoberturaSupervisor(supervisorId) {
    await cargarMapaSupervisores(supervisorId);
}

async function mostrarCoberturaGeneral() {
    await cargarMapaSupervisores();
}

async function mostrarMapaSupervisorPorCuil() {
    const cuil = document.getElementById("cuilInput")?.value?.trim();
    if (!cuil) {
        mostrarEstadoMapa("Ingrese un CUIL para localizar al supervisor.");
        return;
    }
    const response = await fetch(`/supreg/api/supervisores/?q=${encodeURIComponent(cuil)}`);
    const data = await response.json();
    if (!data.exists || !data.supervisor) {
        mostrarEstadoMapa(data.error || "Supervisor no encontrado o sin permisos.");
        return;
    }
    await cargarMapaSupervisores(data.supervisor.id);
}

function escapeHtml(value) {
    if (value == null) return "";
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
    inicializarMapaSupervisores();
    ["filtroRegion", "filtroNivel", "filtroSituacion"].forEach(id => {
        document.getElementById(id)?.addEventListener("change", () => mostrarCoberturaGeneral());
    });
    document.getElementById("filtroBusqueda")?.addEventListener("change", () => mostrarCoberturaGeneral());
});
