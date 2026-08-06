// =========================
// 🔐 OBTENER CSRF DESDE INPUT
// =========================
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

$(function () {

    const csrftoken = getCSRFToken();

    console.log("CSRF TOKEN:", csrftoken); // ahora sí va a tener valor

    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,

        ajax: {
            url: window.location.pathname,
            type: 'POST',

            headers: {
                "X-CSRFToken": csrftoken
            },

            data: {
                action: 'searchdata'
            },

            dataSrc: function (json) {

                console.log("DATA RECIBIDA:", json);

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
                    text: "Error 403 CSRF o servidor"
                });
            }
        },

        columns: [
            {"data": "cueanexo"},
            {"data": "mes"},
            {"data": "anio"},
            {"data": "servicio"},
            {"data": "turnos"},
            {"data": "t_material"},
            {"data": "cantidad"},
            {"data": "id"}
        ],

        columnDefs: [
            {
                targets: -1,
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    return `
                        <a href="../update/${row.id}/" class="btn btn-warning btn-sm">
                            <i class="fas fa-edit"></i>
                        </a>
                        <a href="../delete/${row.id}/" class="btn btn-danger btn-sm">
                            <i class="fas fa-trash"></i>
                        </a>
                    `;
                }
            }
        ],

        footerCallback: function (row, data) {
            let total = data.reduce((sum, r) => sum + (parseInt(r.cantidad) || 0), 0);
            $('#totales').html(total);
        }
    });

});