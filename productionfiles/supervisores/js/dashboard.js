// ===============================
// CONFIG
// ===============================
const API = {
    search: "/supreg/api/supervisores/",
    create: "/supreg/api/supervisor/create/",
    update: "/supreg/api/supervisor/update/",
    toggle: "/supreg/api/supervisor/toggle/",

    situacion_add: "/supreg/api/expediente/situacion/add/",
    situacion_delete: "/supreg/api/expediente/situacion/delete/",

    regional_add: "/supreg/api/expediente/regional/add/",
    regional_delete: "/supreg/api/expediente/regional/delete/",

    nivel_add: "/supreg/api/expediente/nivel/add/",
    nivel_delete: "/supreg/api/expediente/nivel/delete/",

    oferta_add: "/supreg/api/expediente/oferta/add/",
    oferta_delete: "/supreg/api/expediente/oferta/delete/",

    regiones_permitidas: "/supreg/api/regiones-permitidas/",

    catalogo_situaciones: "/supreg/api/catalogos/situaciones/",

    catalogo_niveles: "/supreg/api/catalogos/niveles/",

    catalogo_ofertas: "/supreg/api/ofertas/buscar/",

    buscar_cue: "/supreg/api/buscar-cue/",

    situacion_update: "/supreg/api/expediente/situacion/",

    regional_update: "/supreg/api/expediente/regional/",

    nivel_update: "/supreg/api/expediente/nivel/",

    oferta_update: "/supreg/api/expediente/oferta/",

    listado_supervisores: "/supreg/api/supervisores/listado/",
};

// ===============================
// STATE
// ===============================
let CURRENT_SUPERVISOR = null;

// ===============================
// HELPERS
// ===============================
function csrf() {

    const token =
        document.querySelector(
            '[name=csrfmiddlewaretoken]'
        )?.value;

    console.log("CSRF:", token);

    return token;
}

function msgSuccess(texto) {
    Swal.fire({
        icon: "success",
        title: "Correcto",
        text: texto
    });
}

function msgError(texto) {
    Swal.fire({
        icon: "error",
        title: "Error",
        text: texto
    });
}

function msgWarning(texto) {
    Swal.fire({
        icon: "warning",
        title: "Atención",
        text: texto
    });
}

async function confirmar(texto) {

    const r = await Swal.fire({
        icon: "warning",
        title: "Confirmar",
        text: texto,
        showCancelButton: true,
        confirmButtonText: "Sí",
        cancelButtonText: "Cancelar"
    });

    return r.isConfirmed;
}


async function post(url, data) {
    const form = new FormData();

    Object.entries(data).forEach(([k, v]) => {
        form.append(k, v);
    });

    const res = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrf() },
        body: form
    });

    if (!res.ok) {

        const texto = await res.text();

        console.error(texto);

        msgError(
            `Error ${res.status}`
        );

        throw new Error(texto);
    }

    return await res.json();
}

async function get(url) {
    const res = await fetch(url);
    return await res.json();
}

