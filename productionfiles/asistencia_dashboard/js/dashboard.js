"use strict";

const CFG = window.ASISTENCIA_DASHBOARD;

let chartEvolucion = null;
let chartNivel = null;
let chartRanking = null;

const paginationState = {
    ranking: 1,
    alertas: 1,
    mensual: 1,
    calidad: 1,
    alertasAlumnos: 1,
    secciones: 1
};

const formatter = new Intl.NumberFormat("es-AR");

document.addEventListener("DOMContentLoaded", async function () {
    configurarPeriodoInicial();
    inicializarSelect2();
    configurarEventos();
    configurarPaginacion();

    await cargarFiltros();
    await cargarSemanas(true);
    await actualizarDashboard();
});

function configurarPeriodoInicial() {
    $("#filtroAnio").val(String(CFG.anioActual));
    $("#filtroMes").val(String(CFG.mesActual));
    $("#filtroAnioSemana").val(String(CFG.anioSemanaActual));
    actualizarTituloPeriodo();
}

function actualizarTituloPeriodo() {
    const anio = $("#filtroAnio").val();
    const mes = Number($("#filtroMes").val());

    const nombresMeses = [
        "",
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre"
    ];

    $("#periodoActual").text(
        `${nombresMeses[mes]} ${anio}`
    );

    const semanaTexto = $("#filtroSemana option:selected").text();
    if (semanaTexto) {
        $("#periodoActual").attr(
            "title",
            `Alertas: ${semanaTexto}`
        );
    }
}

function inicializarSelect2() {
    const selects = [
        "#filtroNivel",
        "#filtroAmbito",
        "#filtroRegion",
        "#filtroDepartamento",
        "#filtroLocalidad",
        "#filtroOferta",
        "#filtroSemana"
    ];

    selects.forEach(function (selector) {
        $(selector).select2({
            theme: "bootstrap-5",
            width: "100%",
            allowClear: true,
            placeholder: "Todos"
        });
    });

    $("#filtroCue").select2({
        theme: "bootstrap-5",
        width: "100%",
        allowClear: true,
        placeholder: "Buscar por CUE o establecimiento",
        minimumInputLength: 2,

        ajax: {
            url: CFG.urls.establecimientos,
            dataType: "json",
            delay: 350,

            data: function (params) {
                return {
                    q: params.term || "",
                    anio: $("#filtroAnio").val(),
                    mes: $("#filtroMes").val(),
                    region: $("#filtroRegion").val() || ""
                };
            },

            processResults: function (data) {
                return data;
            }
        }
    });
}

function configurarEventos() {
    // Filtros mensuales generales.
    [
        "#filtroNivel",
        "#filtroAmbito",
        "#filtroDepartamento",
        "#filtroLocalidad",
        "#filtroOferta"
    ].forEach(function (selector) {
        $(selector).on(
            "change",
            async function () {
                await actualizarDashboard();
            }
        );
    });

    // Año/mes: primero actualiza las opciones disponibles y luego el tablero.
    $("#filtroAnio, #filtroMes").on(
        "change",
        async function () {
            actualizarTituloPeriodo();
            await cargarFiltros();
            await actualizarDashboard();
        }
    );

    // Regional: invalida el CUE seleccionado y refresca el tablero.
    $("#filtroRegion").on(
        "change",
        async function () {
            $("#filtroCue")
                .val(null)
                .trigger("change.select2");

            await actualizarDashboard();
        }
    );

    // Seleccionar CUE filtra indicadores mensuales y habilita drill-down semanal.
    $("#filtroCue").on(
        "change",
        async function () {
            await actualizarDashboard();
        }
    );

    // El año/semana de alerta sólo refresca la capa nominal.
    $("#filtroAnioSemana").on(
        "change",
        async function () {
            await cargarSemanas(false);
            actualizarTituloPeriodo();
            await cargarDetalleCue();
        }
    );

    $("#filtroSemana").on(
        "change",
        async function () {
            actualizarTituloPeriodo();
            await cargarDetalleCue();
        }
    );

    $("#btnLimpiar").on(
        "click",
        async function () {
            [
                "#filtroNivel",
                "#filtroAmbito",
                "#filtroRegion",
                "#filtroDepartamento",
                "#filtroLocalidad",
                "#filtroOferta",
                "#filtroCue"
            ].forEach(function (selector) {
                $(selector)
                    .val(null)
                    .trigger("change.select2");
            });

            await actualizarDashboard();
        }
    );
}

