let mapaSupervisores = null;

let capaEscuelas = null;

let markersEscuelas = [];


/* =========================================================
INICIALIZAR
========================================================= */

function inicializarMapaSupervisores() {

    mapaSupervisores = L.map(
        "mapaSupervisores"
    ).setView(
        [-27.45, -59.0],
        8
    );


    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,

            attribution:
                "&copy; OpenStreetMap contributors"
        }
    ).addTo(
        mapaSupervisores
    );


    capaEscuelas =
        L.layerGroup().addTo(
            mapaSupervisores
        );

}


/* =========================================================
   LIMPIAR
========================================================= */

function limpiarMapaSupervisores() {

    if (!capaEscuelas)
        return;

    capaEscuelas.clearLayers();

    markersEscuelas = [];

}


/* =========================================================
   CARGAR MAPA
========================================================= */

async function cargarMapaSupervisores(
    supervisorId = null
) {

    limpiarMapaSupervisores();


    const params =
        new URLSearchParams();


    if (supervisorId) {

        params.append(
            "supervisor_id",
            supervisorId
        );

    }


    const region =
        document.getElementById(
            "filtroRegion"
        )?.value;


    const nivel =
        document.getElementById(
            "filtroNivel"
        )?.value;


    const situacion =
        document.getElementById(
            "filtroSituacion"
        )?.value;


    const q =
        document.getElementById(
            "filtroBusqueda"
        )?.value;


    if (region) {

        params.append(
            "region",
            region
        );

    }


    if (nivel) {

        params.append(
            "nivel",
            nivel
        );

    }


    if (situacion) {

        params.append(
            "situacion",
            situacion
        );

    }


    if (q) {

        params.append(
            "q",
            q
        );

    }


    const response =
        await fetch(
            `/supreg/api/mapa/supervisores/?${params}`,
            {
                headers: {
                    "X-Requested-With":
                        "XMLHttpRequest"
                }
            }
        );


    if (!response.ok) {

        console.error(
            "Error cargando mapa",
            response.status
        );

        return;

    }


    const data =
        await response.json();


    if (!data.ok) {

        console.error(
            data.error
        );

        return;

    }


    dibujarEscuelasSupervisores(
        data.escuelas
    );

}


/* =========================================================
   DIBUJAR ESCUELAS
========================================================= */

function dibujarEscuelasSupervisores(
    escuelas
) {

    const bounds = [];


    escuelas.forEach(
        escuela => {

            if (
                escuela.latitud === null ||
                escuela.longitud === null
            ) {

                return;

            }


            const marker =
                L.marker([
                    escuela.latitud,
                    escuela.longitud
                ]);


            let supervisoresHtml = "";


            if (
                escuela.supervisores &&
                escuela.supervisores.length
            ) {

                supervisoresHtml = `

                    <hr>

                    <strong>
                        Supervisores
                    </strong>

                    <ul class="mb-0">

                `;


                escuela.supervisores.forEach(
                    supervisor => {

                        supervisoresHtml += `

                            <li>

                                <strong>
                                    ${escapeHtml(
                                        supervisor.nombre
                                    )}
                                </strong>

                                <br>

                                CUIL:
                                ${escapeHtml(
                                    supervisor.cuil
                                )}

                                <br>

                                Regional:
                                ${escapeHtml(
                                    supervisor.region
                                )}

                            </li>

                        `;

                    }
                );


                supervisoresHtml += `
                    </ul>
                `;

            }


            let ofertasHtml = "";


            if (
                escuela.ofertas &&
                escuela.ofertas.length
            ) {

                ofertasHtml = `

                    <hr>

                    <strong>
                        Ofertas asignadas
                    </strong>

                    <ul class="mb-0">

                `;


                escuela.ofertas.forEach(
                    oferta => {

                        ofertasHtml += `

                            <li>

                                ${escapeHtml(
                                    oferta.oferta
                                )}

                                ${
                                    oferta.acronimo
                                    ? `(${escapeHtml(
                                        oferta.acronimo
                                    )})`
                                    : ""
                                }

                            </li>

                        `;

                    }
                );


                ofertasHtml += `
                    </ul>
                `;

            }


            marker.bindPopup(`

                <div
                    style="
                        min-width:300px;
                        max-width:400px;
                    "
                >

                    <h6>

                        <strong>
                            ${escapeHtml(
                                escuela.escuela
                            )}
                        </strong>

                    </h6>

                    <div>

                        <strong>
                            CUEANEXO:
                        </strong>

                        ${escapeHtml(
                            escuela.cueanexo
                        )}

                    </div>

                    ${
                        escuela.regiones &&
                        escuela.regiones.length
                        ? `

                            <div>

                                <strong>
                                    Regional:
                                </strong>

                                ${escapeHtml(
                                    escuela.regiones.join(
                                        ", "
                                    )
                                )}

                            </div>

                          `
                        : ""
                    }

                    ${ofertasHtml}

                    ${supervisoresHtml}

                </div>

            `);


            marker.addTo(
                capaEscuelas
            );


            markersEscuelas.push(
                marker
            );


            bounds.push([
                escuela.latitud,
                escuela.longitud
            ]);

        }
    );


    if (bounds.length) {

        mapaSupervisores.fitBounds(
            bounds,
            {
                padding: [
                    40,
                    40
                ]
            }
        );

    }

}


/* =========================================================
   VER SUPERVISOR
========================================================= */

function mostrarCoberturaSupervisor(
    supervisorId
) {

    cargarMapaSupervisores(
        supervisorId
    );

}


/* =========================================================
   VER TODO
========================================================= */

function mostrarCoberturaGeneral() {

    cargarMapaSupervisores();

}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)

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