// ===============================
// SEARCH
// ===============================
async function buscarSupervisor() {

    const input = document.getElementById("cuilInput");

    if (!input) {
        console.error("No existe cuilInput en el DOM");
        return;
    }

    const cuil = input.value.trim();
    if (!cuil) return;

    const res = await get(`${API.search}?q=${cuil}`);

    const resultado = document.getElementById("resultadoSupervisor");

    if (res.exists) {

        CURRENT_SUPERVISOR = res.supervisor;

        await cargarRegionesPermitidas();
        await cargarSituaciones();
        await cargarNiveles();
        await cargarRegionesPermitidas();

        cargarExpediente(
            res.supervisor.id
        );

        resultado.innerHTML = `
            <div class="alert alert-success">

                <b>Supervisor existente</b>

                <hr>
                <b>CUIL:</b> ${res.supervisor.cuil}<br>
                <b>Apellido:</b> ${res.supervisor.apellido}<br>
                <b>Nombres:</b> ${res.supervisor.nombres}<br>
                <b>Email:</b> ${res.supervisor.email || "-"}<br>
                <b>Teléfono:</b> ${res.supervisor.telefono || "-"}

            </div>
        `;

        document.getElementById("createBox").classList.add("d-none");
        document.getElementById("expediente").classList.remove("d-none");

        cargarExpediente(res.supervisor.id);
    
    }
    else if (res.usuario) {
        CURRENT_SUPERVISOR = null;

        document
            .getElementById("apellido")
            .value = res.usuario.apellido;

        document
            .getElementById("nombres")
            .value = res.usuario.nombres;

        resultado.innerHTML = `
            <div class="alert alert-warning">

                <b>El usuario existe pero NO es supervisor.</b>

                <hr>

                <b>CUIL:</b> ${res.usuario.cuil}<br>
                <b>Apellido:</b> ${res.usuario.apellido}<br>
                <b>Nombres:</b> ${res.usuario.nombres}

                <br><br>

                Debe registrarlo como supervisor.

            </div>
        `;

        document
            .getElementById("createBox")
            .classList.remove("d-none");

        document
            .getElementById("expediente")
            .classList.add("d-none");

    }
    else {

        CURRENT_SUPERVISOR = null;

        document
            .getElementById("apellido")
            .value = "";

        document
            .getElementById("nombres")
            .value = "";

        document
            .getElementById("email")
            .value = "";

        document
            .getElementById("telefono")
            .value = "";

        resultado.innerHTML = `
            <div class="alert alert-danger">
                <b>No existe como usuario.</b>

                <hr>

                Debe comunicarse con un administrador a:

                <br><br>

                <b>estadisticaseducativaschaco@gmail.com</b>
            </div>
        `;

        // NO permite crear supervisor
        document.getElementById("createBox").classList.add("d-none");
        document.getElementById("expediente").classList.add("d-none");
    }
}

// ===============================
// LISTADO DE MIS SUPERVISORES
// ===============================
async function listarMisSupervisores() {

    try {

        const res =
            await get(
                API.listado_supervisores
            );

        const tbody =
            document.getElementById(
                "tablaSupervisores"
            );

        tbody.innerHTML = "";

        if (!res.results.length) {

            tbody.innerHTML = `
                <tr>
                    <td colspan="6"
                        class="text-center">

                        No hay supervisores asignados

                    </td>
                </tr>
            `;
        }

        res.results.forEach(s => {

            tbody.innerHTML += `
                <tr>

                    <td>${s.cuil}</td>

                    <td>${s.apellido}</td>

                    <td>${s.nombres}</td>

                    <td>${s.email || "-"}</td>

                    <td>${s.telefono || "-"}</td>

                    <td>
                        ${s.regionales.join(", ")}
                    </td>

                </tr>
            `;
        });

        const modal =
            new bootstrap.Modal(
                document.getElementById(
                    "modalListadoSupervisores"
                )
            );

        modal.show();

    } catch(error) {

        console.error(error);

        msgError(
            "No se pudo cargar el listado"
        );
    }
}

// ===============================
// CREATE
// ===============================
async function crearSupervisor() {

    const cuil = document.getElementById("cuilInput").value;

    const res = await post(API.create, {
        cuil,
        apellido: document.getElementById("apellido").value,
        nombres: document.getElementById("nombres").value,
        email: document.getElementById("email").value,
        telefono: document.getElementById("telefono").value
    });

    if (res.id) {
        msgSuccess("Supervisor creado correctamente");
        buscarSupervisor();
    }
}

// ===============================
// BUSCAR CUEANEXO PARA OFERTA
// ===============================
async function buscarCue() {

    const sr_id =
        document.getElementById(
            "ofertaRegionalSelect"
        ).value;

    const cue =
        document.getElementById(
            "cueanexo"
        ).value;

    if (cue.length < 9)
        return;

    const datos =
        await get(
            `${API.buscar_cue}?sr_id=${sr_id}&cueanexo=${cue}`
        );

    const select =
        document.getElementById(
            "ofertaSelect"
        );

    const nomEst =
        document.getElementById(
            "nomEst"
        );

    select.innerHTML = "";

    if (!datos.ok) {

        nomEst.value = "";
        select.innerHTML = "";

        msgWarning(datos.mensaje);

        return;
    }

    nomEst.value = datos.nom_est;

    datos.ofertas.forEach(o => {

        select.innerHTML += `
            <option
                value="${o.oferta}"
                data-acronimo="${o.acronimo}">
                ${o.oferta}
            </option>
        `;
    });
}


// ===============================
// EXPEDIENTE
// ===============================
async function cargarExpediente(id) {

    try {

        const res =
            await get(`/supreg/api/expediente/${id}/`);

        console.log(res);

        renderSituaciones(
            res.situaciones || []
        );

        renderRegionales(
            res.regionales || []
        );

        cargarSelectRegionales();

        renderNiveles(
            res.niveles || []
        );

        renderOfertas(
            res.ofertas || []
        );

    } catch(error) {

        console.error(
            "Error expediente:",
            error
        );

    }
}