async function cargarFiltros() {
    try {
        const query = new URLSearchParams({
            anio: $("#filtroAnio").val(),
            mes: $("#filtroMes").val()
        });

        const data = await fetchJSON(
            `${CFG.urls.filtros}?${query}`
        );

        cargarOpciones("#filtroNivel", data.nivel || []);
        cargarOpciones("#filtroAmbito", data.ambito || []);
        cargarOpciones("#filtroRegion", data.region || []);
        cargarOpciones("#filtroDepartamento", data.departamento || []);
        cargarOpciones("#filtroLocalidad", data.localidad || []);
        cargarOpciones("#filtroOferta", data.oferta || []);
    }
    catch (error) {
        console.error("Error cargando filtros:", error);
    }
}

async function cargarSemanas(seleccionarInicial) {
    const anio = $("#filtroAnioSemana").val();

    const data = await fetchJSON(
        `${CFG.urls.semanas}?anio=${anio}`,
        15000
    );

    const select = $("#filtroSemana");
    const actual = select.val();

    select.empty();

    (data.data || []).forEach(function (item) {
        select.append(
            new Option(
                item.texto,
                item.semana,
                false,
                false
            )
        );
    });

    if (
        seleccionarInicial
        && String(anio) === String(CFG.anioSemanaActual)
    ) {
        select.val(String(CFG.semanaActual));
    }
    else if (
        actual
        && (data.data || []).some(
            item => String(item.semana) === String(actual)
        )
    ) {
        select.val(String(actual));
    }
    else if ((data.data || []).length) {
        select.val(String(data.data[0].semana));
    }

    select.trigger("change.select2");
    actualizarTituloPeriodo();
}

function cargarOpciones(selector, valores) {
    const select = $(selector);
    const actual = select.val();

    select.empty();

    select.append(
        new Option(
            "Todos",
            "",
            false,
            false
        )
    );

    valores.forEach(function (valor) {
        select.append(
            new Option(
                valor,
                valor,
                false,
                false
            )
        );
    });

    if (
        actual
        && valores.includes(actual)
    ) {
        select.val(actual);
    }

    select.trigger("change.select2");
}

function obtenerParametros() {
    return {
        anio: $("#filtroAnio").val(),
        mes: $("#filtroMes").val(),
        anio_semana: $("#filtroAnioSemana").val(),
        semana: $("#filtroSemana").val() || "",
        cueanexo: $("#filtroCue").val() || "",
        nivel: $("#filtroNivel").val() || "",
        ambito: $("#filtroAmbito").val() || "",
        region: $("#filtroRegion").val() || "",
        departamento: $("#filtroDepartamento").val() || "",
        localidad: $("#filtroLocalidad").val() || "",
        oferta: $("#filtroOferta").val() || ""
    };
}

