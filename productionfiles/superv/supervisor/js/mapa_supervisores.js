"use strict";


/* ============================================================
   ESTADO GLOBAL DEL MAPA
============================================================ */

let mapaSupervisores = null;
let capaEscuelas = null;
let mapaInicializado = false;
let cargandoMapa = false;


/* ============================================================
   CONFIGURACIÓN
============================================================ */

const MAPA_SUPERVISORES_URL =
    "/supreg/api/mapa/supervisores/";

const CENTRO_CHACO = [
    -27.45,
    -59.0
];


/* ============================================================
   ICONO PERSONALIZADO DE ESCUELA
============================================================ */

const ICONO_ESCUELA = L.divIcon({
    className: "marcador-escuela",

    html: `
        <div class="marcador-escuela-pin">
            <span></span>
        </div>
    `,

    iconSize: [30, 30],

    iconAnchor: [15, 30],

    popupAnchor: [0, -30]
});


/* ============================================================
   INICIALIZAR MAPA
============================================================ */

function inicializarMapaSupervisores() {

    const contenedor =
        document.getElementById(
            "mapaSupervisores"
        );


    if (!contenedor) {

        console.warn(
            "No existe el contenedor #mapaSupervisores."
        );

        return;
    }


    if (mapaInicializado) {

        recalcularTamanoMapa();

        return;
    }


    if (typeof L === "undefined") {

        console.error(
            "Leaflet no está cargado."
        );

        actualizarEstadoMapa(
            "Error: Leaflet no pudo inicializarse.",
            true
        );

        return;
    }


    mapaSupervisores =
        L.map(
            "mapaSupervisores",
            {
                zoomControl: true,
                preferCanvas: true
            }
        )
        .setView(
            CENTRO_CHACO,
            7
        );


    /* ========================================================
       CAPA BASE CARTO POSITRON

       IMPORTANTE:
       reemplazar TU_API_KEY_CARTO por tu clave real.
    ======================================================== */

    L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=cb1_2s9h_1_bd646db33e2c8813a2d9b537",
        {
            subdomains: "abcd",

            maxZoom: 20,

            attribution:
                '&copy; OpenStreetMap contributors ' +
                '&copy; CARTO'
        }
    ).addTo(
        mapaSupervisores
    );


    /* ========================================================
       CAPA ESCUELAS
    ======================================================== */

    capaEscuelas =
        L.layerGroup()
        .addTo(
            mapaSupervisores
        );


    mapaInicializado = true;


    recalcularTamanoMapa();


    /* ========================================================
       CUANDO CAMBIA EL TAMAÑO DE LA VENTANA
    ======================================================== */

    window.addEventListener(
        "resize",
        () => {

            recalcularTamanoMapa();

        }
    );

}


/* ============================================================
   RECALCULAR TAMAÑO DEL MAPA
============================================================ */

function recalcularTamanoMapa() {

    if (!mapaSupervisores) {
        return;
    }


    /*
     * Se ejecuta varias veces porque los dashboards con sidebar
     * pueden cambiar de ancho después de cargar.
     */

    setTimeout(
        () => {

            mapaSupervisores.invalidateSize({
                animate: false
            });

        },
        100
    );


    setTimeout(
        () => {

            mapaSupervisores.invalidateSize({
                animate: false
            });

        },
        400
    );


    setTimeout(
        () => {

            mapaSupervisores.invalidateSize({
                animate: false
            });

        },
        800
    );

}


/* ============================================================
   LIMPIAR MAPA
============================================================ */

function limpiarMapa() {

    if (capaEscuelas) {

        capaEscuelas.clearLayers();

    }

}


/* ============================================================
   FILTROS DEL DASHBOARD
============================================================ */

