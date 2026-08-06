// =========================
// 🔐 OBTENER CSRF DESDE INPUT
// =========================
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// =========================
// DATATABLE
// =========================
$(function () {

    console.log("INIT SOLO UNA VEZ");

    // evitar doble inicialización REAL
    if ($('#data').hasClass('dataTable')) {
        return;
    }

    const csrftoken = getCSRFToken();

    console.log("CSRF TOKEN:", csrftoken); // ahora sí va a tener valor

    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: false, // 🔥 importante

        ajax: {
            url: window.location.pathname,
            type: 'POST',
            headers: {
                "X-CSRFToken": csrftoken
            },
            data: { action: 'searchdata' },
            dataSrc: function (json) {

                console.log("DATA:", json);

                if (json.error) {
                    Swal.fire("Error", json.message, "error");
                    return [];
                }

                return json;
            },

            error: function (xhr) {

                console.error("STATUS:", xhr.status);
                console.error("RESPONSE:", xhr.responseText);

                Swal.fire({
                    icon: "error",
                    title: "Error AJAX",
                    text: "Ver consola (F12)"
                });
            }
        },

        columns: [
            { data: "cueanexo" },
            { data: "mes" },
            { data: "anio" },
            { data: "total_mes" },
            { data: "total_base" },
            { data: "total_usuarios" },
            { data: "observaciones" },
            { data: "id" }
        ],

        columnDefs: [
            {
                targets: -1,
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    return `
                        <a href="../update/${row.id}/" class="btn btn-warning btn-xs btn-flat">
                            <i class="fas fa-edit"></i>
                        </a>
                        <a href="../delete/${row.id}/" class="btn btn-danger btn-xs btn-flat">
                            <i class="fas fa-trash-alt"></i>
                        </a>
                    `;
                }
            }
        ],

        drawCallback: function () {

            var api = this.api();

            var totalmes = api.column(3).data().reduce((a, b) => a + b, 0);
            var totalbase = api.column(4).data().reduce((a, b) => a + b, 0);
            var totalusuarios = api.column(5).data().reduce((a, b) => a + b, 0);

            var footer = $(api.table().footer()).find('th');

            footer.eq(3).html(totalmes);
            footer.eq(4).html(totalbase);
            footer.eq(5).html(totalusuarios);

            console.log("TOTAL FINAL:", totalusuarios);
        }
    });

});