async function actualizarDashboard() {
    paginationState.ranking = 1;
    paginationState.alertas = 1;
    paginationState.mensual = 1;
    paginationState.calidad = 1;
    paginationState.alertasAlumnos = 1;
    paginationState.secciones = 1;
    mostrarLoader(true);

    try {
        const params = new URLSearchParams(
            obtenerParametros()
        );

        const rankingParams = new URLSearchParams(params);
        rankingParams.set("page", paginationState.ranking);
        rankingParams.set("page_size", 10);

        const alertasParams = new URLSearchParams(params);
        alertasParams.set("page", paginationState.alertas);
        alertasParams.set("page_size", 10);

        const [
            resumen,
            evolucion,
            niveles,
            ranking,
            alertas
        ] = await Promise.all([
            fetchJSON(`${CFG.urls.resumen}?${params}`),
            fetchJSON(`${CFG.urls.evolucion}?${params}`),
            fetchJSON(`${CFG.urls.niveles}?${params}`),
            fetchJSON(`${CFG.urls.ranking}?${rankingParams}`),
            fetchJSON(`${CFG.urls.alertas}?${alertasParams}`)
        ]);

        pintarResumen(resumen);
        pintarEvolucion(evolucion.data || []);
        pintarNiveles(niveles.data || []);
        pintarRanking(ranking.data || []);
        pintarTablaRanking(ranking.data || []);
        pintarPaginacion("pagerRanking", ranking.pagination, "ranking");
        pintarAlertas(alertas);
        pintarPaginacion("pagerAlertas", alertas.pagination, "alertas");

        // Estos paneles leen datos agregados/materializados y no bloquean
        // la carga principal del tablero.
        cargarPanelesComplementarios(params);
    }
    catch (error) {
        console.error("Error actualizando dashboard:", error);
    }
    finally {
        mostrarLoader(false);
    }

    await cargarDetalleCue();
}


async function cargarPanelesComplementarios(params) {
    try {
        const mensualParams = new URLSearchParams(params);
        mensualParams.set("page", paginationState.mensual);
        mensualParams.set("page_size", 10);

        const calidadParams = new URLSearchParams(params);
        calidadParams.set("page", paginationState.calidad);
        calidadParams.set("page_size", 10);

        const [mensual, calidad] = await Promise.all([
            fetchJSON(`${CFG.urls.mensual}?${mensualParams}`, 20000),
            fetchJSON(`${CFG.urls.calidadRegistro}?${calidadParams}`, 20000)
        ]);

        pintarMensual(mensual.data || []);
        pintarPaginacion("pagerMensual", mensual.pagination, "mensual");

        pintarCalidad(calidad);
        pintarPaginacion("pagerCalidad", calidad.pagination, "calidad");
    }
    catch (error) {
        console.error("Error cargando paneles complementarios:", error);
        pintarCalidad({data: [], resumen: {}, procesado: false, message: error.message});
        pintarPaginacion("pagerCalidad", null, "calidad");
    }
}


async function cargarDetalleCue() {
    const cue = $("#filtroCue").val();
    if (!cue) {
        pintarSecciones([]);
        pintarAlertasAlumnos([]);
        pintarPaginacion("pagerSecciones", null, "secciones");
        pintarPaginacion("pagerAlertasAlumnos", null, "alertasAlumnos");
        mostrarMensajeDetalle();
        return;
    }

    const base = new URLSearchParams(obtenerParametros());
    const paramsSecciones = new URLSearchParams(base);
    paramsSecciones.set("page", paginationState.secciones);
    paramsSecciones.set("page_size", 10);
    const paramsAlertas = new URLSearchParams(base);
    paramsAlertas.set("page", paginationState.alertasAlumnos);
    paramsAlertas.set("page_size", 10);

    try {
        const [secciones, alertasAlumnos] = await Promise.all([
            fetchJSON(`${CFG.urls.secciones}?${paramsSecciones}`, 20000),
            fetchJSON(`${CFG.urls.alertasAlumnos}?${paramsAlertas}`, 20000)
        ]);
        pintarSecciones(secciones.data || []);
        pintarPaginacion("pagerSecciones", secciones.pagination, "secciones");
        pintarAlertasAlumnos(alertasAlumnos.data || []);
        pintarPaginacion("pagerAlertasAlumnos", alertasAlumnos.pagination, "alertasAlumnos");
    }
    catch (error) {
        console.error("Error cargando detalle del establecimiento:", error);
        pintarSecciones([]);
        pintarAlertasAlumnos([]);
    }
}


function mostrarMensajeDetalle() {
    const secciones = document.getElementById("tablaSecciones");
    if (secciones) {
        secciones.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-5 text-muted">
                    Seleccione un establecimiento para ver el detalle por grado y sección.
                </td>
            </tr>
        `;
    }

    const alumnos = document.getElementById("tablaAlertasAlumnos");
    if (alumnos) {
        alumnos.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-5 text-muted">
                    Seleccione un establecimiento para consultar las alertas nominales semanales.
                </td>
            </tr>
        `;
    }
}