// ===============================
// SITUACIONES
// ===============================
function renderSituaciones(list) {

    const el = document.getElementById("sitListado");
    el.innerHTML = "";

    list.forEach(s => {
        el.innerHTML += `
            <div class="border p-2 mb-2">
                <b>${s.situacion_revista__nombre}</b>
                (${s.fecha_desde} - ${s.fecha_hasta || "Actual"})
                <button class="btn btn-sm btn-danger"
                    onclick="eliminarSituacion(${s.id})">X</button>
                
                <button
                    class="btn btn-warning btn-sm"
                    onclick="abrirEditarSituacion(${s.id})">

                    Editar

                </button>
            </div>
        `;
    });
}


//================================
// CARGAR SITUACION DE REVISTA
//================================
async function cargarSituaciones() {

    const datos =
        await get(
            API.catalogo_situaciones
        );

    const select =
        document.getElementById(
            "situacionSelect"
        );

    if (!select) return;

    select.innerHTML = "";

    datos.forEach(s => {

        select.innerHTML += `
            <option value="${s.id}">
                ${s.nombre}
            </option>
        `;
    });
}

//================================
// AGREGAR SITUACION DE REVISTA
//================================
async function agregarSituacion() {

    await post(
        API.situacion_add,
        {
            supervisor_id:
                CURRENT_SUPERVISOR.id,

            situacion_id:
                document.getElementById(
                    "situacionSelect"
                ).value,

            fecha_desde:
                document.getElementById(
                    "fechaDesde"
                ).value || null,

            fecha_hasta:
                document.getElementById(
                    "fechaHasta"
                ).value || null
        }
    );

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}

// ===============================
// ELIMINAR SITUACIONES
// ===============================
async function eliminarSituacion(id) {
    if (!await confirmar("¿Desea eliminar esta Situación de Revista?"))
        return;

    await post(
        `${API.situacion_delete}${id}/`,
        {}
    );

    msgSuccess("Situación de Revista eliminada");

    cargarExpediente(CURRENT_SUPERVISOR.id);
}


// ===============================
// EDITAR SITUACIONES
// ===============================
async function abrirEditarSituacion(id) {

    const expediente = await get(`/supreg/api/expediente/${CURRENT_SUPERVISOR.id}/`);

    const item = expediente.situaciones.find(s => s.id === id);

    document.getElementById("editSituacionId").value = id;

    document.getElementById("editFechaDesde").value = item.fecha_desde || "";
    document.getElementById("editFechaHasta").value = item.fecha_hasta || "";

    // cargar opciones
    const select = document.getElementById("editSituacionSelect");
    select.innerHTML = "";

    const catalogo = await get(API.catalogo_situaciones);

    catalogo.forEach(s => {
        select.innerHTML += `<option value="${s.id}">${s.nombre}</option>`;
    });

    select.value = item.situacion_revista;

    const modal = new bootstrap.Modal(
        document.getElementById("modalEditarSituacion")
    );

    modal.show();
}


async function guardarEdicionSituacion() {

    const id = document.getElementById("editSituacionId").value;

    await post(`${API.situacion_update}${id}/update/`, {
        situacion_id: document.getElementById("editSituacionSelect").value,
        fecha_desde: document.getElementById("editFechaDesde").value || null,
        fecha_hasta: document.getElementById("editFechaHasta").value || null
    });

    msgSuccess("Situación actualizada");

    bootstrap.Modal.getInstance(
        document.getElementById("modalEditarSituacion")
    ).hide();

    cargarExpediente(CURRENT_SUPERVISOR.id);
}

// ===============================
// REGIONALES
// ===============================
function renderRegionales(list) {

    const el =
        document.getElementById("regListado");

    el.innerHTML = "";

    if (!list.length) {

        el.innerHTML = `
            <div class="alert alert-warning">
                Sin regionales asignadas
            </div>
        `;

        return;
    }

    list.forEach(r => {

        el.innerHTML += `
            <div class="border p-2 mb-2"
                class="border p-2 mb-2"
                data-regional-id="${r.id}"
                data-regional-nombre="${r.region}">

                <strong>${r.region}</strong>

                <br>

                <button
                    class="btn btn-sm btn-danger"
                    onclick="eliminarRegional(${r.id})">

                    Eliminar

                </button>

            </div>
        `;
    });

    cargarSelectRegionales();
}

