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

    const csrftoken = getCSRFToken();

    console.log("CSRF TOKEN:", csrftoken); // ahora sí va a tener valor

    $('#data').DataTable({
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
            {"data": "cueanexo"},
            {"data": "mes"},
            {"data": "anio"},
            {"data": "servicio"},
            {"data": "turnos"},
            {"data": "varones"},
            {"data": "total"},
            {"data": "id"}
        ],

        columnDefs: [
            {
                targets: -1,
                className: 'text-center',
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

            let totalVarones = data.reduce((sum, r) => sum + (parseInt(r.varones) || 0), 0);
            let totalGeneral = data.reduce((sum, r) => sum + (parseInt(r.total) || 0), 0);

            $('#total_varones').html(totalVarones);
            $('#totales').html(totalGeneral);
        }
    });

});