async function cargarPaginaRanking() {
    const params = new URLSearchParams(obtenerParametros());
    params.set("page", paginationState.ranking);
    params.set("page_size", 10);

    try {
        const ranking = await fetchJSON(`${CFG.urls.ranking}?${params}`, 20000);
        pintarRanking(ranking.data || []);
        pintarTablaRanking(ranking.data || []);
        pintarPaginacion("pagerRanking", ranking.pagination, "ranking");
    }
    catch (error) {
        console.error("Error cargando página de ranking:", error);
    }
}


async function cargarPaginaAlertas() {
    const params = new URLSearchParams(obtenerParametros());
    params.set("page", paginationState.alertas);
    params.set("page_size", 10);

    try {
        const alertas = await fetchJSON(`${CFG.urls.alertas}?${params}`, 20000);
        pintarAlertas(alertas);
        pintarPaginacion("pagerAlertas", alertas.pagination, "alertas");
    }
    catch (error) {
        console.error("Error cargando página de alertas institucionales:", error);
    }
}

function configurarPaginacion() {
    configurarPager("pagerRanking", "ranking", cargarPaginaRanking);
    configurarPager("pagerAlertas", "alertas", cargarPaginaAlertas);
    configurarPager("pagerMensual", "mensual", async () => {
        const params = new URLSearchParams(obtenerParametros());
        await cargarPanelesComplementarios(params);
    });
    configurarPager("pagerCalidad", "calidad", async () => {
        const params = new URLSearchParams(obtenerParametros());
        await cargarPanelesComplementarios(params);
    });
    configurarPager("pagerAlertasAlumnos", "alertasAlumnos", cargarDetalleCue);
    configurarPager("pagerSecciones", "secciones", cargarDetalleCue);
}

function configurarPager(id, key, reload) {
    const el = document.getElementById(id);
    if (!el) return;
    el.querySelector(".pager-prev").addEventListener("click", async () => {
        if (paginationState[key] <= 1) return;
        paginationState[key] -= 1;
        await reload();
    });
    el.querySelector(".pager-next").addEventListener("click", async () => {
        paginationState[key] += 1;
        await reload();
    });
}

function pintarPaginacion(id, meta, key) {
    const el = document.getElementById(id);
    if (!el) return;
    const m = meta || {page: 1, pages: 0, total: 0, has_previous: false, has_next: false};
    paginationState[key] = m.page || 1;
    el.querySelector(".pager-current").textContent = m.page || 1;
    el.querySelector(".pager-pages").textContent = m.pages || 1;
    el.querySelector(".pager-total").textContent = formatNumero(m.total || 0);
    el.querySelector(".pager-prev").disabled = !m.has_previous;
    el.querySelector(".pager-next").disabled = !m.has_next;
}