function obtenerFiltrosMapa() {

    return {

        region:
            document
                .getElementById(
                    "filtroRegion"
                )
                ?.value || "",

        nivel:
            document
                .getElementById(
                    "filtroNivel"
                )
                ?.value || "",

        situacion:
            document
                .getElementById(
                    "filtroSituacion"
                )
                ?.value || "",

        q:
            document
                .getElementById(
                    "filtroBusqueda"
                )
                ?.value
                ?.trim() || ""

    };

}


/* ============================================================
   CONSTRUIR PARÁMETROS
============================================================ */

function construirParametrosMapa(
    supervisorId = null
) {

    const params =
        new URLSearchParams();


    const filtros =
        obtenerFiltrosMapa();


    if (supervisorId) {

        params.set(
            "supervisor_id",
            supervisorId
        );

    }


    if (filtros.region) {

        params.set(
            "region",
            filtros.region
        );

    }


    if (filtros.nivel) {

        params.set(
            "nivel",
            filtros.nivel
        );

    }


    if (filtros.situacion) {

        params.set(
            "situacion",
            filtros.situacion
        );

    }


    if (filtros.q) {

        params.set(
            "q",
            filtros.q
        );

    }


    return params;

}


/* ============================================================
   COBERTURA GENERAL
============================================================ */

function mostrarCoberturaGeneral() {

    cargarMapaSupervisores(
        null
    );

}


/* ============================================================
   CARGAR MAPA
============================================================ */

async function cargarMapaSupervisores(
    supervisorId = null
) {

    inicializarMapaSupervisores();


    if (!mapaSupervisores) {
        return;
    }


    if (cargandoMapa) {
        return;
    }


    cargandoMapa = true;


    limpiarMapa();


    actualizarEstadoMapa(
        "Cargando cobertura territorial..."
    );


    try {

        const params =
            construirParametrosMapa(
                supervisorId
            );


        const query =
            params.toString();


        const url =
            query
                ? `${MAPA_SUPERVISORES_URL}?${query}`
                : MAPA_SUPERVISORES_URL;


        console.log(
            "Consultando mapa:",
            url
        );


        const response =
            await fetch(
                url,
                {
                    method: "GET",

                    credentials:
                        "same-origin",

                    headers: {

                        "Accept":
                            "application/json",

                        "X-Requested-With":
                            "XMLHttpRequest"

                    }
                }
            );


        let data;


        try {

            data =
                await response.json();

        }
        catch {

            throw new Error(
                "El servidor devolvió una respuesta inválida."
            );

        }


        if (
            !response.ok ||
            !data.ok
        ) {

            throw new Error(
                data?.error ||
                `Error HTTP ${response.status}`
            );

        }


        console.log(
            "Datos mapa:",
            data
        );


        dibujarEscuelas(
            data.escuelas || []
        );


        actualizarKpis(
            data.estadisticas || {}
        );


        actualizarTituloMapa(
            data
        );


        if (
            !Array.isArray(data.escuelas) ||
            data.escuelas.length === 0
        ) {

            actualizarEstadoMapa(
                "No se encontraron establecimientos."
            );

        }
        else {

            actualizarEstadoMapa(
                `${data.escuelas.length} establecimiento(s) cargado(s).`
            );

        }

    }
    catch (error) {

        console.error(
            "Error cargando mapa:",
            error
        );


        actualizarEstadoMapa(
            error.message ||
            "Error cargando el mapa.",
            true
        );


        actualizarKpis({
            total: 0,
            geolocalizadas: 0,
            sin_geolocalizar: 0,
            supervisores: 0,
            regiones: 0
        });

    }
    finally {

        cargandoMapa = false;

    }

}


/* ============================================================
   DIBUJAR ESCUELAS
============================================================ */

