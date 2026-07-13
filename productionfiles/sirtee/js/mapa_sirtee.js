document.addEventListener("DOMContentLoaded", function () {

    // ==========================================================
    // VARIABLES GLOBALES
    // ==========================================================

    let escuelas = [];

    const contador = document.getElementById("contadorEscuelas");

    const btnActualizar = document.getElementById("btnActualizar");

    const mapa = L.map("mapa", {
        zoomControl: true,
        preferCanvas: true
    });

    // ==========================================================
    // CAPAS BASE
    // ==========================================================

    const osm = L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        {
            attribution: "&copy; OpenStreetMap &copy; CARTO",
            maxZoom: 12
        }
    );

    osm.addTo(mapa);

    mapa.setView(
        [-27.45, -59.00],
        7
    );

    // ==========================================================
    // CLUSTER
    // ==========================================================

    const cluster = L.markerClusterGroup({

        showCoverageOnHover: false,

        spiderfyOnMaxZoom: true,

        zoomToBoundsOnClick: true,

        removeOutsideVisibleBounds: true

    });

    mapa.addLayer(cluster);

    // ==========================================================
    // COLORES
    // ==========================================================

    function obtenerColor(escuela) {

        if (Number(escuela.hallazgos_criticos) > 0) {
            return "#dc3545";
        }

        if (Number(escuela.intervenciones_pendientes) > 0) {
            return "#fd7e14";
        }

        if (Number(escuela.cantidad_hallazgos) > 0) {
            return "#ffc107";
        }

        return "#198754";

    }

    // ==========================================================
    // ICONO
    // ==========================================================

    function crearIcono(color) {

        return L.divIcon({

            className: "sirtee-marker",

            html: `

                <div
                    style="
                        width:18px;
                        height:18px;
                        border-radius:50%;
                        background:${color};
                        border:3px solid white;
                        box-shadow:0 0 8px rgba(0,0,0,.45);
                    ">
                </div>

            `,

            iconSize: [22,22],

            iconAnchor: [11,11],

            popupAnchor: [0,-10]

        });

    }

    // ==========================================================
    // POPUP
    // ==========================================================

    function popupEscuela(e){

        return `

        <div style="min-width:320px">

            <h5 class="mb-2">

                ${e.nom_est || "Escuela"}

            </h5>

            <table class="table table-sm table-bordered mb-3">

                <tr>

                    <th width="40%">CUEANEXO</th>
                    <td>${e.cueanexo ?? "-"}</td>
                </tr>
                <tr>
                    <th>Localidad</th>
                    <td>${e.localidad ?? "-"}</td>
                </tr>
                <tr>
                    <th>Departamento</th>
                    <td>${e.departamento ?? "-"}</td>
                </tr>
                <tr>
                    <th>Región</th>
                    <td>${e.region_loc ?? "-"}</td>
                </tr>
                <tr>
                    <th>Hallazgos</th>
                    <td>${e.cantidad_hallazgos ?? 0}</td>
                </tr>
                <tr>
                    <th>Críticos</th>
                    <td>${e.hallazgos_criticos ?? 0}</td>
                </tr>
                <tr>
                    <th>Intervenciones</th>
                    <td>${e.intervenciones_pendientes ?? 0}</td>
                </tr>
                <tr>
                    <th>Criticidades</th>
                    <td>${e.criticidades ?? "-"}</td>
                </tr>
                <tr>
                    <th>Estados</th>
                    <td>${e.estados_intervencion ?? "-"}</td>
                </tr>

            </table>
            
            <div class="d-grid">
                <a
                    href="${URL_RELEVAMIENTO}escuela/${e.cueanexo}/"
                    class="btn btn-primary">

                    <i class="bi bi-building"></i>

                    Ver relevamientos de esta escuela

                </a>
            </div>
        </div>

        `;

    }

    // ==========================================================
    // LIMPIAR MAPA
    // ==========================================================

    function limpiarMapa(){

        cluster.clearLayers();

        if(contador){

            contador.textContent = "0";

        }

    }

    // ==========================================================
    // CARGAR MARCADORES
    // ==========================================================

    function cargarMarcadores(lista){

        if(!Array.isArray(lista)){

            console.error(
                "La lista recibida no es un array.",
                lista
            );

            limpiarMapa();

            return;

        }

        limpiarMapa();

        const bounds = [];

        lista.forEach(function(e){

            if(
                e.lat === null ||
                e.long === null ||
                e.lat === "" ||
                e.long === ""
            ){
                return;
            }

            const lat = parseFloat(e.lat);

            const lng = parseFloat(e.long);

            if(
                Number.isNaN(lat) ||
                Number.isNaN(lng)
            ){
                return;
            }

            bounds.push([lat,lng]);

            const marker = L.marker(

                [lat,lng],

                {

                    icon: crearIcono(
                        obtenerColor(e)
                    )

                }

            );

            marker.bindPopup(

                popupEscuela(e),

                {

                    maxWidth: 350

                }

            );

            cluster.addLayer(marker);

        });

        if(contador){

            contador.textContent = cluster.getLayers().length;

        }

        if(bounds.length > 0){

            mapa.fitBounds(

                bounds,

                {

                    padding:[40,40],

                    maxZoom:16

                }

            );

        }

    }

        // ==========================================================
    // OBTENER FILTROS
    // ==========================================================

    function obtenerFiltros() {

        const params = new URLSearchParams();

        const region = document.getElementById("filtroRegion")?.value || "";
        const departamento = document.getElementById("filtroDepartamento")?.value || "";
        const criticidad = document.getElementById("filtroCriticidad")?.value || "";
        const estado = document.getElementById("filtroEstado")?.value || "";

        if (region) {
            params.append("region", region);
        }

        if (departamento) {
            params.append("departamento", departamento);
        }

        if (criticidad) {
            params.append("criticidad", criticidad);
        }

        if (estado) {
            params.append("estado", estado);
        }

        return params;
    }

    // ==========================================================
    // CARGAR DESDE API
    // ==========================================================

    async function cargarDesdeServidor() {

        try {

            const params = obtenerFiltros();

            const response = await fetch(
                `/sirtee/api/mapa/?${params.toString()}`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            if (!response.ok) {

                throw new Error(
                    `HTTP ${response.status}`
                );

            }

            const json = await response.json();

            console.log("Respuesta API:", json);

            if (!json.success) {

                throw new Error(
                    json.error || "Error informado por la API."
                );

            }

            if (!Array.isArray(json.data)) {

                throw new Error(
                    "La propiedad data no contiene un array."
                );

            }

            escuelas = json.data;

            cargarMarcadores(escuelas);

        }

        catch (error) {

            console.error(
                "Error cargando mapa:",
                error
            );

            limpiarMapa();

            alert(
                "No fue posible cargar la información del mapa."
            );

        }

    }

    // ==========================================================
    // ACTUALIZAR
    // ==========================================================

    if (btnActualizar) {

        btnActualizar.addEventListener(
            "click",
            function () {

                cargarDesdeServidor();

            }
        );

    }

    // ==========================================================
    // CAMBIO DE FILTROS
    // ==========================================================

    [
        "filtroRegion",
        "filtroDepartamento",
        "filtroCriticidad",
        "filtroEstado"

    ].forEach(function (id) {

        const control = document.getElementById(id);

        if (!control) {

            return;

        }

        control.addEventListener(

            "change",

            function () {

                cargarDesdeServidor();

            }

        );

    });

    // ==========================================================
    // CARGA INICIAL
    // ==========================================================

    if (

        typeof escuelasIniciales !== "undefined" &&

        Array.isArray(escuelasIniciales)

    ) {

        escuelas = escuelasIniciales;

        cargarMarcadores(
            escuelas
        );

    }

    else {

        cargarDesdeServidor();

    }

});