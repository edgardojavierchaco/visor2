document.addEventListener("DOMContentLoaded", function () {

    //--------------------------------------------------------
    // VARIABLES
    //--------------------------------------------------------

    let escuelas = [];

    const contador = document.getElementById("contadorEscuelas");

    //--------------------------------------------------------
    // MAPA
    //--------------------------------------------------------

    const mapa = L.map("mapa");

    L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        {
            attribution:
                "&copy; OpenStreetMap contributors &copy; CARTO",
            subdomains: "abcd",
            maxZoom: 20,
        }
    ).addTo(mapa);

    //--------------------------------------------------------
    // CLUSTER
    //--------------------------------------------------------

    const cluster = L.markerClusterGroup();

    mapa.addLayer(cluster);

    //--------------------------------------------------------
    // COLORES
    //--------------------------------------------------------

    function obtenerColor(escuela) {

        if (Number(escuela.hallazgos_criticos) > 0)
            return "#dc3545";

        if (Number(escuela.intervenciones_pendientes) > 0)
            return "#fd7e14";

        if (Number(escuela.cantidad_hallazgos) > 0)
            return "#ffc107";

        return "#198754";

    }

    //--------------------------------------------------------
    // ICONO
    //--------------------------------------------------------

    function crearIcono(color) {

        return L.divIcon({

            className: "",

            html: `
                <div style="
                    width:18px;
                    height:18px;
                    border-radius:50%;
                    background:${color};
                    border:2px solid white;
                    box-shadow:0 0 6px rgba(0,0,0,.4);
                ">
                </div>
            `

        });

    }

    //--------------------------------------------------------
    // CARGAR MARCADORES
    //--------------------------------------------------------

    function cargarMarcadores(lista) {

        cluster.clearLayers();

        if (contador)
            contador.innerHTML = lista.length;

        const bounds = [];

        lista.forEach(function (e) {

            if (!e.lat || !e.long)
                return;

            const lat = parseFloat(e.lat);
            const lng = parseFloat(e.long);

            if (isNaN(lat) || isNaN(lng))
                return;

            bounds.push([lat, lng]);

            const marker = L.marker(

                [lat, lng],

                {
                    icon: crearIcono(
                        obtenerColor(e)
                    )
                }

            );

            marker.bindPopup(`

                <div style="min-width:260px;">

                    <h6 class="mb-2">
                        ${e.nom_est}
                    </h6>

                    <table class="table table-sm table-borderless">

                        <tr>
                            <th>CUE</th>
                            <td>${e.cueanexo}</td>
                        </tr>

                        <tr>
                            <th>Localidad</th>
                            <td>${e.localidad ?? ""}</td>
                        </tr>

                        <tr>
                            <th>Región</th>
                            <td>${e.region_loc ?? ""}</td>
                        </tr>

                        <tr>
                            <th>Departamento</th>
                            <td>${e.departamento ?? ""}</td>
                        </tr>

                        <tr>
                            <th>Hallazgos</th>
                            <td>${e.cantidad_hallazgos}</td>
                        </tr>

                        <tr>
                            <th>Críticos</th>
                            <td>${e.hallazgos_criticos}</td>
                        </tr>

                        <tr>
                            <th>Intervenciones</th>
                            <td>${e.intervenciones_pendientes}</td>
                        </tr>

                    </table>

                    <a
                        class="btn btn-primary btn-sm w-100"
                        href="/sirtee/relevamientos/${e.relevamiento_id}/">

                        Abrir relevamiento

                    </a>

                </div>

            `);

            cluster.addLayer(marker);

        });

        if (bounds.length > 0) {

            mapa.fitBounds(bounds, {

                padding: [40, 40]

            });

        }

    }

    //--------------------------------------------------------
    // CARGA AJAX
    //--------------------------------------------------------

    function cargarDesdeServidor() {

        const params = new URLSearchParams();

        const region =
            document.getElementById("filtroRegion")?.value;

        const departamento =
            document.getElementById("filtroDepartamento")?.value;

        const criticidad =
            document.getElementById("filtroCriticidad")?.value;

        const estado =
            document.getElementById("filtroEstado")?.value;

        if (region)
            params.append("region", region);

        if (departamento)
            params.append("departamento", departamento);

        if (criticidad)
            params.append("criticidad", criticidad);

        if (estado)
            params.append("estado", estado);

        fetch(`/sirtee/api/mapa/?${params.toString()}`)

            .then(function (response) {

                if (!response.ok)
                    throw new Error("Error al cargar el mapa");

                return response.json();

            })

            .then(function (data) {

                escuelas = data;

                cargarMarcadores(escuelas);

            })

            .catch(function (error) {

                console.error(error);

            });

    }

    //--------------------------------------------------------
    // EVENTOS
    //--------------------------------------------------------

    [

        "filtroRegion",

        "filtroDepartamento",

        "filtroCriticidad",

        "filtroEstado"

    ].forEach(function (id) {

        const control = document.getElementById(id);

        if (control) {

            control.addEventListener(

                "change",

                cargarDesdeServidor

            );

        }

    });

    //--------------------------------------------------------
    // INICIO
    //--------------------------------------------------------

    cargarDesdeServidor();

});