// ===============================
// CARGAR SELECT REGIONALES
// ===============================
function cargarSelectRegionales() {

    const nivelSelect =
        document.getElementById(
            "nivelRegionalSelect"
        );

    const ofertaSelect =
        document.getElementById(
            "ofertaRegionalSelect"
        );

    if (!nivelSelect || !ofertaSelect)
        return;

    nivelSelect.innerHTML = "";
    ofertaSelect.innerHTML = "";

    document
        .querySelectorAll(
            "#regListado [data-regional-id]"
        )
        .forEach(item => {

            const id =
                item.dataset.regionalId;

            const nombre =
                item.dataset.regionalNombre;

            nivelSelect.innerHTML += `
                <option value="${id}">
                    ${nombre}
                </option>
            `;

            ofertaSelect.innerHTML += `
                <option value="${id}">
                    ${nombre}
                </option>
            `;
        });
}

// ===============================
// CARGAR REGIONALES PERMITIDAS
// ===============================
async function cargarRegionesPermitidas() {

    const regiones =
        await get(API.regiones_permitidas);

    const select =
        document.getElementById("regionSelect");

    if (!select) return;

    select.innerHTML = "";

    regiones.forEach(r => {

        select.innerHTML += `
            <option value="${r.id}">
                ${r.nombre}
            </option>
        `;
    });
}

//================================
// AGREGAR REGIONAL
//================================
async function agregarRegional() {

    const region_id =
        document.getElementById(
            "regionSelect"
        ).value;

    const res = await post(
        API.regional_add,
        {
            supervisor_id: CURRENT_SUPERVISOR.id,
            region_id: region_id
        }
    );

    console.log(res);

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}


// ===============================
// ELIMINAR REGIONALES 
// ===============================
async function eliminarRegional(id) {
    if (!await confirmar("¿Desea eliminar esta Regional?"))
        return;

    await post(
        `${API.regional_delete}${id}/`,
        {}
    );

    msgSuccess("Regional eliminada");

    cargarExpediente(CURRENT_SUPERVISOR.id);
}

// ===============================
// NIVELES
// ===============================
function renderNiveles(list) {

    const el =
        document.getElementById("nivListado");

    el.innerHTML = "";

    if (!list.length) {

        el.innerHTML = `
            <div class="alert alert-warning">
                Sin niveles cargados
            </div>
        `;

        return;
    }

    list.forEach(n => {

        el.innerHTML += `
            <div class="border p-2 mb-2">

                <b>${n.nivel}</b>

                <br>

                Regional:
                ${n.regional}

                <button
                    class="btn btn-danger btn-sm mt-2"
                    onclick="eliminarNivel(${n.id})">

                    Eliminar

                </button>
                <button
                    class="btn btn-warning btn-sm"
                    onclick="editarNivel(${n.id})">

                    Editar

                </button>

            </div>
        `;
    });
}


//================================
// CARGAR NIVEL
//================================
async function cargarNiveles() {

    const datos =
        await get(
            API.catalogo_niveles
        );

    const select =
        document.getElementById(
            "nivelSelect"
        );

    if (!select) return;

    select.innerHTML = "";

    datos.forEach(n => {

        select.innerHTML += `
            <option value="${n.id}">
                ${n.nombre}
            </option>
        `;
    });
}


//================================
// AGREGAR NIVEL
//================================
async function agregarNivel() {

    const supervisor_regional_id =
        document.getElementById(
            "nivelRegionalSelect"
        ).value;
    
    if (!supervisor_regional_id) {
        msgWarning("Debe seleccionar una regional");
        return;
    }

    await post(
        API.nivel_add,
        {
            sr_id:
                supervisor_regional_id,

            nivel_id:
                document.getElementById(
                    "nivelSelect"
                ).value
        }
    );

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}


//================================
// ELIMINAR NIVEL
//================================
async function eliminarNivel(id) {

    if (!await confirmar("¿Desea eliminar este Nivel?"))
        return;

    await post(
        API.nivel_delete,
        {
            id: id
        }
    );

    msgSuccess("Nivel eliminado");

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}