function dibujarEscuelas(
    escuelas
) {

    if (!Array.isArray(escuelas)) {

        console.warn(
            "escuelas no es un array:",
            escuelas
        );

        return;
    }


    if (!capaEscuelas) {
        return;
    }


    capaEscuelas.clearLayers();


    const bounds = [];


    let cantidadMarcadores = 0;


    escuelas.forEach(
        escuela => {

            if (
                escuela.latitud === null ||
                escuela.latitud === undefined ||
                escuela.longitud === null ||
                escuela.longitud === undefined
            ) {

                console.warn(
                    "Escuela sin coordenadas:",
                    escuela.cueanexo
                );

                return;
            }


            const lat =
                Number(
                    escuela.latitud
                );


            const lon =
                Number(
                    escuela.longitud
                );


            if (
                !Number.isFinite(lat) ||
                !Number.isFinite(lon)
            ) {

                console.warn(
                    "Coordenadas inválidas:",
                    escuela
                );

                return;
            }


            if (
                lat < -90 ||
                lat > 90 ||
                lon < -180 ||
                lon > 180
            ) {

                console.warn(
                    "Coordenadas fuera de rango:",
                    escuela
                );

                return;
            }


            const marker =
                L.marker(
                    [
                        lat,
                        lon
                    ],
                    {
                        icon:
                            ICONO_ESCUELA,

                        title:
                            escuela.escuela ||
                            "Establecimiento",

                        riseOnHover:
                            true,

                        riseOffset:
                            1000
                    }
                );


            marker.bindPopup(
                construirPopup(
                    escuela
                ),
                {
                    minWidth: 300,
                    maxWidth: 450
                }
            );


            marker.addTo(
                capaEscuelas
            );


            bounds.push([
                lat,
                lon
            ]);


            cantidadMarcadores++;

        }
    );


    console.log(
        "Marcadores dibujados:",
        cantidadMarcadores
    );


    setTimeout(
        () => {

            mapaSupervisores.invalidateSize({
                animate: false
            });


            if (
                bounds.length === 1
            ) {

                mapaSupervisores.setView(
                    bounds[0],
                    15,
                    {
                        animate: false
                    }
                );

            }
            else if (
                bounds.length > 1
            ) {

                mapaSupervisores.fitBounds(
                    bounds,
                    {
                        padding: [
                            40,
                            40
                        ],

                        maxZoom:
                            15,

                        animate:
                            false
                    }
                );

            }
            else {

                mapaSupervisores.setView(
                    CENTRO_CHACO,
                    7,
                    {
                        animate: false
                    }
                );

            }

        },
        250
    );

}


/* ============================================================
   POPUP ESCUELA
============================================================ */

function construirPopup(
    escuela
) {

    return `

        <div class="popup-supervisor">

            <div class="popup-supervisor-titulo">

                ${escapeHtml(
                    escuela.escuela
                )}

            </div>


            <div class="popup-supervisor-dato">

                <strong>CUEANEXO:</strong>

                ${escapeHtml(
                    escuela.cueanexo
                )}

            </div>


            ${
                escuela.region_loc
                    ? `

                        <div class="popup-supervisor-dato">

                            <strong>
                                Región:
                            </strong>

                            ${escapeHtml(
                                escuela.region_loc
                            )}

                        </div>

                      `
                    : ""
            }


            ${
                escuela.localidad
                    ? `

                        <div class="popup-supervisor-dato">

                            <strong>
                                Localidad:
                            </strong>

                            ${escapeHtml(
                                escuela.localidad
                            )}

                        </div>

                      `
                    : ""
            }


            ${
                escuela.departamento
                    ? `

                        <div class="popup-supervisor-dato">

                            <strong>
                                Departamento:
                            </strong>

                            ${escapeHtml(
                                escuela.departamento
                            )}

                        </div>

                      `
                    : ""
            }


            ${construirRegiones(
                escuela.regiones
            )}


            ${construirSupervisores(
                escuela.supervisores
            )}


            ${construirOfertas(
                escuela.ofertas
            )}

        </div>

    `;

}


/* ============================================================
   REGIONES
============================================================ */