async function fetchJSON(url, timeoutMs = 20000) {
    const controller = new AbortController();
    const timeout = setTimeout(
        () => controller.abort(),
        timeoutMs
    );

    try {
        const response = await fetch(url, {
            signal: controller.signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status} en ${url}`);
        }

        return await response.json();
    }
    catch (error) {
        if (error.name === "AbortError") {
            throw new Error(`Tiempo de espera agotado en ${url}`);
        }
        throw error;
    }
    finally {
        clearTimeout(timeout);
    }
}

function pintarResumen(data) {
    $("#kpiEstablecimientos").text(
        formatNumero(data.establecimientos)
    );

    $("#kpiDias").text(
        formatNumero(data.dias_con_registro)
    );

    $("#kpiSecciones").text(
        formatNumero(data.secciones)
    );

    $("#kpiAsistencia").text(
        formatPorcentaje(
            data.porcentaje_asistencia
        )
    );

    $("#kpiAusentismo").text(
        formatPorcentaje(
            data.porcentaje_ausentismo
        )
    );

    $("#kpiPresentes").text(
        `${formatNumero(data.presentes)} alumno-días presentes`
    );

    $("#kpiAusentes").text(
        `${formatNumero(data.ausentes)} alumno-días ausentes`
    );
}

function pintarEvolucion(data) {
    const labels = data.map(
        fila => formatearFecha(
            fila.fecha_asistencia
        )
    );

    const asistencia = data.map(
        fila => Number(
            fila.porcentaje_asistencia || 0
        )
    );

    const ausentismo = data.map(
        fila => Number(
            fila.porcentaje_ausentismo || 0
        )
    );

    if (chartEvolucion) {
        chartEvolucion.destroy();
    }

    const ctx = document
        .getElementById("chartEvolucion")
        .getContext("2d");

    chartEvolucion = new Chart(
        ctx,
        {
            type: "line",

            data: {
                labels: labels,

                datasets: [
                    {
                        label: "Asistencia",
                        data: asistencia,
                        borderWidth: 2.5,
                        tension: .3,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    },
                    {
                        label: "Ausentismo",
                        data: ausentismo,
                        borderWidth: 2,
                        tension: .3,
                        pointRadius: 2
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                interaction: {
                    mode: "index",
                    intersect: false
                },

                plugins: {
                    legend: {
                        position: "bottom",

                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            padding: 20
                        }
                    },

                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return (
                                    `${context.dataset.label}: `
                                    + `${Number(context.raw).toFixed(2)}%`
                                );
                            }
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,

                        ticks: {
                            callback: value => `${value}%`
                        },

                        grid: {
                            color: "#eef2f6"
                        }
                    },

                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );
}

function pintarNiveles(data) {
    const labels = data.map(
        fila => fila.nivel
    );

    const valores = data.map(
        fila => Number(
            fila.porcentaje_asistencia || 0
        )
    );

    if (chartNivel) {
        chartNivel.destroy();
    }

    const ctx = document
        .getElementById("chartNivel")
        .getContext("2d");

    chartNivel = new Chart(
        ctx,
        {
            type: "bar",

            data: {
                labels: labels,

                datasets: [
                    {
                        label: "Asistencia",
                        data: valores,
                        borderRadius: 6,
                        barThickness: 25
                    }
                ]
            },

            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {
                            label: context =>
                                `${Number(context.raw).toFixed(2)}%`
                        }
                    }
                },

                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,

                        ticks: {
                            callback: value => `${value}%`
                        },

                        grid: {
                            color: "#eef2f6"
                        }
                    },

                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );
}

function pintarRanking(data) {
    const items = data.slice(0, 10);

    const labels = items.map(
        fila => {
            const nombre =
                fila.escuela
                || fila.cueanexo;

            return nombre.length > 30
                ? nombre.substring(0, 30) + "…"
                : nombre;
        }
    );

    const valores = items.map(
        fila => Number(
            fila.porcentaje_ausentismo || 0
        )
    );

    if (chartRanking) {
        chartRanking.destroy();
    }

    const ctx = document
        .getElementById("chartRanking")
        .getContext("2d");

    chartRanking = new Chart(
        ctx,
        {
            type: "bar",

            data: {
                labels: labels,

                datasets: [
                    {
                        label: "Ausentismo",
                        data: valores,
                        borderRadius: 6
                    }
                ]
            },

            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {
                            label: context =>
                                `${Number(context.raw).toFixed(2)}%`
                        }
                    }
                },

                scales: {
                    x: {
                        beginAtZero: true,

                        ticks: {
                            callback: value => `${value}%`
                        },

                        grid: {
                            color: "#eef2f6"
                        }
                    },

                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );
}

function pintarTablaRanking(data) {
    const tbody = document.getElementById(
        "tablaRanking"
    );

    tbody.innerHTML = "";

    if (!data.length) {
        tbody.innerHTML = `
            <tr>
                <td
                    colspan="5"
                    class="text-center py-5 text-muted"
                >
                    Sin información para los filtros seleccionados.
                </td>
            </tr>
        `;

        return;
    }

    data.forEach(
        fila => {
            const asistencia = Number(
                fila.porcentaje_asistencia || 0
            );

            const ausentismo = Number(
                fila.porcentaje_ausentismo || 0
            );

            tbody.insertAdjacentHTML(
                "beforeend",
                `
                <tr>

                    <td>
                        <strong>
                            ${escapeHtml(fila.cueanexo)}
                        </strong>
                    </td>

                    <td class="school-name">
                        ${escapeHtml(fila.escuela || "—")}
                    </td>

                    <td class="text-center">
                        ${formatNumero(fila.jornadas_registradas)}
                    </td>

                    <td class="text-end">

                        <span
                            class="
                                metric-pill
                                ${claseAsistencia(asistencia)}
                            "
                        >
                            ${asistencia.toFixed(2)}%
                        </span>

                    </td>

                    <td class="text-end">
                        ${ausentismo.toFixed(2)}%
                    </td>

                </tr>
                `
            );
        }
    );
}

function pintarSecciones(data) {
    const tbody = document.getElementById(
        "tablaSecciones"
    );

    tbody.innerHTML = "";

    $("#contadorSecciones").text(
        formatNumero(data.length)
    );

    if (!data.length) {
        tbody.innerHTML = `
            <tr>
                <td
                    colspan="10"
                    class="text-center py-5 text-muted"
                >
                    No existen registros para los filtros seleccionados.
                </td>
            </tr>
        `;

        return;
    }

    data.forEach(
        fila => {
            const asistencia = Number(
                fila.porcentaje_asistencia || 0
            );

            tbody.insertAdjacentHTML(
                "beforeend",
                `
                <tr>

                    <td class="school-name">

                        <div>
                            ${escapeHtml(fila.escuela || "—")}
                        </div>

                        <small class="text-muted">
                            ${escapeHtml(fila.cueanexo || "")}
                        </small>

                    </td>

                    <td>
                        ${escapeHtml(fila.nivel || "—")}
                    </td>

                    <td>
                        ${escapeHtml(fila.grado || "—")}
                    </td>

                    <td>
                        ${escapeHtml(fila.seccion || "—")}
                    </td>

                    <td>
                        ${escapeHtml(fila.turno || "—")}
                    </td>

                    <td class="text-center">
                        ${formatNumero(fila.jornadas_registradas)}
                    </td>

                    <td class="text-end">
                        ${formatNumero(fila.alumno_dias)}
                    </td>

                    <td class="text-end">
                        ${formatNumero(fila.presentes)}
                    </td>

                    <td class="text-end">
                        ${formatNumero(fila.ausentes)}
                    </td>

                    <td class="text-end">

                        <span
                            class="
                                metric-pill
                                ${claseAsistencia(asistencia)}
                            "
                        >
                            ${asistencia.toFixed(2)}%
                        </span>

                    </td>

                </tr>
                `
            );
        }
    );
}

function pintarAlertas(data) {
    const resumen = data.resumen || {};

    $("#alertaNormal").text(
        formatNumero(
            resumen.NORMAL || 0
        )
    );

    $("#alertaAtencion").text(
        formatNumero(
            resumen.ATENCION || 0
        )
    );

    $("#alertaAlto").text(
        formatNumero(
            resumen.ALTO || 0
        )
    );

    $("#alertaCritico").text(
        formatNumero(
            resumen.CRITICO || 0
        )
    );

    pintarTablaAlertas(
        data.data || []
    );
}

function pintarTablaAlertas(data) {
    const tbody = document.getElementById(
        "tablaAlertas"
    );

    tbody.innerHTML = "";

    if (!data.length) {
        tbody.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="text-center py-5 text-muted"
                >
                    No existen alertas para los filtros seleccionados.
                </td>
            </tr>
        `;

        return;
    }

    data.forEach(
        fila => {
            const nivel =
                fila.nivel_alerta
                || "SIN DATOS";

            const porcentaje =
                fila.porcentaje_asistencia !== null
                ? Number(fila.porcentaje_asistencia)
                : null;

            tbody.insertAdjacentHTML(
                "beforeend",
                `
                <tr>

                    <td>

                        <span
                            class="
                                alert-badge
                                ${claseAlerta(nivel)}
                            "
                        >
                            ${textoAlerta(nivel)}
                        </span>

                    </td>

                    <td>

                        <strong>
                            ${escapeHtml(fila.cueanexo || "")}
                        </strong>

                    </td>

                    <td class="school-name">
                        ${escapeHtml(fila.escuela || "—")}
                    </td>

                    <td>
                        ${escapeHtml(fila.departamento || "—")}
                    </td>

                    <td class="text-center">
                        ${formatNumero(fila.jornadas_registradas)}
                    </td>

                    <td class="text-center">
                        ${formatNumero(fila.secciones)}
                    </td>

                    <td class="text-end">
                        ${
                            porcentaje !== null
                            ? porcentaje.toFixed(2) + "%"
                            : "—"
                        }
                    </td>

                </tr>
                `
            );
        }
    );
}

function claseAsistencia(valor) {
    if (valor >= 90) {
        return "metric-good";
    }

    if (valor >= 80) {
        return "metric-warning";
    }

    return "metric-danger";
}

function claseAlerta(nivel) {
    switch (nivel) {
        case "NORMAL":
            return "badge-normal";

        case "ATENCION":
            return "badge-atencion";

        case "ALTO":
            return "badge-alto";

        case "CRITICO":
            return "badge-critico";

        default:
            return "badge-sin-datos";
    }
}

function textoAlerta(nivel) {
    switch (nivel) {
        case "ATENCION":
            return "ATENCIÓN";

        case "CRITICO":
            return "CRÍTICO";

        default:
            return nivel;
    }
}

function formatNumero(valor) {
    if (
        valor === null
        || valor === undefined
    ) {
        return "0";
    }

    return formatter.format(
        Number(valor)
    );
}

function formatPorcentaje(valor) {
    if (
        valor === null
        || valor === undefined
    ) {
        return "0,00%";
    }

    return (
        Number(valor)
        .toLocaleString(
            "es-AR",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        )
        + "%"
    );
}

function formatearFecha(fecha) {
    if (!fecha) {
        return "";
    }

    const partes = fecha.split("-");

    return `${partes[2]}/${partes[1]}`;
}

function mostrarLoader(mostrar) {
    const loader = document.getElementById(
        "dashboardLoader"
    );

    loader.classList.toggle(
        "d-none",
        !mostrar
    );
}

function escapeHtml(value) {
    if (
        value === null
        || value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function pintarAlertasAlumnos(data) {
    const tbody = document.getElementById(
        "tablaAlertasAlumnos"
    );

    if (!tbody) {
        return;
    }

    tbody.innerHTML = "";

    $("#contadorAlertasAlumnos").text(
        formatNumero(data.length)
    );

    if (!data.length) {
        tbody.innerHTML = `
            <tr>
                <td
                    colspan="9"
                    class="text-center py-5 text-muted"
                >
                    No existen estudiantes con información nominal
                    para los filtros seleccionados.
                </td>
            </tr>
        `;

        return;
    }

    data.forEach(
        fila => {

            const porcentaje =
                fila.porcentaje_asistencia !== null
                ? Number(fila.porcentaje_asistencia)
                : null;

            const nivel =
                fila.nivel_alerta_final
                || "SIN DATOS";

            tbody.insertAdjacentHTML(
                "beforeend",
                `
                <tr>

                    <td>
                        <span
                            class="
                                alert-badge
                                ${claseAlerta(nivel)}
                            "
                        >
                            ${textoAlerta(nivel)}
                        </span>
                    </td>

                    <td>
                        <strong>
                            ${escapeHtml(
                                fila.nombre_apellido
                                || `Alumno ${fila.id_alumno}`
                            )}
                        </strong>
                    </td>

                    <td>
                        ${escapeHtml(
                            fila.cueanexo || ""
                        )}
                    </td>

                    <td class="school-name">
                        ${escapeHtml(
                            fila.escuela || "—"
                        )}
                    </td>

                    <td>
                        ${escapeHtml(
                            fila.grado || "—"
                        )}
                        ·
                        ${escapeHtml(
                            fila.seccion || "—"
                        )}
                    </td>

                    <td class="text-end">
                        ${
                            porcentaje !== null
                            ? porcentaje.toFixed(2) + "%"
                            : "—"
                        }
                    </td>

                    <td class="text-end">
                        ${Number(
                            fila.inasistencias_equivalentes || 0
                        ).toFixed(2)}
                    </td>

                    <td class="text-center">
                        ${formatNumero(
                            fila.racha_actual_ausencias
                        )}
                    </td>

                    <td class="text-center">
                        ${formatNumero(
                            fila.racha_maxima_ausencias
                        )}
                    </td>

                </tr>
                `
            );
        }
    );
}


function pintarMensual(data) {
    const tbody = document.getElementById("tablaMensual");
    if (!tbody) return;
    tbody.innerHTML = "";
    $("#contadorMensual").text(formatNumero(data.length));

    if (!data.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">Sin información mensual para los filtros seleccionados.</td></tr>`;
        return;
    }

    data.forEach(fila => {
        const detalle = [fila.nivel, fila.grado, fila.seccion, fila.turno]
            .filter(Boolean).join(" · ") || "Resumen establecimiento";
        tbody.insertAdjacentHTML("beforeend", `
            <tr>
                <td><strong>${escapeHtml(fila.cueanexo || "")}</strong><br><small>${escapeHtml(fila.escuela || "")}</small></td>
                <td>${escapeHtml(detalle)}</td>
                <td class="text-end">${formatNumero(fila.presentes)}</td>
                <td class="text-end">${formatNumero(fila.ausentes)}</td>
                <td class="text-end">${formatNumero(fila.ausentes_justificados)}</td>
                <td class="text-end">${formatNumero(fila.otras_faltas)}</td>
                <td class="text-end"><span class="metric-pill ${claseAsistencia(Number(fila.porcentaje_asistencia || 0))}">${Number(fila.porcentaje_asistencia || 0).toFixed(2)}%</span></td>
            </tr>
        `);
    });
}

function pintarCalidad(resultado) {
    const datos = resultado.data || [];
    const resumen = resultado.resumen || {};
    $("#calidadCompleto").text(formatNumero(resumen.COMPLETO || 0));
    $("#calidadParcial").text(formatNumero(resumen.PARCIAL || 0));
    $("#calidadSinCarga").text(formatNumero(resumen.SIN_CARGA || 0));

    const tbody = document.getElementById("tablaCalidad");
    tbody.innerHTML = "";
    const panel = tbody.closest(".quality-panel");
    const anterior = panel ? panel.querySelector(".quality-message") : null;
    if (anterior) anterior.remove();
    if (resultado.message && panel) {
        const aviso = document.createElement("div");
        aviso.className = "quality-message";
        aviso.textContent = resultado.message;
        const table = panel.querySelector(".table-responsive");
        panel.insertBefore(aviso, table);
    }
    if (!datos.length) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center py-5 text-muted">${escapeHtml(resultado.message || "Sin datos de calidad procesados para el período seleccionado.")}</td></tr>`;
        return;
    }
    datos.forEach(fila => {
        tbody.insertAdjacentHTML("beforeend", `
            <tr>
                <td><strong>${escapeHtml(fila.cueanexo || "—")}</strong></td>
                <td class="school-name">${escapeHtml(fila.escuela || "—")}</td>
                <td class="text-center">${formatNumero(fila.cantidad_secciones)}</td>
                <td class="text-center">${formatNumero(fila.dias_habiles_calendario)}</td>
                <td class="text-center">${formatNumero(fila.jornadas_esperadas)}</td>
                <td class="text-center">${formatNumero(fila.jornadas_registradas)}</td>
                <td class="text-center"><strong>${formatNumero(fila.jornadas_sin_registro)}</strong></td>
                <td class="text-end">${formatPorcentaje(fila.porcentaje_cumplimiento)}</td>
                <td>${escapeHtml((fila.estado_registro || "—").replaceAll("_", " "))}</td>
            </tr>`);
    });
}