// ===============================
// EDITAR NIVEL
// ===============================
async function editarNivel(id) {

    const nivel =
        document.getElementById(
            "nivelSelect"
        ).value;

    await post(
        `${API.nivel_update}${id}/update/`,
        {
            nivel_id: nivel
        }
    );

    Swal.fire(
        "Actualizado",
        "Nivel actualizado",
        "success"
    );

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}

// ===============================
// OFERTAS
// ===============================
function renderOfertas(list) {

    const el =
        document.getElementById("ofeListado");

    el.innerHTML = "";

    if (!list.length) {

        el.innerHTML = `
            <div class="alert alert-warning">
                Sin ofertas cargadas
            </div>
        `;

        return;
    }

    list.forEach(o => {

        el.innerHTML += `
            <div class="border p-2 mb-2">

                <b>${o.establecimiento}</b>

                <br>

                ${o.oferta}

                <br>

                Regional:
                ${o.regional}

                <button
                    class="btn btn-danger btn-sm"
                    onclick="eliminarOferta(${o.id})">
                    X
                </button>
                <button
                    class="btn btn-warning btn-sm"
                    onclick="editarOferta(${o.id})">

                    Editar

                </button>

            </div>
        `;
    });
}


//================================
// AGREGAR OFERTA
//================================
async function agregarOferta() {

    const supervisor_regional_id =
        document.getElementById(
            "ofertaRegionalSelect"
        ).value;

    const ofertaSelect =
        document.getElementById(
            "ofertaSelect"
        );

    const option =
        ofertaSelect.options[
            ofertaSelect.selectedIndex
        ];
    
    if (!supervisor_regional_id) {
        msgWarning("Debe seleccionar una regional");
        return;
    }

    await post(
        API.oferta_add,
        {
            sr_id:
                supervisor_regional_id,

            cueanexo:
                document.getElementById(
                    "cueanexo"
                ).value,

            nom_est:
                document.getElementById(
                    "nomEst"
                ).value,

            oferta:
                ofertaSelect.value
        }
    );

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}

//================================
// ELIMINAR OFERTA
//================================
async function eliminarOferta(id) {

    if (!await confirmar("¿Desea eliminar esta oferta?"))
        return;

    await post(
        `${API.oferta_delete}${id}/`,
        {}
    );

    msgSuccess("Oferta eliminada");

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}


//================================
// EDITAR OFERTA
//================================
async function editarOferta(id) {

    const ofertaSelect =
        document.getElementById(
            "ofertaSelect"
        );

    await post(
        `${API.oferta_update}${id}/update/`,
        {
            cueanexo:
                document.getElementById(
                    "cueanexo"
                ).value,

            nom_est:
                document.getElementById(
                    "nomEst"
                ).value,

            oferta:
                ofertaSelect.value,

            acronimo:
                ofertaSelect.options[
                    ofertaSelect.selectedIndex
                ].dataset.acronimo
        }
    );

    Swal.fire(
        "Actualizado",
        "Oferta actualizada",
        "success"
    );

    cargarExpediente(
        CURRENT_SUPERVISOR.id
    );
}

document.addEventListener(
    "DOMContentLoaded",
    () => {

        // Tabs
        document
            .querySelectorAll(
                '[data-bs-toggle="tab"]'
            )
            .forEach(btn => {

                btn.addEventListener(
                    "click",
                    function() {

                        document
                            .querySelectorAll(
                                ".tab-pane"
                            )
                            .forEach(p =>
                                p.classList.remove(
                                    "show",
                                    "active"
                                )
                            );

                        document
                            .querySelectorAll(
                                ".nav-link"
                            )
                            .forEach(t =>
                                t.classList.remove(
                                    "active"
                                )
                            );

                        this.classList.add(
                            "active"
                        );

                        const target =
                            this.dataset.bsTarget;

                        document
                            .querySelector(
                                target
                            )
                            .classList.add(
                                "show",
                                "active"
                            );
                    }
                );
            });

        // Filtro listado supervisores
        const filtro =
            document.getElementById(
                "filtroSupervisores"
            );

        if (filtro) {

            filtro.addEventListener(
                "keyup",
                function() {

                    const texto =
                        this.value
                            .toLowerCase();

                    document
                        .querySelectorAll(
                            "#tablaSupervisores tr"
                        )
                        .forEach(tr => {

                            tr.style.display =
                                tr.innerText
                                    .toLowerCase()
                                    .includes(texto)
                                ? ""
                                : "none";

                        });
                }
            );
        }
    }
);