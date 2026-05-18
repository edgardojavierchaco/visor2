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
            type: "POST",
            headers: {
                "X-CSRFToken": csrftoken
            },
            data: {
                'action': 'searchdata'
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
            { data: "cueanexo" },
            { data: "cuil" },
            { data: "apellidos" },
            { data: "nombres" },
            { data: "cargo" },
            { data: "situacion_revista" },
            { data: "f_ingreso" },
            { data: "f_hasta" },
            { data: "turno" },
            { data: "mes" },
            { data: "anio" },
            {
                data: "id",
                render: function (data, type, row) {
                    var buttons = '<a href="../update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="../delete/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    return buttons;
                }
            }
        ]
    });

});