document.addEventListener("DOMContentLoaded", () => {

    // =====================================================
    // Configuración Global
    // =====================================================

    Chart.defaults.font.family =
        "'Inter','Segoe UI',sans-serif";

    Chart.defaults.font.size = 13;

    Chart.defaults.plugins.legend.position = "bottom";

    Chart.defaults.plugins.tooltip.cornerRadius = 8;

    Chart.defaults.plugins.tooltip.padding = 10;

    Chart.defaults.responsive = true;

    Chart.defaults.maintainAspectRatio = false;



    // =====================================================
    // Colores Institucionales
    // =====================================================

    const colores = {

        azul: "#0d6efd",

        celeste: "#3da5ff",

        verde: "#198754",

        amarillo: "#ffc107",

        rojo: "#dc3545",

        gris: "#6c757d",

        cyan: "#0dcaf0",

        naranja: "#fd7e14",

        violeta: "#6f42c1",

        fondo: [
            "#0d6efd",
            "#198754",
            "#ffc107",
            "#dc3545",
            "#6f42c1",
            "#20c997",
            "#fd7e14",
            "#0dcaf0",
            "#6c757d"
        ]

    };



    // =====================================================
    // Utilidades
    // =====================================================

    function crearGrafico(id, config) {

        const canvas = document.getElementById(id);

        if (!canvas) return;

        new Chart(canvas, config);

    }



    // =====================================================
    // Estados
    // =====================================================

    if (typeof estadosChart !== "undefined") {

        crearGrafico("chartEstados", {

            type: "doughnut",

            data: {

                labels: estadosChart.labels,

                datasets: [{

                    data: estadosChart.values,

                    backgroundColor: colores.fondo,

                    borderWidth: 1

                }]

            },

            options: {

                plugins: {

                    legend: {

                        position: "bottom"

                    }

                }

            }

        });

    }



    // =====================================================
    // Prioridades
    // =====================================================

    if (typeof prioridadesChart !== "undefined") {

        crearGrafico("chartPrioridades", {

            type: "pie",

            data: {

                labels: prioridadesChart.labels,

                datasets: [{

                    data: prioridadesChart.values,

                    backgroundColor: colores.fondo

                }]

            }

        });

    }



    // =====================================================
    // Empresas
    // =====================================================

    if (typeof empresasChart !== "undefined") {

        crearGrafico("chartEmpresas", {

            type: "bar",

            data: {

                labels: empresasChart.labels,

                datasets: [{

                    label: "Intervenciones",

                    data: empresasChart.values,

                    backgroundColor: colores.azul

                }]

            },

            options: {

                indexAxis: "y",

                scales: {

                    x: {

                        beginAtZero: true

                    }

                }

            }

        });

    }



    // =====================================================
    // Organismos
    // =====================================================

    if (typeof organismosChart !== "undefined") {

        crearGrafico("chartOrganismos", {

            type: "bar",

            data: {

                labels: organismosChart.labels,

                datasets: [{

                    label: "Cantidad",

                    data: organismosChart.values,

                    backgroundColor: colores.verde

                }]

            }

        });

    }



    // =====================================================
    // Financiamiento
    // =====================================================

    if (typeof financiamientoChart !== "undefined") {

        crearGrafico("chartFinanciamiento", {

            type: "polarArea",

            data: {

                labels: financiamientoChart.labels,

                datasets: [{

                    data: financiamientoChart.values,

                    backgroundColor: colores.fondo

                }]

            }

        });

    }



    // =====================================================
    // Costos
    // =====================================================

    if (typeof costosChart !== "undefined") {

        crearGrafico("chartCostos", {

            type: "bar",

            data: {

                labels: costosChart.labels,

                datasets: [

                    {

                        label: "Estimado",

                        data: costosChart.estimado,

                        backgroundColor: colores.azul

                    },

                    {

                        label: "Real",

                        data: costosChart.real,

                        backgroundColor: colores.rojo

                    }

                ]

            },

            options: {

                scales: {

                    y: {

                        beginAtZero: true

                    }

                }

            }

        });

    }



    // =====================================================
    // Avance mensual
    // =====================================================

    if (typeof avanceMensualChart !== "undefined") {

        crearGrafico("chartAvanceMensual", {

            type: "line",

            data: {

                labels: avanceMensualChart.labels,

                datasets: [

                    {

                        label: "Intervenciones",

                        data: avanceMensualChart.values,

                        borderColor: colores.azul,

                        backgroundColor: colores.celeste,

                        fill: false,

                        tension: 0.35

                    }

                ]

            },

            options: {

                interaction: {

                    intersect: false,

                    mode: "index"

                }

            }

        });

    }



    // =====================================================
    // Hallazgos por categoría
    // =====================================================

    if (typeof categoriasChart !== "undefined") {

        crearGrafico("chartCategorias", {

            type: "bar",

            data: {

                labels: categoriasChart.labels,

                datasets: [{

                    label: "Hallazgos",

                    data: categoriasChart.values,

                    backgroundColor: colores.naranja

                }]

            }

        });

    }



    // =====================================================
    // Relevamientos por mes
    // =====================================================

    if (typeof relevamientosChart !== "undefined") {

        crearGrafico("chartRelevamientos", {

            type: "line",

            data: {

                labels: relevamientosChart.labels,

                datasets: [{

                    label: "Relevamientos",

                    data: relevamientosChart.values,

                    borderColor: colores.verde,

                    backgroundColor: colores.verde,

                    tension: 0.30,

                    fill: false

                }]

            }

        });

    }



    // =====================================================
    // Intervenciones por tipo
    // =====================================================

    if (typeof tiposChart !== "undefined") {

        crearGrafico("chartTipos", {

            type: "bar",

            data: {

                labels: tiposChart.labels,

                datasets: [{

                    label: "Cantidad",

                    data: tiposChart.values,

                    backgroundColor: colores.violeta

                }]

            }

        });

    }



});