function construirRegiones(
    regiones
) {

    if (
        !Array.isArray(regiones) ||
        regiones.length === 0
    ) {

        return "";

    }


    const nombres =
        regiones
            .map(
                item =>
                    escapeHtml(
                        item?.nombre || ""
                    )
            )
            .filter(Boolean);


    if (
        nombres.length === 0
    ) {

        return "";

    }


    return `

        <div class="popup-supervisor-seccion">

            <strong>
                Regional asignada:
            </strong>

            <div>

                ${nombres.join(", ")}

            </div>

        </div>

    `;

}


/* ============================================================
   SUPERVISORES
============================================================ */

function construirSupervisores(
    supervisores
) {

    if (
        !Array.isArray(supervisores) ||
        supervisores.length === 0
    ) {

        return "";

    }


    let html = `

        <div class="popup-supervisor-seccion">

            <strong>

                Supervisor${supervisores.length > 1 ? "es" : ""}:

            </strong>

    `;


    supervisores.forEach(
        supervisor => {

            html += `

                <div class="popup-supervisor-persona">

                    <div>

                        <strong>

                            ${escapeHtml(
                                supervisor.nombre ||
                                "Sin nombre"
                            )}

                        </strong>

                    </div>


                    ${
                        supervisor.cuil
                            ? `

                                <div>
                                    CUIL:
                                    ${escapeHtml(
                                        supervisor.cuil
                                    )}
                                </div>

                              `
                            : ""
                    }


                    ${
                        supervisor.telefono
                            ? `

                                <div>

                                    Teléfono:

                                    ${escapeHtml(
                                        supervisor.telefono
                                    )}

                                </div>

                              `
                            : ""
                    }


                    ${
                        supervisor.email
                            ? `

                                <div>

                                    Email:

                                    <a
                                        href="mailto:${escapeHtml(
                                            supervisor.email
                                        )}"
                                    >

                                        ${escapeHtml(
                                            supervisor.email
                                        )}

                                    </a>

                                </div>

                              `
                            : ""
                    }

                </div>

            `;

        }
    );


    html += `

        </div>

    `;


    return html;

}


/* ============================================================
   OFERTAS
============================================================ */

function construirOfertas(
    ofertas
) {

    if (
        !Array.isArray(ofertas) ||
        ofertas.length === 0
    ) {

        return "";

    }


    let html = `

        <div class="popup-supervisor-seccion">

            <strong>

                Oferta${ofertas.length > 1 ? "s" : ""}:

            </strong>

            <ul
                style="
                    padding-left:20px;
                    margin-top:5px;
                    margin-bottom:0;
                "
            >

    `;


    ofertas.forEach(
        oferta => {

            html += `

                <li>

                    ${escapeHtml(
                        oferta.oferta || ""
                    )}

                    ${
                        oferta.acronimo
                            ? `

                                <span class="text-muted">

                                    (${escapeHtml(
                                        oferta.acronimo
                                    )})

                                </span>

                              `
                            : ""
                    }

                </li>

            `;

        }
    );


    html += `

            </ul>

        </div>

    `;


    return html;

}


/* ============================================================
   KPIs
============================================================ */

function actualizarKpis(
    estadisticas
) {

    setTexto(
        "kpiSupervisores",
        estadisticas.supervisores ?? 0
    );


    setTexto(
        "kpiRegionales",
        estadisticas.regiones ?? 0
    );


    setTexto(
        "kpiEscuelas",
        estadisticas.total ?? 0
    );


    setTexto(
        "kpiGeo",
        estadisticas.geolocalizadas ?? 0
    );


    setTexto(
        "kpiSinGeo",
        estadisticas.sin_geolocalizar ?? 0
    );

}


/* ============================================================
   TÍTULO
============================================================ */

function actualizarTituloMapa(
    data
) {

    const titulo =
        document.getElementById(
            "tituloMapa"
        );


    if (!titulo) {
        return;
    }


    if (
        data.modo === "supervisor"
    ) {

        titulo.textContent =
            "Cobertura territorial del supervisor";

    }
    else {

        titulo.textContent =
            "Cobertura territorial de supervisores";

    }

}


/* ============================================================
   ESTADO MAPA
============================================================ */

function actualizarEstadoMapa(
    mensaje,
    error = false
) {

    const estado =
        document.getElementById(
            "estadoMapa"
        );


    if (!estado) {
        return;
    }


    estado.textContent =
        mensaje;


    estado.classList.remove(
        "text-muted",
        "text-danger",
        "text-success"
    );


    if (error) {

        estado.classList.add(
            "text-danger"
        );

    }
    else {

        estado.classList.add(
            "text-muted"
        );

    }

}


/* ============================================================
   MAPA DE UN SUPERVISOR
============================================================ */

function mostrarCoberturaSupervisor(
    supervisorId
) {

    if (!supervisorId) {
        return;
    }


    cargarMapaSupervisores(
        supervisorId
    );


    document
        .getElementById(
            "mapaSupervisores"
        )
        ?.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

}


/* ============================================================
   FILTRAR POR CUIL / NOMBRE
============================================================ */

async function mostrarMapaSupervisorPorCuil() {

    const input =
        document.getElementById(
            "filtroBusqueda"
        );


    const valor =
        input
            ?.value
            ?.trim();


    if (!valor) {

        if (
            typeof Swal !== "undefined"
        ) {

            Swal.fire(
                "Atención",
                "Ingrese un CUIL, apellido o nombre.",
                "warning"
            );

        }
        else {

            alert(
                "Ingrese un CUIL, apellido o nombre."
            );

        }

        return;

    }


    await cargarMapaSupervisores();

}


/* ============================================================
   SET TEXTO
============================================================ */

function setTexto(
    id,
    valor
) {

    const elemento =
        document.getElementById(
            id
        );


    if (elemento) {

        elemento.textContent =
            String(valor);

    }

}


/* ============================================================
   ESCAPE HTML
============================================================ */

function escapeHtml(
    valor
) {

    if (
        valor === null ||
        valor === undefined
    ) {

        return "";

    }


    return String(valor)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


/* ============================================================
   ENTER BUSCADOR
============================================================ */

function configurarBuscadorMapa() {

    const input =
        document.getElementById(
            "filtroBusqueda"
        );


    if (!input) {
        return;
    }


    input.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Enter"
            ) {

                event.preventDefault();

                mostrarCoberturaGeneral();

            }

        }
    );

}


/* ============================================================
   SELECTS
============================================================ */

function configurarFiltrosMapa() {

    [
        "filtroRegion",
        "filtroNivel",
        "filtroSituacion"
    ]
        .forEach(
            id => {

                const elemento =
                    document.getElementById(
                        id
                    );


                if (!elemento) {
                    return;
                }


                elemento.addEventListener(
                    "change",
                    () => {

                        mostrarCoberturaGeneral();

                    }
                );

            }
        );

}


/* ============================================================
   INICIO
============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const contenedor =
            document.getElementById(
                "mapaSupervisores"
            );


        if (!contenedor) {
            return;
        }


        inicializarMapaSupervisores();

        configurarBuscadorMapa();

        configurarFiltrosMapa();


        /*
         * Esperamos un instante para que el layout principal
         * termine de calcular su ancho.
         */

        setTimeout(
            () => {

                mostrarCoberturaGeneral();

            },
            300
        );

    }
);


/* ============================================================
   FUNCIONES DISPONIBLES GLOBALMENTE
============================================================ */

window.inicializarMapaSupervisores =
    inicializarMapaSupervisores;

window.cargarMapaSupervisores =
    cargarMapaSupervisores;

window.mostrarCoberturaGeneral =
    mostrarCoberturaGeneral;

window.mostrarCoberturaSupervisor =
    mostrarCoberturaSupervisor;

window.mostrarMapaSupervisorPorCuil =
    mostrarMapaSupervisorPorCuil;